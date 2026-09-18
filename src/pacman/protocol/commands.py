"""Commands sent by the controllers and handled by session and model."""

from dataclasses import dataclass

from pacman.protocol.enums import Cheat, Direction


@dataclass(frozen=True)
class Command:
    """Base class for every command."""


@dataclass(frozen=True)
class SetDirection(Command):
    """Ask Pac-Man to move in a direction as soon as it is possible."""

    direction: Direction


@dataclass(frozen=True)
class MoveSelection(Command):
    """Move the menu cursor by ``delta`` entries."""

    delta: int


@dataclass(frozen=True)
class Confirm(Command):
    """Validate the current menu entry or the typed name."""


@dataclass(frozen=True)
class Back(Command):
    """Leave the current screen (pause the game, close a sub-screen)."""


@dataclass(frozen=True)
class TypeCharacter(Command):
    """Append a character to the name being typed."""

    character: str


@dataclass(frozen=True)
class Backspace(Command):
    """Remove the last character of the name being typed."""


@dataclass(frozen=True)
class ToggleCheatMode(Command):
    """Enable or disable cheat mode."""


@dataclass(frozen=True)
class UseCheat(Command):
    """Apply one cheat; ignored when cheat mode is disabled."""

    cheat: Cheat


@dataclass(frozen=True)
class Quit(Command):
    """Close the game."""
