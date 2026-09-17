"""Enumerations shared by the model, the views and the controllers."""

from enum import Enum


class Direction(Enum):
    """Possible movement directions."""

    UP = (0.0, -1.0)
    DOWN = (0.0, 1.0)
    LEFT = (-1.0, 0.0)
    RIGHT = (1.0, 0.0)
    NONE = (0.0, 0.0)


class FoodType(Enum):
    """Types of food available in the game."""

    PACGUM = 1
    SUPER_PACGUM = 2
