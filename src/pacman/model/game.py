"""The game state: the model of the MVC architecture.

The model owns every rule of the game and never draws anything. It
describes what it does through the events of ``pacman.protocol``, which
the views turn into pixels. Positions sent in those events are always
cell centres (see the module docstring of ``protocol.events``).
"""

import random

from mazegenerator import MazeGenerator

from pacman.config import Config
from pacman.model.collision import CollisionDetector
from pacman.model.entities import Blinky, Pacman
from pacman.model.food import Food
from pacman.model.maze import Maze
from pacman.protocol import (
    Cheat,
    CheatsChanged,
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
    LevelStarted,
    LivesChanged,
    MazeGenerated,
    PacmanCaught,
    PacmanMoved,
    ScoreChanged,
    SetDirection,
    TimeChanged,
    ToggleCheatMode,
    UseCheat,
)
from pacman.utils.observer import Observable

_ALL_DIRECTIONS = (
    Direction.UP,
    Direction.DOWN,
    Direction.LEFT,
    Direction.RIGHT,
)

_OPPOSITE_DIRECTIONS = {
    Direction.UP: Direction.DOWN,
    Direction.DOWN: Direction.UP,
    Direction.LEFT: Direction.RIGHT,
    Direction.RIGHT: Direction.LEFT,
    Direction.NONE: Direction.NONE,
}

# Speed multiplier applied by the "fast Pac-Man" cheat.
_CHEAT_SPEED_FACTOR = 1.8


class Game(Observable[Event]):
    """Hold the game state and notify the observers of every change."""

    # How long ghosts stay edible after Pac-Man eats a super-pacgum.
    FRIGHTENED_DURATION = 8.0

    # How long an eaten ghost stays away before it respawns at home.
    GHOST_RESPAWN_DELAY = 7.0

    PACMAN_SPEED = 5.0
    GHOST_SPEED = 4.0
    ENTITY_RADIUS = 0.3

    # How far from a cell centre Pac-Man may still take a turn. Unlike
    # the tolerance of _is_centred, this is not a frame-rate matter but
    # a geometric one: the snap that follows moves him by at most this
    # much, and with a radius of 0.3 in a corridor one cell wide there
    # is room to spare. Widening this window is what keeps the controls
    # responsive - at 5 cells per second a centre goes by every 200 ms,
    # and a window of one frame would throw most inputs away.
    TURN_WINDOW = 0.2

    # A turn asked for too long ago is dropped instead of firing at some
    # later intersection, which felt like Pac-Man turning on his own.
    TURN_REQUEST_TIMEOUT = 0.3

    def __init__(self, config: Config) -> None:
        super().__init__()

        self._config = config
        self._level = 1
        self._time_left = float(config.level_max_time)
        self._game_over = False
        self._game_won = False

        # Game time, used to expire a turn request. It follows the
        # model and not the wall clock, so it stops when the game is
        # paused and stays reproducible in the tests.
        self._elapsed = 0.0
        self._request_time = 0.0

        self._cheats_enabled = False
        self._invincible = False
        self._ghosts_frozen = False
        self._speed_boost = False

        # Pac-Man is created once: his lives and his score have to
        # survive both a respawn and a level change.
        self._pacman = Pacman(
            x=1.5,
            y=1.5,
            radius=self.ENTITY_RADIUS,
            speed=self.PACMAN_SPEED,
            lives=config.lives,
        )
        self._spawn = (1.5, 1.5)

        self._maze: Maze
        self._collisions: CollisionDetector
        self._ghosts: list[Blinky] = []
        self._foods: list[Food] = []

        self._setup_level(config.seed)

    # -- Level setup -----------------------------------------------------

    def _setup_level(self, seed: int) -> None:
        """(Re)generate the maze, the ghosts and the food for a level.

        Raises:
            RuntimeError: If the external generator cannot produce a
                usable maze; the caller turns it into a clean message.
        """
        self._maze = self._generate_maze(seed)
        self._collisions = CollisionDetector(self._maze)

        self._spawn = self._nearest_walkable_center(
            self._maze.width // 2, self._maze.height // 2
        )
        self._pacman.reset_position(*self._spawn)

        self._ghosts = self._spawn_ghosts()
        self._foods = self._generate_food()

        self._time_left = float(self._config.level_max_time)

    def _generate_maze(self, seed: int) -> Maze:
        """Build a maze with the external A-Maze-ing package.

        Every generator cell becomes a 2x2 block plus a one-cell border,
        so a grid of N cells needs N // 2 generator cells.
        """
        try:
            generator = MazeGenerator(
                size=(self._config.width // 2, self._config.height // 2),
                perfect=False,
                seed=seed,
            )

            return Maze(generator)
        except Exception as error:  # the package is not ours: trust nothing
            raise RuntimeError(
                f"maze generation failed (seed {seed}): {error}"
            ) from error

    def _spawn_ghosts(self) -> list[Blinky]:
        """Create one ghost in each corner of the maze."""
        return [
            Blinky(
                x=x,
                y=y,
                radius=self.ENTITY_RADIUS,
                speed=self.GHOST_SPEED,
            )
            for x, y in (
                self._nearest_walkable_center(cell_x, cell_y)
                for cell_x, cell_y in self._corner_cells()
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
            for offset_x in range(-radius, radius + 1):
                for offset_y in range(-radius, radius + 1):
                    candidate_x = x + offset_x
                    candidate_y = y + offset_y

                    if self._maze.is_walkable(candidate_x, candidate_y):
                        return candidate_x + 0.5, candidate_y + 0.5

        # Should never happen on a maze that has at least one corridor.
        return x + 0.5, y + 0.5

    def _generate_food(self) -> list[Food]:
        """Place a super-pacgum in each corner and pacgums elsewhere.

        ``config.pacgum`` caps how many pacgums a level holds. When it is
        larger than the number of corridors (the shipped default), every
        corridor gets one, as in the original game; a smaller value
        spreads them evenly instead of crowding one part of the maze.
        """
        corners = {
            self._nearest_walkable_center(cell_x, cell_y)
            for cell_x, cell_y in self._corner_cells()
        }

        foods = [
            Food(x=x, y=y, kind=FoodType.SUPER_PACGUM) for x, y in corners
        ]

        corridors = [
            (x + 0.5, y + 0.5)
            for y in range(self._maze.height)
            for x in range(self._maze.width)
            if self._maze.is_walkable(x, y)
            and (x + 0.5, y + 0.5) not in corners
        ]

        foods.extend(
            Food(x=x, y=y, kind=FoodType.PACGUM)
            for x, y in self._select_spread(corridors, self._config.pacgum)
        )

        return foods

    @staticmethod
    def _select_spread(
        cells: list[tuple[float, float]], maximum: int
    ) -> list[tuple[float, float]]:
        """Return at most ``maximum`` cells, evenly spread over ``cells``."""
        if maximum >= len(cells):
            return cells

        step = len(cells) / maximum

        return [cells[int(index * step)] for index in range(maximum)]

    # -- Lifecycle -------------------------------------------------------

    def start(self) -> None:
        """Notify the observers of the whole initial state."""
        self._notify_level_state()

    def _notify_level_state(self) -> None:
        """Send everything a view needs to draw the current level."""
        self.notify(
            MazeGenerated(self._maze.width, self._maze.height, self._maze.grid)
        )
        self.notify(
            LevelStarted(
                self._level,
                self._config.levels,
                self._config.level_max_time,
            )
        )

        for food in self._foods:
            if not food.collected:
                self.notify(FoodSpawned(food.x, food.y, food.kind))

        self._notify_pacman_moved()

        for index, ghost in enumerate(self._ghosts):
            self.notify(GhostStateChanged(index, ghost.state))
            self._notify_ghost_moved(index, ghost)

        self.notify(ScoreChanged(self._pacman.score))
        self.notify(LivesChanged(self._pacman.lives))
        self.notify(TimeChanged(int(self._time_left)))
        self._notify_cheats()

    def handle(self, command: Command) -> None:
        """Apply a command coming from a controller."""
        match command:
            case SetDirection(direction=direction):
                self._request_direction(direction)
            case ToggleCheatMode():
                self._toggle_cheat_mode()
            case UseCheat(cheat=cheat):
                self._use_cheat(cheat)

    def update(self, delta_time: float) -> None:
        """Advance the game by ``delta_time`` seconds."""
        if self.is_over:
            return

        self._elapsed += delta_time
        self._update_timer(delta_time)

        if self.is_over:
            return

        self._update_pacman(delta_time)
        self._update_ghosts(delta_time)
        self._check_food_collisions()
        self._check_entity_collisions()

        if self.is_over:
            return

        self._check_level_complete()

    # -- Level timer -----------------------------------------------------

    def _update_timer(self, delta_time: float) -> None:
        """Count the level time down and react when it runs out."""
        previous = int(self._time_left)
        self._time_left = max(0.0, self._time_left - delta_time)

        if int(self._time_left) != previous:
            self.notify(TimeChanged(int(self._time_left)))

        if self._time_left <= 0.0:
            # Running out of time costs a life and restarts the level.
            self._lose_life()

    # -- Pac-Man ---------------------------------------------------------

    def _update_pacman(self, delta_time: float) -> None:
        """Turn if the player asked to, then move and stop at walls."""
        self._apply_requested_direction(delta_time)

        old_position = self._pacman.position
        self._pacman.update(delta_time)

        if self._collisions.entity_hits_wall(self._pacman):
            self._pacman.position = self._collisions.clip_to_wall(
                self._pacman.radius, old_position, self._pacman.position
            )
            self._pacman.direction = Direction.NONE

            # Snap to the centre of the cell Pac-Man is currently in,
            # so _is_centred and _is_open work correctly next frame.
            cell_x = int(self._pacman.x)
            cell_y = int(self._pacman.y)
            self._pacman.position = (cell_x + 0.5, cell_y + 0.5)

        if self._pacman.position != old_position:
            self._notify_pacman_moved()

    def _request_direction(self, direction: Direction) -> None:
        """Remember the direction the player wants to take, and when."""
        self._pacman.next_direction = direction
        self._request_time = self._elapsed

        # Turning back is always possible: no need to wait for a centre.
        if direction == _OPPOSITE_DIRECTIONS[self._pacman.direction]:
            self._pacman.direction = direction

    def _apply_requested_direction(self, delta_time: float) -> None:
        """Apply the requested direction once Pac-Man can take it."""
        wanted = self._pacman.next_direction

        if wanted is Direction.NONE or wanted == self._pacman.direction:
            return

        if self._elapsed - self._request_time > self.TURN_REQUEST_TIMEOUT:
            self._pacman.next_direction = Direction.NONE
            return

        if not self._can_turn(delta_time):
            return

        cell_x, cell_y = int(self._pacman.x), int(self._pacman.y)

        if not self._is_open(cell_x, cell_y, wanted):
            return

        # Snapping removes the fraction of a cell lost between two
        # frames, so corridors stay perfectly aligned over time.
        self._pacman.position = (cell_x + 0.5, cell_y + 0.5)
        self._pacman.direction = wanted

    # -- Ghosts ----------------------------------------------------------

    def _update_ghosts(self, delta_time: float) -> None:
        """Update ghosts: state timers, steering, movement and walls."""
        for index, ghost in enumerate(self._ghosts):
            self._update_ghost_state(index, ghost, delta_time)

            if ghost.state == GhostState.EATEN or self._ghosts_frozen:
                # Eaten ghosts wait invisibly until they respawn.
                continue

            self._steer_ghost(ghost, delta_time)

            old_position = ghost.position
            ghost.update(delta_time)

            if self._collisions.entity_hits_wall(ghost):
                ghost.position = self._collisions.clip_to_wall(
                    ghost.radius, old_position, ghost.position
                )
                ghost.direction = Direction.NONE

                # Snap to the centre of the cell the ghost is currently
                # in, so _is_centred (and therefore _steer_ghost) can
                # succeed next frame instead of leaving the ghost stuck
                # wherever clip_to_wall's binary search happened to land.
                cell_x = int(ghost.x)
                cell_y = int(ghost.y)
                ghost.position = (cell_x + 0.5, cell_y + 0.5)

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

    def _steer_ghost(self, ghost: Blinky, delta_time: float) -> None:
        """Pick a new direction for a ghost when it reaches a centre."""
        if not self._is_centred(ghost, delta_time):
            return

        cell_x, cell_y = int(ghost.x), int(ghost.y)
        ghost.position = (cell_x + 0.5, cell_y + 0.5)

        candidates = [
            direction
            for direction in _ALL_DIRECTIONS
            if self._is_open(cell_x, cell_y, direction)
        ]

        if not candidates:
            ghost.direction = Direction.NONE
            return

        # Ghosts never turn back, unless it is the only way out.
        opposite = _OPPOSITE_DIRECTIONS[ghost.direction]
        options = [d for d in candidates if d != opposite] or candidates

        flee = ghost.state == GhostState.FRIGHTENED

        def score(direction: Direction) -> float:
            step_x, step_y = direction.value
            next_x = cell_x + step_x + 0.5
            next_y = cell_y + step_y + 0.5
            distance = (next_x - self._pacman.x) ** 2 + (
                next_y - self._pacman.y
            ) ** 2

            # Chase: get as close as possible. Frightened: run away.
            return -distance if flee else distance

        ghost.direction = min(options, key=score)

    # -- Grid helpers ----------------------------------------------------

    @staticmethod
    def _is_centred(entity: Blinky | Pacman, delta_time: float) -> bool:
        """Return True if an entity is close enough to a cell centre.

        The tolerance follows the distance covered in one frame: an
        entity moving ``s`` cells per frame is never sampled more than
        ``s / 2`` away from a centre it goes through, so a fixed epsilon
        would silently skip intersections as soon as the frame rate
        dropped.
        """
        tolerance = entity.speed * delta_time / 2 + 1e-9
        offset_x = entity.x - int(entity.x) - 0.5
        offset_y = entity.y - int(entity.y) - 0.5

        return abs(offset_x) <= tolerance and abs(offset_y) <= tolerance

    def _can_turn(self, delta_time: float) -> bool:
        """Return True if Pac-Man is close enough to a centre to turn.

        This is the player-facing half of _is_centred, and it uses a
        fixed window instead of a frame-relative one. The max keeps the
        guarantee of _is_centred anyway: below roughly twelve frames per
        second a single step is longer than TURN_WINDOW, and a fixed
        window alone would be stepped straight over.
        """
        tolerance = max(
            self.TURN_WINDOW, self._pacman.speed * delta_time / 2
        )
        offset_x = self._pacman.x - int(self._pacman.x) - 0.5
        offset_y = self._pacman.y - int(self._pacman.y) - 0.5

        return abs(offset_x) <= tolerance and abs(offset_y) <= tolerance

    def _is_open(self, cell_x: int, cell_y: int, direction: Direction) -> bool:
        """Return True if the neighbour cell in ``direction`` is a floor."""
        step_x, step_y = direction.value

        return self._maze.is_walkable(
            cell_x + int(step_x), cell_y + int(step_y)
        )

    # -- Food ------------------------------------------------------------

    def _check_food_collisions(self) -> None:
        """Check if Pac-Man collects any food."""
        for food in self._foods:
            if food.collected:
                continue

            if not self._food_collides_with_pacman(food):
                continue

            food.collect()
            self.notify(FoodCollected(food.x, food.y, food.kind))

            if food.kind == FoodType.PACGUM:
                self._pacman.add_score(self._config.points_per_pacgum)
            else:
                self._pacman.add_score(self._config.points_per_super_pacgum)
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

        self._complete_level()

    def _complete_level(self) -> None:
        """Win the current level, then the game or the next level."""
        self.notify(LevelCompleted(self._level))

        if self._level >= self._config.levels:
            self._game_won = True
            self.notify(GameWon(self._pacman.score))
            return

        self._level += 1

        # The first level uses the configured seed; every level after it
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

            if self._collisions.entities_collide(self._pacman, ghost):
                self._handle_ghost_collision(index, ghost)

                if self.is_over:
                    return

    def _handle_ghost_collision(self, index: int, ghost: Blinky) -> None:
        """Handle a collision between Pac-Man and a ghost."""
        if ghost.state == GhostState.FRIGHTENED:
            ghost.state = GhostState.EATEN
            ghost.state_timer = self.GHOST_RESPAWN_DELAY
            self.notify(GhostStateChanged(index, ghost.state))

            self._pacman.add_score(self._config.points_per_ghost)
            self.notify(ScoreChanged(self._pacman.score))
            return

        if self._invincible:
            return

        self.notify(PacmanCaught(index))
        self._lose_life()

    def _lose_life(self) -> None:
        """Remove a life from Pac-Man, ending the game or respawning."""
        self._pacman.lose_life()
        self.notify(LivesChanged(self._pacman.lives))

        if self._pacman.lives <= 0:
            self._game_over = True
            self.notify(GameOver(self._pacman.score))
            return

        self._respawn_after_death()

    def _respawn_after_death(self) -> None:
        """Send Pac-Man and every ghost back to their starting position."""
        self._pacman.reset_position(*self._spawn)
        self._notify_pacman_moved()

        for index, ghost in enumerate(self._ghosts):
            ghost.respawn()
            self.notify(GhostStateChanged(index, ghost.state))
            self._notify_ghost_moved(index, ghost)

        self._time_left = float(self._config.level_max_time)
        self.notify(TimeChanged(int(self._time_left)))

    # -- Cheat mode ------------------------------------------------------

    def _toggle_cheat_mode(self) -> None:
        """Enable or disable cheat mode, resetting its flags when off."""
        self._cheats_enabled = not self._cheats_enabled

        if not self._cheats_enabled:
            self._invincible = False
            self._ghosts_frozen = False
            self._speed_boost = False
            self._pacman.speed = self._pacman.base_speed

        self._notify_cheats()

    def _use_cheat(self, cheat: Cheat) -> None:
        """Apply one cheat, if cheat mode is currently enabled."""
        if not self._cheats_enabled:
            return

        match cheat:
            case Cheat.INVINCIBILITY:
                self._invincible = not self._invincible
            case Cheat.FREEZE_GHOSTS:
                self._ghosts_frozen = not self._ghosts_frozen
            case Cheat.SPEED:
                self._speed_boost = not self._speed_boost
                factor = _CHEAT_SPEED_FACTOR if self._speed_boost else 1.0
                self._pacman.speed = self._pacman.base_speed * factor
            case Cheat.EXTRA_LIFE:
                self._pacman.add_life()
                self.notify(LivesChanged(self._pacman.lives))
            case Cheat.SKIP_LEVEL:
                for food in self._foods:
                    food.collect()

                self._complete_level()

        self._notify_cheats()

    # -- Notifications ---------------------------------------------------

    def _notify_pacman_moved(self) -> None:
        """Tell the observers where Pac-Man is and where he faces."""
        self.notify(
            PacmanMoved(self._pacman.x, self._pacman.y, self._pacman.direction)
        )

    def _notify_ghost_moved(self, index: int, ghost: Blinky) -> None:
        """Tell the observers where one ghost is."""
        self.notify(GhostMoved(index, ghost.x, ghost.y, ghost.direction))

    def _notify_cheats(self) -> None:
        """Tell the observers which cheats are currently active."""
        self.notify(
            CheatsChanged(
                self._cheats_enabled,
                self._invincible,
                self._ghosts_frozen,
                self._speed_boost,
            )
        )

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
    def score(self) -> int:
        """Return the current score."""
        return self._pacman.score

    @property
    def is_won(self) -> bool:
        """Return True once every level has been completed."""
        return self._game_won

    @property
    def is_over(self) -> bool:
        """Return True once the game has been lost or won."""
        return self._game_over or self._game_won
