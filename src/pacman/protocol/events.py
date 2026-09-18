"""Events emitted by the model and the session, received by the views.

Coordinate convention (the single source of truth for the whole
project): every ``x``/``y`` pair in an event is the **centre of a maze
cell or a point inside it**, expressed in cells. The cell containing a
point is therefore ``(int(x), int(y))`` and the centre of the cell
``(col, row)`` is ``(col + 0.5, row + 0.5)``.

A view must never add or remove half a cell on its own.
"""

from dataclasses import dataclass, field

from pacman.protocol.enums import Direction, FoodType, GhostState, Screen


@dataclass(frozen=True)
class Event:
    """Base class for every event."""


# -- Level content ------------------------------------------------------


@dataclass(frozen=True)
class MazeGenerated(Event):
    """The maze is ready: 0 is a floor cell, 1 is a wall cell."""

    width: int
    height: int
    grid: list[list[int]]


@dataclass(frozen=True)
class FoodSpawned(Event):
    """A food item has been placed in the maze."""

    x: float
    y: float
    kind: FoodType


@dataclass(frozen=True)
class FoodCollected(Event):
    """Pac-Man has eaten a food item."""

    x: float
    y: float
    kind: FoodType


# -- Entities -----------------------------------------------------------


@dataclass(frozen=True)
class PacmanMoved(Event):
    """Pac-Man has changed position."""

    x: float
    y: float
    direction: Direction


@dataclass(frozen=True)
class GhostMoved(Event):
    """A ghost has changed position."""

    index: int
    x: float
    y: float
    direction: Direction


@dataclass(frozen=True)
class GhostStateChanged(Event):
    """A ghost switched between chase, frightened and eaten."""

    index: int
    state: GhostState


@dataclass(frozen=True)
class PacmanCaught(Event):
    """A ghost has touched Pac-Man."""

    ghost_index: int


# -- HUD ----------------------------------------------------------------


@dataclass(frozen=True)
class ScoreChanged(Event):
    """The score has changed."""

    score: int


@dataclass(frozen=True)
class LivesChanged(Event):
    """The number of remaining lives has changed."""

    lives: int


@dataclass(frozen=True)
class LevelStarted(Event):
    """A level has just been (re)built and is about to be played."""

    level: int
    total_levels: int
    time_limit: int


@dataclass(frozen=True)
class TimeChanged(Event):
    """The remaining time of the current level, in whole seconds."""

    seconds_left: int


@dataclass(frozen=True)
class CheatsChanged(Event):
    """Cheat mode was toggled, or one of its flags changed."""

    enabled: bool
    invincible: bool = False
    ghosts_frozen: bool = False
    speed_boost: bool = False


# -- End of level / end of game -----------------------------------------


@dataclass(frozen=True)
class LevelCompleted(Event):
    """Every pacgum and super-pacgum of the level has been eaten."""

    level: int


@dataclass(frozen=True)
class GameOver(Event):
    """Pac-Man has no lives left."""

    score: int


@dataclass(frozen=True)
class GameWon(Event):
    """Every level has been completed."""

    score: int


# -- Session (screen flow) ----------------------------------------------


@dataclass(frozen=True)
class ScreenChanged(Event):
    """The player moved to another screen."""

    screen: Screen


@dataclass(frozen=True)
class MenuChanged(Event):
    """The entries of the active menu, and the highlighted one."""

    items: tuple[str, ...] = ()
    selected: int = 0


@dataclass(frozen=True)
class HighscoresChanged(Event):
    """The stored highscores, best first."""

    entries: tuple[tuple[str, int], ...] = field(default=())


@dataclass(frozen=True)
class NameEntryChanged(Event):
    """The name the player is typing on the game over / victory screen."""

    name: str
    score: int
