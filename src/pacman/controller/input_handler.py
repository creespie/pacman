"""Base class of every input source."""

from abc import ABC, abstractmethod

from pacman.protocol import Command


class InputHandler(ABC):
    """Translate raw input (keyboard, mouse, network...) into commands."""

    @abstractmethod
    def poll(self) -> list[Command]:
        """Return the commands produced since the last call."""
