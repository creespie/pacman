import sys

from pacman.config import ConfigError, load_config
from pacman.controller.app import App
from pacman.view.console import ConsoleView


def main() -> None:
    """Load the configuration and run the game."""
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.json"

    try:
        config = load_config(config_path)
    except ConfigError as error:
        sys.exit(f"error: {error}")

    try:
        App(config, views=[ConsoleView()]).run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
