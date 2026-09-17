"""Base class of every view."""

from abc import abstractmethod

from pacman.protocol import Event
from pacman.utils.observer import Observer


class View(Observer[Event]):
    """Receive the model events and draw the current state on render()."""

    def update(self , event : Event):
        if isinstance(event, Event.MazeGenerated):
            

    @abstractmethod
    def render(self) -> None:
        """Draw the current state."""
