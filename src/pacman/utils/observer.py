"""Generic implementation of the Observer pattern."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

EventT = TypeVar("EventT")


class Observer(ABC, Generic[EventT]):
    """Receive the events emitted by an Observable."""

    @abstractmethod
    def update(self, event: EventT) -> None:
        """Handle an event."""


class Observable(Generic[EventT]):
    """Emit events to the attached observers."""

    def __init__(self) -> None:
        self._observers: list[Observer[EventT]] = []

    def attach(self, observer: Observer[EventT]) -> None:
        """Start sending events to an observer."""
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: Observer[EventT]) -> None:
        """Stop sending events to an observer."""
        self._observers.remove(observer)

    def notify(self, event: EventT) -> None:
        """Send an event to every attached observer."""
        for observer in self._observers:
            observer.update(event)
