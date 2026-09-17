"""The game state: the model of the MVC architecture."""

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
    GhostMoved,
    MazeGenerated,
    PacmanCaught,
    PacmanMoved,
    ScoreChanged,
    SetDirection,
)
from pacman.utils.observer import Observable


class Game(Observable[Event]):
    """Hold the game state and notify the observers of every change."""

    def __init__(self, config: Config) -> None:
        super().__init__()

        self._points_per_pacgum = config.points_per_pacgum
        self._points_per_super_pacgum = config.points_per_super_pacgum

        # Generate the maze. Every generator cell becomes a 2x2 block plus
        # a one-cell border, so a grid of N cells needs N // 2 generator cells.
        self._maze = Maze(
            MazeGenerator(
                size=(config.width // 2, config.height // 2),
                perfect=False,
                seed=config.seed,
            )
        )

        # Create collision detector.
        self._collision_detector = CollisionDetector(self._maze)

        # Create Pac-Man.
        self._pacman = Pacman(
            x=1.5, y=1.5, radius=0.3, speed=5.0, lives=config.lives
        )

        # Create the ghosts.
        self._ghosts: list[Blinky] = [
            Blinky(x=3.5, y=3.5, radius=0.3, speed=4.0),
        ]

        # Generate food.
        self._foods: list[Food] = []
        self._generate_food()

    def start(self) -> None:
        """Notify the observers of the initial state."""
        self.notify(
            MazeGenerated(self._maze.width, self._maze.height, self._maze.grid)
        )

        for food in self._foods:
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
        self._update_pacman(delta_time)
        self._update_ghosts(delta_time)
        self._check_food_collisions()
        self._check_entity_collisions()

    def _generate_food(self) -> None:
        """Generate food on every walkable maze cell."""
        for y in range(self._maze.height):
            for x in range(self._maze.width):
                if not self._maze.is_walkable(x, y):
                    continue

                self._foods.append(
                    Food(x=x + 0.5, y=y + 0.5, kind=FoodType.PACGUM)
                )

    def _update_pacman(self, delta_time: float) -> None:
        """Update Pac-Man and prevent wall collisions."""
        old_position = self._pacman.position

        self._pacman.update(delta_time)

        if self._collision_detector.entity_hits_wall(self._pacman):
            self._pacman.position = old_position

        if self._pacman.position != old_position:
            self._notify_pacman_moved()

    def _update_ghosts(self, delta_time: float) -> None:
        """Update ghosts and prevent wall collisions."""
        for index, ghost in enumerate(self._ghosts):
            old_position = ghost.position

            ghost.update(delta_time)

            if self._collision_detector.entity_hits_wall(ghost):
                ghost.position = old_position

                # Stop the ghost if it hits a wall.
                ghost.direction = Direction.NONE

            if ghost.position != old_position:
                self._notify_ghost_moved(index, ghost)

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

                    # TODO:
                    # Activate frightened mode for ghosts.

                self.notify(ScoreChanged(self._pacman.score))

    def _food_collides_with_pacman(self, food: Food) -> bool:
        """Return True if Pac-Man touches a food item."""
        distance_x = self._pacman.x - food.x
        distance_y = self._pacman.y - food.y

        distance_squared = distance_x * distance_x + distance_y * distance_y

        # Food is considered a point.
        radius = self._pacman.radius

        return distance_squared < radius * radius

    def _check_entity_collisions(self) -> None:
        """Check collisions between Pac-Man and ghosts."""
        for index, ghost in enumerate(self._ghosts):
            if self._collision_detector.entities_collide(self._pacman, ghost):
                self._handle_pacman_ghost_collision(index)

    def _handle_pacman_ghost_collision(self, ghost_index: int) -> None:
        """Handle a collision between Pac-Man and a ghost."""
        # TODO:
        # If the ghost is frightened:
        #     Pac-Man gets points.
        #     Ghost respawns.
        #
        # Otherwise:
        #     Pac-Man loses a life.

        self.notify(PacmanCaught(ghost_index))

    def _notify_pacman_moved(self) -> None:
        self.notify(
            PacmanMoved(self._pacman.x, self._pacman.y, self._pacman.direction)
        )

    def _notify_ghost_moved(self, index: int, ghost: Blinky) -> None:
        self.notify(GhostMoved(index, ghost.x, ghost.y, ghost.direction))

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
