"""Wire the model, the views and the input handlers, and run the game loop."""

import time
from collections.abc import Iterable

from pacman.config import Config
from pacman.controller.input_handler import InputHandler
from pacman.model.game import Game
from pacman.protocol import Command, Quit
from pacman.view.base import View


class App:
    """Create the game, connect views and input handlers, run the loop."""

    FPS = 60
    DELTA_TIME = 1.0 / FPS

    def __init__(
        self,
        config: Config,
        views: Iterable[View] = (),
        input_handlers: Iterable[InputHandler] = (),
    ) -> None:
        self._game = Game(config)
        self._views = list(views)
        self._input_handlers = list(input_handlers)
        self._running = False

        for view in self._views:
            self._game.attach(view)

    def run(self) -> None:
        """Start the main game loop."""
        self._running = True
        self._game.start()

        while self._running:
            start_time = time.perf_counter()

            self._process_input()
            self._game.update(self.DELTA_TIME)

            for view in self._views:
                view.render()

            # Keep the game close to the target FPS.
            elapsed_time = time.perf_counter() - start_time
            sleep_time = self.DELTA_TIME - elapsed_time

            if sleep_time > 0:
                time.sleep(sleep_time)

    def stop(self) -> None:
        """Stop the game loop."""
        self._running = False

    def _process_input(self) -> None:
        """Collect the commands from every input handler and dispatch them."""
        for handler in self._input_handlers:
            for command in handler.poll():
                self._dispatch(command)

    def _dispatch(self, command: Command) -> None:
        """Route a command to the app or to the model."""
        match command:
            case Quit():
                self.stop()
            case _:
                self._game.handle(command)
