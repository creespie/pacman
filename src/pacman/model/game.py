"""The game state: the model of the MVC architecture."""

import random

from mazegenerator import MazeGenerator

from pacman.config import Config
from pacman.model.collision import CollisionDetector
from pacman.model.entities import Blinky, Pacman
from pacman.model.food import Food
from pacman.model.maze import Maze
from pacman.protocol import (
    Command,
    Direction,
    Event,
    FoodCollected,
    FoodSpawned,
    FoodType,
    GameOver,
    GameWon,
    GhostMoved,
    GhostState,
    GhostStateChanged,
    LevelCompleted,
    LifeLost,
    MazeGenerated,
    PacmanCaught,
    PacmanMoved,
    ScoreChanged,
    SetDirection,
)
from pacman.utils.observer import Observable

# How far (in maze cells) an entity may be from a cell's centre and still
# be considered "on" it. Must stay above the distance covered in a single
# frame (speed * delta_time) or a fast ghost could skip past every centre.
_ALIGN_EPSILON = 0.1

_ALL_DIRECTIONS = (Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT)

_OPPOSITE_DIRECTIONS = {
    Direction.UP: Direction.DOWN,
    Direction.DOWN: Direction.UP,
    Direction.LEFT: Direction.RIGHT,
    Direction.RIGHT: Direction.LEFT,
    Direction.NONE: Direction.NONE,
}


class Game(Observable[Event]):
    """Hold the game state and notify the observers of every change."""

    # How long ghosts stay edible after Pac-Man eats a super-pacgum.
    FRIGHTENED_DURATION = 8.0

    # How long an eaten ghost stays away before it respawns at home.
    GHOST_RESPAWN_DELAY = 7.0

    def __init__(self, config: Config) -> None:
        super().__init__()

        self._config = config
        self._points_per_pacgum = config.points_per_pacgum
        self._points_per_super_pacgum = config.points_per_super_pacgum
        self._points_per_ghost = config.points_per_ghost

        self._level = 1
        self._level_timer = 0.0
        self._game_over = False
        self._game_won = False

        # Create Pac-Man once. Only its position is ever reset afterwards,
        # so its lives and score survive level changes and respawns.
        self._pacman = Pacman(
            x=1.5, y=1.5, radius=0.3, speed=5.0, lives=config.lives
        )
        self._pacman_spawn = self._pacman.position

        self._maze: Maze
        self._collision_detector: CollisionDetector
        self._ghosts: list[Blinky] = []
        self._foods: list[Food] = []

        self._setup_level(config.seed)

    # -- Level setup -------------------------------------------------------

    def _setup_level(self, seed: int) -> None:
        """(Re)generate the maze, the ghosts and the food for a level."""
        # Generate the maze. Every generator cell becomes a 2x2 block plus
        # a one-cell border, so a grid of N cells needs N // 2 generator
        # cells.
        self._maze = Maze(
            MazeGenerator(
                size=(self._config.width // 2, self._config.height // 2),
                perfect=False,
                seed=seed,
            )
        )

        self._collision_detector = CollisionDetector(self._maze)

        self._pacman.reset_position(*self._pacman_spawn)

        self._ghosts = self._spawn_ghosts()

        self._foods = []
        self._generate_food()

        self._level_timer = 0.0

    def _spawn_ghosts(self) -> list[Blinky]:
        """Create one ghost in each corner of the maze."""
        return [
            Blinky(x=x, y=y, radius=0.3, speed=4.0)
            for x, y in (
                self._nearest_walkable_center(cx, cy)
                for cx, cy in self._corner_cells()
            )
        ]

    def _corner_cells(self) -> tuple[tuple[int, int], ...]:
        """Return the 4 corner cells of the maze (grid coordinates)."""
        return (
            (1, 1),
            (self._maze.width - 2, 1),
            (1, self._maze.height - 2),
            (self._maze.width - 2, self._maze.height - 2),
        )

    def _nearest_walkable_center(self, x: int, y: int) -> tuple[float, float]:
        """Return the centre of the walkable cell closest to (x, y)."""
        if self._maze.is_walkable(x, y):
            return x + 0.5, y + 0.5

        max_radius = max(self._maze.width, self._maze.height)

        for radius in range(1, max_radius):
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    candidate_x, candidate_y = x + dx, y + dy

                    if self._maze.is_walkable(candidate_x, candidate_y):
                        return candidate_x + 0.5, candidate_y + 0.5

        # Should never happen on a valid maze.
        return self._pacman_spawn

    def _generate_food(self) -> None:
        """Place a pacgum on every walkable cell, and a super-pacgum in
        each of the 4 corners of the maze."""
        super_pacgum_cells = {
            self._nearest_walkable_center(cx, cy) for cx, cy in self._corner_cells()
        }

        for y in range(self._maze.height):
            for x in range(self._maze.width):
                if not self._maze.is_walkable(x, y):
                    continue

                center = (x + 0.5, y + 0.5)
                kind = (
                    FoodType.SUPER_PACGUM
                    if center in super_pacgum_cells
                    else FoodType.PACGUM
                )

                self._foods.append(Food(x=center[0], y=center[1], kind=kind))

    # -- Lifecycle -----------------------------------------------------

    def start(self) -> None:
        """Notify the observers of the initial state."""
        self._notify_level_state()

    def _notify_level_state(self) -> None:
        """Notify the observers of the full state of the current level."""
        self.notify(
            MazeGenerated(self._maze.width, self._maze.height, self._maze.grid)
        )

        for food in self._foods:
            if not food.collected:
                self.notify(FoodSpawned(food.x, food.y, food.kind))

        self._notify_pacman_moved()

        for index, ghost in enumerate(self._ghosts):
            self._notify_ghost_moved(index, ghost)

        self.notify(ScoreChanged(self._pacman.score))

    def handle(self, command: Command) -> None:
        """Apply a command coming from a controller."""
        match command:
            case SetDirection(direction=direction):
                self._pacman.direction = direction

    def update(self, delta_time: float) -> None:
        """Update all game objects."""
        if self._game_over or self._game_won:
            return

        self._update_level_timer(delta_time)

        if self._game_over:
            return

        self._update_pacman(delta_time)
        self._update_ghosts(delta_time)
        self._check_food_collisions()
        self._check_entity_collisions()

        if self._game_over:
            return

        self._check_level_complete()

    # -- Level timer ---------------------------------------------------

    def _update_level_timer(self, delta_time: float) -> None:
        """Track how long the current level has been running."""
        self._level_timer += delta_time

        if self._level_timer >= self._config.level_max_time:
            # Running out of time is treated like being caught by a ghost:
            # Pac-Man loses a life and the level restarts.
            self._lose_life()

    # -- Pac-Man -------------------------------------------------------

    def _update_pacman(self, delta_time: float) -> None:
        """Update Pac-Man and prevent wall collisions."""
        old_position = self._pacman.position

        self._pacman.update(delta_time)

        if self._collision_detector.entity_hits_wall(self._pacman):
            self._pacman.position = self._collision_detector.clip_to_wall(
                self._pacman.radius, old_position, self._pacman.position
            )

        if self._pacman.position != old_position:
            self._notify_pacman_moved()

    # -- Ghosts ----------------------------------------------------------

    def _update_ghosts(self, delta_time: float) -> None:
        """Update ghosts: state timers, steering, movement and walls."""
        for index, ghost in enumerate(self._ghosts):
            self._update_ghost_state(index, ghost, delta_time)

            if ghost.state == GhostState.EATEN:
                # Eaten ghosts wait invisibly until they respawn.
                continue

            self._steer_ghost(ghost)

            old_position = ghost.position
            ghost.update(delta_time)

            if self._collision_detector.entity_hits_wall(ghost):
                ghost.position = self._collision_detector.clip_to_wall(
                    ghost.radius, old_position, ghost.position
                )
                ghost.direction = Direction.NONE

            if ghost.position != old_position:
                self._notify_ghost_moved(index, ghost)

    def _update_ghost_state(
        self, index: int, ghost: Blinky, delta_time: float
    ) -> None:
        """Advance a ghost's frightened/eaten timer, if it has one."""
        if ghost.state == GhostState.CHASE:
            return

        ghost.state_timer -= delta_time

        if ghost.state_timer > 0:
            return

        if ghost.state == GhostState.FRIGHTENED:
            ghost.state = GhostState.CHASE
            self.notify(GhostStateChanged(index, ghost.state))

        elif ghost.state == GhostState.EATEN:
            ghost.respawn()
            self.notify(GhostStateChanged(index, ghost.state))
            self._notify_ghost_moved(index, ghost)

    def _steer_ghost(self, ghost: Blinky) -> None:
        """Pick a new direction for a ghost when it reaches a cell centre."""
        cell_x, cell_y = int(ghost.x), int(ghost.y)
        offset_x = ghost.x - cell_x - 0.5
        offset_y = ghost.y - cell_y - 0.5

        if abs(offset_x) > _ALIGN_EPSILON or abs(offset_y) > _ALIGN_EPSILON:
            # Not centred on a cell yet: keep moving the same way.
            return

        candidates = [
            direction
            for direction in _ALL_DIRECTIONS
            if self._maze.is_walkable(
                cell_x + int(direction.value[0]), cell_y + int(direction.value[1])
            )
        ]

        if not candidates:
            ghost.direction = Direction.NONE
            return

        # Ghosts never reverse into where they came from, unless it is the
        # only walkable direction (a dead end).
        opposite = _OPPOSITE_DIRECTIONS[ghost.direction]
        non_reversing = [d for d in candidates if d != opposite]
        options = non_reversing or candidates

        flee = ghost.state == GhostState.FRIGHTENED

        def score(direction: Direction) -> float:
            dx, dy = direction.value
            next_x, next_y = cell_x + dx + 0.5, cell_y + dy + 0.5
            distance = (
                (next_x - self._pacman.x) ** 2 + (next_y - self._pacman.y) ** 2
            )
            # Chase: get as close as possible. Frightened: run away.
            return -distance if flee else distance

        ghost.direction = min(options, key=score)

    # -- Food --------------------------------------------------------------

    def _check_food_collisions(self) -> None:
        """Check if Pac-Man collects any food."""
        for food in self._foods:
            if food.collected:
                continue

            if self._food_collides_with_pacman(food):
                food.collect()
                self.notify(FoodCollected(food.x, food.y, food.kind))

                if food.kind == FoodType.PACGUM:
                    self._pacman.add_score(self._points_per_pacgum)

                elif food.kind == FoodType.SUPER_PACGUM:
                    self._pacman.add_score(self._points_per_super_pacgum)
                    self._frighten_ghosts()

                self.notify(ScoreChanged(self._pacman.score))

    def _food_collides_with_pacman(self, food: Food) -> bool:
        """Return True if Pac-Man touches a food item."""
        distance_x = self._pacman.x - food.x
        distance_y = self._pacman.y - food.y

        distance_squared = distance_x * distance_x + distance_y * distance_y

        # Food is considered a point.
        radius = self._pacman.radius

        return distance_squared < radius * radius

    def _frighten_ghosts(self) -> None:
        """Make every ghost that isn't already eaten edible for a while."""
        for index, ghost in enumerate(self._ghosts):
            if ghost.state == GhostState.EATEN:
                continue

            ghost.state = GhostState.FRIGHTENED
            ghost.state_timer = self.FRIGHTENED_DURATION
            self.notify(GhostStateChanged(index, ghost.state))

    def _check_level_complete(self) -> None:
        """Move to the next level once every food item is eaten."""
        if any(not food.collected for food in self._foods):
            return

        self.notify(LevelCompleted(self._level))

        if self._level >= self._config.levels:
            self._game_won = True
            self.notify(GameWon(self._pacman.score))
            return

        self._level += 1
        # The first level uses the configured seed; every following level
        # is generated randomly.
        self._setup_level(random.randint(0, 2**31 - 1))
        self._notify_level_state()

    # -- Entity collisions -----------------------------------------------

    def _check_entity_collisions(self) -> None:
        """Check collisions between Pac-Man and the ghosts."""
        for index, ghost in enumerate(self._ghosts):
            if ghost.state == GhostState.EATEN:
                # Eaten ghosts are just eyes heading home: harmless.
                continue

            if self._collision_detector.entities_collide(self._pacman, ghost):
                self._handle_pacman_ghost_collision(index, ghost)

                if self._game_over:
                    return

    def _handle_pacman_ghost_collision(self, ghost_index: int, ghost: Blinky) -> None:
        """Handle a collision between Pac-Man and a ghost."""
        if ghost.state == GhostState.FRIGHTENED:
            ghost.state = GhostState.EATEN
            ghost.state_timer = self.GHOST_RESPAWN_DELAY
            self.notify(GhostStateChanged(ghost_index, ghost.state))

            self._pacman.add_score(self._points_per_ghost)
            self.notify(ScoreChanged(self._pacman.score))
        else:
            self.notify(PacmanCaught(ghost_index))
            self._lose_life()

    def _lose_life(self) -> None:
        """Remove a life from Pac-Man, ending the game or respawning."""
        self._pacman.lose_life()
        self.notify(LifeLost(self._pacman.lives))

        if self._pacman.lives <= 0:
            self._game_over = True
            self.notify(GameOver(self._pacman.score))
            return

        self._respawn_after_death()

    def _respawn_after_death(self) -> None:
        """Send Pac-Man and every ghost back to their starting position."""
        self._pacman.reset_position(*self._pacman_spawn)
        self._notify_pacman_moved()

        for index, ghost in enumerate(self._ghosts):
            ghost.respawn()
            self.notify(GhostStateChanged(index, ghost.state))
            self._notify_ghost_moved(index, ghost)

        self._level_timer = 0.0

    # -- Notifications -------------------------------------------------

    def _notify_pacman_moved(self) -> None:
        self.notify(
            PacmanMoved(self._pacman.x, self._pacman.y, self._pacman.direction)
        )

    def _notify_ghost_moved(self, index: int, ghost: Blinky) -> None:
        self.notify(GhostMoved(index, ghost.x, ghost.y, ghost.direction))

    # -- Accessors -------------------------------------------------------

    @property
    def maze(self) -> Maze:
        """Return the maze."""
        return self._maze

    @property
    def pacman(self) -> Pacman:
        """Return Pac-Man."""
        return self._pacman

    @property
    def ghosts(self) -> list[Blinky]:
        """Return all ghosts."""
        return self._ghosts

    @property
    def foods(self) -> list[Food]:
        """Return all food."""
        return self._foods

    @property
    def level(self) -> int:
        """Return the current level number (1-based)."""
        return self._level

    @property
    def is_over(self) -> bool:
        """Return True once the game has been lost or won."""
        return self._game_over or self._game_won
