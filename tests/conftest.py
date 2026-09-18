"""Shared fixtures: a small, fast game configuration and a fake view."""

from dataclasses import replace
from typing import TypeVar

import pytest

from pacman.config import Config
from pacman.protocol import Event
from pacman.view.base import View

EventT = TypeVar("EventT", bound=Event)


class RecordingView(View):
    """A view that keeps every event instead of drawing it."""

    def __init__(self) -> None:
        self.events: list[Event] = []
        self.frames = 0

    def update(self, event: Event) -> None:
        """Record the event, then dispatch it as any view would."""
        self.events.append(event)
        super().update(event)

    def of_type(self, kind: type[EventT]) -> list[EventT]:
        """Return every recorded event of a given type."""
        return [event for event in self.events if isinstance(event, kind)]

    def render(self) -> None:
        """Count the frames instead of drawing them."""
        self.frames += 1


@pytest.fixture
def config() -> Config:
    """A configuration small enough to keep the tests fast."""
    return replace(
        Config(),
        levels=2,
        width=11,
        height=11,
        lives=2,
        pacgum=9999,
        level_max_time=10,
    )


@pytest.fixture
def view() -> RecordingView:
    """A recording view, ready to be attached to a session or a game."""
    return RecordingView()
