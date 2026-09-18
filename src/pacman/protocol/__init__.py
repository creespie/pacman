"""Messages exchanged between model, views and controllers.

Everything here is plain data with primitive fields, so that it can be
serialized (e.g. to JSON over a WebSocket) without changes.
"""

from pacman.protocol.commands import Command, Quit, SetDirection
from pacman.protocol.enums import Direction, FoodType, GhostState
from pacman.protocol.events import (
    Event,
    FoodCollected,
    FoodSpawned,
    GameOver,
    GameWon,
    GhostMoved,
    GhostStateChanged,
    LevelCompleted,
    LifeLost,
    MazeGenerated,
    PacmanCaught,
    PacmanMoved,
    ScoreChanged,
)

__all__ = [
    "Command",
    "Direction",
    "Event",
    "FoodCollected",
    "FoodSpawned",
    "FoodType",
    "GameOver",
    "GameWon",
    "GhostMoved",
    "GhostState",
    "GhostStateChanged",
    "LevelCompleted",
    "LifeLost",
    "MazeGenerated",
    "PacmanCaught",
    "PacmanMoved",
    "Quit",
    "ScoreChanged",
    "SetDirection",
]
