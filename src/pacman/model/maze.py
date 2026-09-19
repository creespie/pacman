from math import ceil, floor

from mazegenerator import MazeGenerator


WALL = 1
FLOOR = 0

NORTH = 1
EAST = 2
SOUTH = 4
WEST = 8
BLOCKED = NORTH | EAST | SOUTH | WEST


class Maze:
    """Represents the generated maze as a spatial 2D grid."""

    def __init__(self, generator: MazeGenerator) -> None:
        self._generator = generator
        self._grid = self._build_grid()

    def _build_grid(self) -> list[list[int]]:
        """Convert MazeGenerator output into a spatial 0/1 grid."""
        source = self._generator.maze

        source_height = len(source)
        source_width = len(source[0])

        height = source_height * 2 + 1
        width = source_width * 2 + 1

        grid = [
            [WALL for _ in range(width)]
            for _ in range(height)
        ]

        for y in range(source_height):
            for x in range(source_width):
                cell = source[y][x]

                # The 42 cells are completely blocked.
                if cell == BLOCKED:
                    continue

                grid_y = y * 2 + 1
                grid_x = x * 2 + 1

                # The cell itself is walkable.
                grid[grid_y][grid_x] = FLOOR

                # North.
                if not (cell & NORTH):
                    grid[grid_y - 1][grid_x] = FLOOR

                # East.
                if not (cell & EAST):
                    grid[grid_y][grid_x + 1] = FLOOR

                # South.
                if not (cell & SOUTH):
                    grid[grid_y + 1][grid_x] = FLOOR

                # West.
                if not (cell & WEST):
                    grid[grid_y][grid_x - 1] = FLOOR

        return grid

    @property
    def grid(self) -> list[list[int]]:
        """Return the maze grid."""
        return self._grid

    @property
    def width(self) -> int:
        """Return the maze width."""
        return len(self._grid[0])

    @property
    def height(self) -> int:
        """Return the maze height."""
        return len(self._grid)

    def is_walkable(self, x: int, y: int) -> bool:
        """Return True if the given grid position is walkable."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False

        return self._grid[y][x] == FLOOR

    def is_colliding(self, x: float, y: float, radius: float) -> bool:
        """Return True if a circle intersects a maze wall."""
        min_x = floor(x - radius)
        max_x = ceil(x + radius)
        min_y = floor(y - radius)
        max_y = ceil(y + radius)

        for grid_y in range(min_y, max_y + 1):
            for grid_x in range(min_x, max_x + 1):

                # Outside the maze is considered a wall.
                if not (0 <= grid_x < self.width):
                    return True

                if not (0 <= grid_y < self.height):
                    return True

                # Ignore walkable cells.
                if self._grid[grid_y][grid_x] == FLOOR:
                    continue

                # The wall cell occupies this square.
                wall_left = grid_x
                wall_right = grid_x + 1
                wall_top = grid_y
                wall_bottom = grid_y + 1

                # Find the closest point of the wall to the circle.
                closest_x = max(wall_left, min(x, wall_right))
                closest_y = max(wall_top, min(y, wall_bottom))

                distance_x = x - closest_x
                distance_y = y - closest_y

                distance_squared = (
                    distance_x * distance_x
                    + distance_y * distance_y
                )

                if distance_squared <= radius * radius:
                    return True

        return False

    def __str__(self) -> str:
        """Return the maze as rows of 0 and 1."""
        return "\n".join(
            " ".join(str(cell) for cell in row)
            for row in self._grid
        )
