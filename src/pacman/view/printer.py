"""Concrete view that renders the game state with MLX."""

from pacman.protocol import (
    Direction,
    FoodCollected,
    FoodSpawned,
    FoodType,
    GhostMoved,
    MazeGenerated,
    PacmanCaught,
    PacmanMoved,
    ScoreChanged,
)
from pacman.view.base import View
from pacman.view.canvas import Canvas

HUD_HEIGHT = 32

WALL_COLOR = 0x2121DE
FLOOR_COLOR = 0x000000
PACGUM_COLOR = 0xFFB897
SUPER_PACGUM_COLOR = 0xFFB897
PACMAN_COLOR = 0xFFFF00
CAUGHT_COLOR = 0xFFFFFF
TEXT_COLOR = 0xFFFFFF
EYE_COLOR = 0xFFFFFF
GHOST_COLORS = (0xFF0000, 0xFFB8FF, 0x00FFFF, 0xFFB852)

CAUGHT_FRAMES = 30


class MlxView(View):
    """Turn the stream of model events into pixels on a Canvas.

    Event handlers only update state; `render` only reads state. The
    maze and the uneaten food live in the canvas background, so a frame
    costs one memcpy plus the few moving entities.
    """

    def __init__(self, canvas: Canvas) -> None:
        self._canvas = canvas
        self._grid: list[list[int]] = []
        self._food: dict[tuple[float, float], FoodType] = {}
        self._pacman: tuple[float, float] = (0.0, 0.0)
        self._direction = Direction.RIGHT
        self._ghosts: dict[int, tuple[float, float]] = {}
        self._score = 0
        self._lives = 3
        self._level = 1
        self._time_left = 0
        self._caught_frames = 0
        self._cell = 0
        self._origin_x = 0
        self._origin_y = 0

    # --- geometry -------------------------------------------------

    def _fit_maze(self, width: int, height: int) -> None:
        """Pick the cell size that fits the maze, and centre it."""
        usable_height = self._canvas.height - HUD_HEIGHT
        self._cell = max(1, min(self._canvas.width // width,
                                usable_height // height))
        self._origin_x = (self._canvas.width - width * self._cell) // 2
        self._origin_y = (usable_height - height * self._cell) // 2

    def _center(self, x: float, y: float) -> tuple[int, int]:
        """Grid coordinates to the pixel at the centre of that cell.

        The model sends floats where the integer part is the cell: if
        it ever sends centres instead, drop the + 0.5 here and nowhere
        else in the codebase.
        """
        return (self._origin_x + int((x + 0.5) * self._cell),
                self._origin_y + int((y + 0.5) * self._cell))

    def _cell_origin(self, x: float, y: float) -> tuple[int, int]:
        """Grid coordinates to the top-left pixel of that cell."""
        return (self._origin_x + int(x) * self._cell,
                self._origin_y + int(y) * self._cell)

    # --- event handlers: state only -------------------------------

    def on_maze_generated(self, event: MazeGenerated) -> None:
        """Store the new maze and repaint the static layer."""
        self._grid = event.grid
        self._food.clear()
        self._fit_maze(event.width, event.height)
        self._redraw_background()

    def on_food_spawned(self, event: FoodSpawned) -> None:
        """Remember a food item and paint it in the static layer."""
        self._food[(event.x, event.y)] = event.kind
        self._draw_food(event.x, event.y, event.kind)

    def on_food_collected(self, event: FoodCollected) -> None:
        """Forget the item and repaint that single cell as floor."""
        self._food.pop((event.x, event.y), None)
        x, y = self._cell_origin(event.x, event.y)
        self._canvas.background.rect(x, y, self._cell, self._cell,
                                     FLOOR_COLOR)

    def on_pacman_moved(self, event: PacmanMoved) -> None:
        """Track Pac-Man's position and facing."""
        self._pacman = (event.x, event.y)
        if event.direction is not Direction.NONE:
            self._direction = event.direction

    def on_ghost_moved(self, event: GhostMoved) -> None:
        """Track one ghost's position."""
        self._ghosts[event.index] = (event.x, event.y)

    def on_score_changed(self, event: ScoreChanged) -> None:
        """Update the score shown in the HUD."""
        self._score = event.score

    def on_pacman_caught(self, event: PacmanCaught) -> None:
        """Flash Pac-Man white for a few frames."""
        self._caught_frames = CAUGHT_FRAMES

    def set_hud(self, lives: int, level: int, time_left: int) -> None:
        """Feed the HUD values the protocol does not carry yet."""
        self._lives = lives
        self._level = level
        self._time_left = time_left

    # --- drawing --------------------------------------------------

    def _redraw_background(self) -> None:
        """Repaint maze and every remaining food item from scratch."""
        background = self._canvas.background
        background.fill(FLOOR_COLOR)
        for row, cells in enumerate(self._grid):
            for col, cell in enumerate(cells):
                if cell == 1:
                    x, y = self._cell_origin(col, row)
                    background.rect(x, y, self._cell, self._cell, WALL_COLOR)
        for (x_pos, y_pos), kind in self._food.items():
            self._draw_food(x_pos, y_pos, kind)

    def _draw_food(self, x: float, y: float, kind: FoodType) -> None:
        """Paint one pacgum in the static layer."""
        if not self._cell:
            return
        center_x, center_y = self._center(x, y)
        if kind is FoodType.SUPER_PACGUM:
            radius = max(3, self._cell // 3)
            color = SUPER_PACGUM_COLOR
        else:
            radius = max(1, self._cell // 8)
            color = PACGUM_COLOR
        self._canvas.background.circle(center_x, center_y, radius, color)

    def _draw_pacman(self) -> None:
        """Body then mouth: the mouth is floor-coloured, so it cuts out."""
        center_x, center_y = self._center(*self._pacman)
        radius = max(2, self._cell // 2 - 1)
        color = CAUGHT_COLOR if self._caught_frames else PACMAN_COLOR
        self._canvas.frame.circle(center_x, center_y, radius, color)
        dx, dy = self._direction.value
        self._canvas.frame.wedge(center_x, center_y, radius, dx, dy,
                                 FLOOR_COLOR)

    def _draw_ghosts(self) -> None:
        """Round head, square skirt, two eyes."""
        radius = max(2, self._cell // 2 - 1)
        for index, (x_pos, y_pos) in self._ghosts.items():
            center_x, center_y = self._center(x_pos, y_pos)
            color = GHOST_COLORS[index % len(GHOST_COLORS)]
            self._canvas.frame.circle(center_x, center_y, radius, color)
            self._canvas.frame.rect(center_x - radius, center_y,
                                    2 * radius + 1, radius + 1, color)
            eye = max(1, radius // 3)
            self._canvas.frame.rect(center_x - eye - 1, center_y - eye,
                                    eye, eye, EYE_COLOR)
            self._canvas.frame.rect(center_x + 1, center_y - eye,
                                    eye, eye, EYE_COLOR)

    def _draw_hud(self) -> None:
        """One line of text under the maze."""
        baseline = self._canvas.height - HUD_HEIGHT // 2
        self._canvas.text(16, baseline, TEXT_COLOR, f"SCORE {self._score}")
        self._canvas.text(180, baseline, TEXT_COLOR, f"LIVES {self._lives}")
        self._canvas.text(300, baseline, TEXT_COLOR, f"LEVEL {self._level}")
        self._canvas.text(420, baseline, TEXT_COLOR, f"TIME {self._time_left}")

    def render(self) -> None:
        """Draw one frame: background copy, entities, HUD, present."""
        if self._caught_frames:
            self._caught_frames -= 1
        self._canvas.begin_frame()
        if self._grid:
            self._draw_pacman()
            self._draw_ghosts()
        self._draw_hud()
        self._canvas.present()