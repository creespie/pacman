"""Events emitted by the model and received by the views."""

from dataclasses import dataclass

from pacman.protocol.enums import Direction, FoodType, GhostState


@dataclass(frozen=True)
class Event:
    """Base class for every event."""


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
class ScoreChanged(Event):
    """The score has changed."""

    score: int


@dataclass(frozen=True)
class PacmanCaught(Event):
    """A ghost has touched Pac-Man."""

    ghost_index: int


@dataclass(frozen=True)
class GhostStateChanged(Event):
    """A ghost switched between chase, frightened and eaten."""

    index: int
    state: GhostState


@dataclass(frozen=True)
class LifeLost(Event):
    """Pac-Man lost a life and respawned."""

    lives: int


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
