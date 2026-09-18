"""Run the MLX view without the model, on fake events.

Launch from the project root:  python3 -m pacman.view.demo
Arrow keys to move, ESC to quit.

This is a throwaway harness: it fakes just enough of a model to prove
the view works, so you can develop the graphics and the game logic in
parallel instead of waiting for each other.
"""

import random

from pacman.protocol import (
    Direction,
    FoodCollected,
    FoodSpawned,
    FoodType,
    GhostMoved,
    MazeGenerated,
    PacmanMoved,
    ScoreChanged,
)
from pacman.view.canvas import ESCAPE_KEY, Canvas
from pacman.view.printer import MlxView

WINDOW_WIDTH = 720
WINDOW_HEIGHT = 560
SPEED = 0.12

KEYS = {
    65361: Direction.LEFT,
    65362: Direction.UP,
    65363: Direction.RIGHT,
    65364: Direction.DOWN,
    97: Direction.LEFT,     # a
    119: Direction.UP,      # w
    100: Direction.RIGHT,   # d
    115: Direction.DOWN,    # s
}


def build_maze(width: int, height: int) -> list[list[int]]:
    """A fake maze: border walls plus a grid of blocks."""
    return [
        [1 if (row in (0, height - 1) or col in (0, width - 1)
               or (row % 2 == 0 and col % 3 == 0)) else 0
         for col in range(width)]
        for row in range(height)
    ]


class FakeModel:
    """Minimal moving state, emitting the same events as the real model."""

    def __init__(self, view: MlxView, width: int, height: int) -> None:
        self._view = view
        self._width = width
        self._height = height
        self._grid = build_maze(width, height)
        self._x = width // 2 + 0.0
        self._y = height // 2 + 0.0
        self._direction = Direction.NONE
        self._ghosts = [(1.0, 1.0), (width - 2.0, 1.0),
                        (1.0, height - 2.0), (width - 2.0, height - 2.0)]
        self._score = 0
        self._ticks = 0
        self._emit_level()

    def _emit_level(self) -> None:
        """Send the events a real level start would send."""
        self._view.update(MazeGenerated(self._width, self._height, self._grid))
        for row in range(self._height):
            for col in range(self._width):
                if self._grid[row][col] == 0:
                    self._view.update(
                        FoodSpawned(float(col), float(row), FoodType.PACGUM))
        for col, row in ((1, 1), (self._width - 2, 1),
                         (1, self._height - 2),
                         (self._width - 2, self._height - 2)):
            self._view.update(
                FoodSpawned(float(col), float(row), FoodType.SUPER_PACGUM))
        self._view.update(ScoreChanged(0))
        for index, (x_pos, y_pos) in enumerate(self._ghosts):
            self._view.update(
                GhostMoved(index, x_pos, y_pos, Direction.NONE))

    def _blocked(self, x: float, y: float) -> bool:
        """True if the 1x1 body at (x, y) overlaps a wall.

        An entity is a full cell wide, so between two cells it straddles
        two columns (or rows): testing only int(x) would let it sink
        half a cell into the wall before stopping.
        """
        for col in {int(x), int(x + 0.999)}:
            for row in {int(y), int(y + 0.999)}:
                if not (0 <= row < self._height and 0 <= col < self._width):
                    return True
                if self._grid[row][col] == 1:
                    return True
        return False

    @staticmethod
    def _snap(value: float) -> float:
        """Round to the grid when already almost aligned with it."""
        nearest = round(value)
        return float(nearest) if abs(value - nearest) < SPEED else value

    def set_direction(self, direction: Direction) -> None:
        """Queue a new direction for Pac-Man."""
        self._direction = direction

    def tick(self) -> None:
        """Advance one frame and emit the resulting events."""
        self._ticks += 1
        dx, dy = self._direction.value
        # Snap the idle axis: float drift of 1e-9 is enough to make the
        # body straddle two columns and get stuck against a corner.
        if dx:
            self._y = self._snap(self._y)
        elif dy:
            self._x = self._snap(self._x)
        next_x = self._x + dx * SPEED
        next_y = self._y + dy * SPEED
        if not self._blocked(next_x, next_y):
            self._x, self._y = next_x, next_y
            self._view.update(
                PacmanMoved(self._x, self._y, self._direction))
            self._eat()
        if self._ticks % 8 == 0:
            self._move_ghosts()

    def _eat(self) -> None:
        """Eat the pacgum of the cell Pac-Man is standing on."""
        cell = (float(int(self._x + 0.5)), float(int(self._y + 0.5)))
        self._view.update(FoodCollected(cell[0], cell[1], FoodType.PACGUM))
        self._score += 10
        self._view.update(ScoreChanged(self._score))

    def _move_ghosts(self) -> None:
        """Random walk, one cell at a time."""
        for index, (x_pos, y_pos) in enumerate(self._ghosts):
            choices = [d for d in Direction if d is not Direction.NONE]
            random.shuffle(choices)
            for direction in choices:
                dx, dy = direction.value
                new_x, new_y = x_pos + dx, y_pos + dy
                if not self._blocked(new_x, new_y):
                    self._ghosts[index] = (new_x, new_y)
                    self._view.update(
                        GhostMoved(index, new_x, new_y, direction))
                    break


def main() -> None:
    """Wire canvas, view and fake model together, then run the loop."""
    canvas = Canvas(WINDOW_WIDTH, WINDOW_HEIGHT, "Pacman - view demo")
    view = MlxView(canvas)
    model = FakeModel(view, 21, 15)
    view.set_hud(lives=3, level=1, time_left=90)

    def on_key(keycode: int) -> None:
        print("keycode:", keycode)
        if keycode == ESCAPE_KEY:
            canvas.stop()
        elif keycode in KEYS:
            model.set_direction(KEYS[keycode])

    def on_tick() -> None:
        model.tick()
        view.render()

    canvas.on_key(on_key)
    canvas.on_tick(on_tick)
    canvas.run()


if __name__ == "__main__":
    main()