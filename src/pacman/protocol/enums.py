"""Enumerations shared by the model, the views and the controllers."""

from enum import Enum


class Direction(Enum):
    """Possible movement directions, as a (dx, dy) unit vector."""

    UP = (0.0, -1.0)
    DOWN = (0.0, 1.0)
    LEFT = (-1.0, 0.0)
    RIGHT = (1.0, 0.0)
    NONE = (0.0, 0.0)


class FoodType(Enum):
    """Types of food available in the game."""

    PACGUM = 1
    SUPER_PACGUM = 2


class GhostState(Enum):
    """Behavioural state of a ghost."""

    CHASE = "chase"
    FRIGHTENED = "frightened"
    EATEN = "eaten"


class Screen(Enum):
    """The screen the player is currently looking at.

    The session owns this value; the views only ever learn about it
    through a ``ScreenChanged`` event.
    """

    MENU = "menu"
    HIGHSCORES = "highscores"
    INSTRUCTIONS = "instructions"
    PLAYING = "playing"
    PAUSED = "paused"
    GAME_OVER = "game_over"
    VICTORY = "victory"


class Cheat(Enum):
    """Cheats available once cheat mode is enabled, for peer review."""

    INVINCIBILITY = "invincibility"
    FREEZE_GHOSTS = "freeze_ghosts"
    SPEED = "speed"
    EXTRA_LIFE = "extra_life"
    SKIP_LEVEL = "skip_level"
