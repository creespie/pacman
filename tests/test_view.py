"""The view must stay inside MiniLibX's per-frame drawing budget.

MiniLibX flushes its draw list to the screen as soon as 64 blits are
queued, and every character of text is one blit. A frame that goes over
that budget is presented in two pieces and flickers, so the screen that
is redrawn sixty times a second has to stay under it.
"""

from typing import cast

from pacman.protocol import (
    Direction,
    FoodSpawned,
    FoodType,
    GhostMoved,
    LevelStarted,
    LivesChanged,
    MazeGenerated,
    MenuChanged,
    PacmanMoved,
    ScoreChanged,
    Screen,
    ScreenChanged,
    TimeChanged,
)
from pacman.view.canvas import MAX_DRAWS_PER_FRAME, Canvas
from pacman.view.mlx_view import MlxView


class FakeImage:
    """An image that counts nothing and draws nothing."""

    def fill(self, color: int) -> None:
        """Ignore a fill."""

    def rect(
        self, x: int, y: int, width: int, height: int, color: int
    ) -> None:
        """Ignore a rectangle."""

    def circle(self, x: int, y: int, radius: int, color: int) -> None:
        """Ignore a disc."""

    def wedge(
        self, x: int, y: int, radius: int, dx: float, dy: float, color: int
    ) -> None:
        """Ignore a wedge."""


class FakeCanvas:
    """A canvas that only records what a frame would cost."""

    def __init__(self, width: int = 700, height: int = 620) -> None:
        self.width = width
        self.height = height
        self.frame = FakeImage()
        self.background = FakeImage()
        self.texts: list[str] = []
        self.presents = 0

    def begin_frame(self) -> None:
        """Start a frame."""

    def text(self, x: int, y: int, color: int, value: str) -> None:
        """Record a line of text."""
        self.texts.append(value)

    @property
    def draw_count(self) -> int:
        """The frame itself, plus one blit per character of text."""
        return 1 + sum(len(text) for text in self.texts)

    def present(self) -> None:
        """Count the frame and drop the queued text, as MLX does."""
        self.presents += 1
        self.texts.clear()


def make_view() -> tuple[MlxView, FakeCanvas]:
    """A view showing a started level, on a fake canvas."""
    canvas = FakeCanvas()
    view = MlxView(cast(Canvas, canvas))

    view.update(MazeGenerated(11, 11, [[0] * 11 for _ in range(11)]))
    view.update(LevelStarted(10, 10, 90))
    view.update(ScoreChanged(123456))
    view.update(LivesChanged(3))
    view.update(TimeChanged(90))
    view.update(PacmanMoved(5.5, 5.5, Direction.LEFT))

    for index in range(4):
        view.update(GhostMoved(index, 1.5, 1.5, Direction.UP))

    for cell in range(10):
        view.update(FoodSpawned(cell + 0.5, 1.5, FoodType.PACGUM))

    return view, canvas


def test_game_frame_fits_the_draw_budget() -> None:
    """The HUD is the only text in game, and it has to stay small."""
    view, canvas = make_view()
    view.update(ScreenChanged(Screen.PLAYING))
    view.render()

    assert canvas.presents == 1
    assert canvas.draw_count <= MAX_DRAWS_PER_FRAME


def test_static_screens_are_not_repainted() -> None:
    """A menu is drawn once, then left alone until something changes."""
    view, canvas = make_view()
    view.update(ScreenChanged(Screen.MENU))
    view.update(MenuChanged(("Start Game", "Exit"), 0))

    view.render()
    view.render()
    view.render()

    assert canvas.presents == 1

    view.update(MenuChanged(("Start Game", "Exit"), 1))
    view.render()

    assert canvas.presents == 2


def test_an_uncovered_window_is_repainted() -> None:
    """invalidate() is what the expose hook calls."""
    view, canvas = make_view()
    view.update(ScreenChanged(Screen.MENU))
    view.render()

    view.invalidate()
    view.render()

    assert canvas.presents == 2


def test_a_running_game_is_repainted_every_frame() -> None:
    """Pac-Man moves, so the game screen cannot be skipped."""
    view, canvas = make_view()
    view.update(ScreenChanged(Screen.PLAYING))

    for _ in range(5):
        view.render()

    assert canvas.presents == 5
