"""Entry point: parse the command line, build the game, run the loop."""

import os
import sys
from pathlib import Path

from pacman.config import Config, ConfigError, load_config
from pacman.controller.app import App
from pacman.controller.keyboard import KeyboardInput, QuitOnClose
from pacman.model.highscore import HighscoreTable
from pacman.view.base import View
from pacman.view.canvas import make_canvas
from pacman.view.console import ConsoleView
from pacman.view.mlx_view import HUD_HEIGHT, MlxView

USAGE = "usage: python3 pac-man.py <config.json>"

WINDOW_TITLE = "Ghosts! More ghosts! - Pac-Man"
CELL_PIXELS = 28
MIN_WIDTH, MAX_WIDTH = 640, 1600
MIN_HEIGHT, MAX_HEIGHT = 480, 1000


def main(argv: list[str] | None = None) -> int:
    """Run the game and return the process exit code."""
    arguments = sys.argv[1:] if argv is None else argv

    error = _check_arguments(arguments)

    if error is not None:
        print(f"error: {error}\n{USAGE}", file=sys.stderr)
        return 1

    try:
        config = load_config(arguments[0])
    except ConfigError as config_error:
        print(f"error: {config_error}", file=sys.stderr)
        return 1

    return _run(config)


def _check_arguments(arguments: list[str]) -> str | None:
    """Return why the command line is wrong, or None if it is fine."""
    if len(arguments) != 1:
        return f"expected exactly one argument, got {len(arguments)}"

    if Path(arguments[0]).suffix.lower() != ".json":
        return f"'{arguments[0]}' is not a .json file"

    return None


def _run(config: Config) -> int:
    """Wire canvas, views, inputs and session, then run the game loop."""
    window_width, window_height = _window_size(config)
    canvas = make_canvas(window_width, window_height, WINDOW_TITLE)

    if canvas is None:
        print(
            "error: MiniLibX could not start. The game needs a Linux "
            "machine with a running X11 display (MiniLibX ships as a "
            "Linux x86-64 library; it does not run on macOS).",
            file=sys.stderr,
        )
        return 1

    mlx_view = MlxView(canvas)
    views: list[View] = [mlx_view]

    # Optional event log, handy during development and peer review.
    if os.environ.get("PACMAN_DEBUG"):
        views.append(ConsoleView())

    keyboard = KeyboardInput()
    window_closed = QuitOnClose()

    app = App(
        config,
        HighscoreTable(config.highscore_filename),
        views=views,
        input_handlers=[keyboard, window_closed],
        on_stop=canvas.stop,
    )

    canvas.on_key(keyboard.press)
    canvas.on_close(window_closed.ask_quit)
    canvas.on_expose(mlx_view.invalidate)
    canvas.on_tick(app.tick)

    try:
        app.start()
        canvas.run()
    except KeyboardInterrupt:
        print("interrupted")
    except Exception as error:  # never show a traceback to the player
        print(f"error: unexpected failure: {error}", file=sys.stderr)
        return 1

    return 0


def _window_size(config: Config) -> tuple[int, int]:
    """Pick a window big enough for the configured maze."""
    width = min(MAX_WIDTH, max(MIN_WIDTH, config.width * CELL_PIXELS))
    height = min(
        MAX_HEIGHT,
        max(MIN_HEIGHT, config.height * CELL_PIXELS + HUD_HEIGHT),
    )

    return width, height


if __name__ == "__main__":
    sys.exit(main())
