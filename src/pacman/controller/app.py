"""Wire the session, the views and the inputs, and drive the frames.

The application never blocks by itself: ``tick`` advances the game by
the time really elapsed since the previous frame. It can therefore be
called by the MLX loop hook (the real game), or by the plain loop of
``run`` (tests and headless runs) without changing anything else.
"""

import sys
import time
from collections.abc import Callable, Iterable

from pacman.config import Config
from pacman.controller.input_handler import InputHandler
from pacman.controller.session import Session
from pacman.model.highscore import HighscoreTable
from pacman.utils.observer import Observer
from pacman.view.base import View


class App:
    """Own the session, poll the inputs, render the views."""

    TARGET_FPS = 60
    FRAME_TIME = 1.0 / TARGET_FPS

    # A frame longer than this (a window being dragged, a slow machine)
    # is capped: better a small slow-down than entities jumping through
    # walls.
    MAX_DELTA = 0.1

    def __init__(
        self,
        config: Config,
        highscores: HighscoreTable,
        views: Iterable[View] = (),
        input_handlers: Iterable[InputHandler] = (),
        on_stop: Callable[[], None] | None = None,
    ) -> None:
        self._session = Session(config, highscores)
        self._views = list(views)
        self._input_handlers = list(input_handlers)
        self._on_stop = on_stop
        self._running = False
        self._last_time = time.perf_counter()

        for view in self._views:
            self._session.attach(view)

        # Input handlers that follow the screen flow (the keyboard needs
        # to know whether an arrow key means "go left" or "menu up").
        for handler in self._input_handlers:
            if isinstance(handler, Observer):
                self._session.attach(handler)

    @property
    def session(self) -> Session:
        """Return the session, mostly for tests."""
        return self._session

    @property
    def is_running(self) -> bool:
        """Return True while the application should keep ticking."""
        return self._running

    def start(self) -> None:
        """Publish the initial state and arm the frame clock."""
        self._running = True
        self._last_time = time.perf_counter()
        self._session.start()

    def tick(self) -> None:
        """Run exactly one frame, and never raise.

        ``tick`` is plugged into the MLX loop hook, which is a ctypes
        callback: an exception escaping it is not propagated to the
        caller, it is printed as a full traceback by ctypes and the loop
        carries on in a broken state. The subject forbids showing a
        traceback, so whatever goes wrong is turned into one clean line
        and stops the application instead.
        """
        try:
            self._tick()
        except Exception as error:
            print(f"error: unexpected failure: {error}", file=sys.stderr)
            self.stop()

    def _tick(self) -> None:
        """Run exactly one frame: input, model, then rendering."""
        if not self._running:
            return

        now = time.perf_counter()
        delta_time = min(now - self._last_time, self.MAX_DELTA)
        self._last_time = now

        self._process_input()
        self._session.tick(delta_time)

        for view in self._views:
            view.render()

        if not self._session.is_running:
            self.stop()

    def run(self) -> None:
        """Drive the frames from a plain loop (no graphics library)."""
        if not self._running:
            self.start()

        while self._running:
            frame_start = time.perf_counter()
            self.tick()
            elapsed = time.perf_counter() - frame_start
            remaining = self.FRAME_TIME - elapsed

            if remaining > 0:
                time.sleep(remaining)

    def stop(self) -> None:
        """Stop ticking and let the graphics loop, if any, return."""
        if not self._running:
            return

        self._running = False

        if self._on_stop is not None:
            self._on_stop()

    def _process_input(self) -> None:
        """Collect the commands of every input handler and route them."""
        for handler in self._input_handlers:
            for command in handler.poll():
                self._session.handle(command)
