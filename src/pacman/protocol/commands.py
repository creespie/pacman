"""Commands sent by the controllers and handled by the model."""

from dataclasses import dataclass

from pacman.protocol.enums import Direction


@dataclass(frozen=True)
class Command:
    """Base class for every command."""


@dataclass(frozen=True)
class SetDirection(Command):
    """Change the direction Pac-Man is moving in."""

    direction: Direction


@dataclass(frozen=True)
class Quit(Command):
    """Stop the game."""
