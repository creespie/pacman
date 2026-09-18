"""Turn raw key presses into commands, according to the active screen.

The same key does different things depending on where the player is: an
arrow moves Pac-Man in game and the cursor in a menu, a letter is a
cheat in game and a character while typing a name. The handler follows
the screen through the ``ScreenChanged`` events, so nothing else in the
program has to know about keycodes.
"""

from pacman.controller.input_handler import InputHandler
from pacman.protocol import (
    Back,
    Backspace,
    Cheat,
    Command,
    Confirm,
    Direction,
    Event,
    MoveSelection,
    Quit,
    Screen,
    ScreenChanged,
    SetDirection,
    ToggleCheatMode,
    TypeCharacter,
    UseCheat,
)
from pacman.utils.observer import Observer

# X11 keysyms, as reported by MiniLibX.
ESCAPE = 65307
ENTER = 65293
KEYPAD_ENTER = 65421
BACKSPACE = 65288
SPACE = 32

ARROWS = {
    65361: Direction.LEFT,
    65362: Direction.UP,
    65363: Direction.RIGHT,
    65364: Direction.DOWN,
}

LETTERS = {
    ord("a"): Direction.LEFT,
    ord("w"): Direction.UP,
    ord("d"): Direction.RIGHT,
    ord("s"): Direction.DOWN,
}

DIRECTIONS = {**ARROWS, **LETTERS}

# Menu navigation: up/down only, mapped to a cursor delta.
MENU_STEPS = {
    65362: -1,
    65364: 1,
    ord("w"): -1,
    ord("s"): 1,
}

CHEAT_KEYS = {
    ord("1"): Cheat.INVINCIBILITY,
    ord("2"): Cheat.FREEZE_GHOSTS,
    ord("3"): Cheat.SPEED,
    ord("4"): Cheat.EXTRA_LIFE,
    ord("5"): Cheat.SKIP_LEVEL,
}

CHEAT_MODE_KEY = ord("c")


class KeyboardInput(InputHandler, Observer[Event]):
    """Queue key presses and translate them when the app polls."""

    def __init__(self) -> None:
        self._pending: list[int] = []
        self._screen = Screen.MENU

    def update(self, event: Event) -> None:
        """Follow the active screen through the session events."""
        if isinstance(event, ScreenChanged):
            self._screen = event.screen

    def press(self, keycode: int) -> None:
        """Record a key press; called from the graphics key hook."""
        self._pending.append(keycode)

    def poll(self) -> list[Command]:
        """Return the commands produced since the last call."""
        keycodes, self._pending = self._pending, []
        commands = []

        for keycode in keycodes:
            command = self._translate(keycode)

            if command is not None:
                commands.append(command)

        return commands

    def _translate(self, keycode: int) -> Command | None:
        """Map one keycode to a command for the current screen."""
        match self._screen:
            case Screen.PLAYING:
                return self._translate_playing(keycode)
            case Screen.MENU | Screen.PAUSED:
                return self._translate_menu(keycode)
            case Screen.GAME_OVER | Screen.VICTORY:
                return self._translate_name_entry(keycode)
            case _:
                return self._translate_sub_screen(keycode)

    @staticmethod
    def _translate_playing(keycode: int) -> Command | None:
        """In game: move, pause, or use the cheat keys."""
        if keycode in DIRECTIONS:
            return SetDirection(DIRECTIONS[keycode])

        if keycode == ESCAPE:
            return Back()

        if keycode == CHEAT_MODE_KEY:
            return ToggleCheatMode()

        if keycode in CHEAT_KEYS:
            return UseCheat(CHEAT_KEYS[keycode])

        return None

    @staticmethod
    def _translate_menu(keycode: int) -> Command | None:
        """In a menu: move the cursor, validate, or leave."""
        if keycode in MENU_STEPS:
            return MoveSelection(MENU_STEPS[keycode])

        if keycode in (ENTER, KEYPAD_ENTER, SPACE):
            return Confirm()

        if keycode == ESCAPE:
            return Back()

        return None

    @staticmethod
    def _translate_name_entry(keycode: int) -> Command | None:
        """While typing a name: characters, backspace, validation."""
        if keycode in (ENTER, KEYPAD_ENTER, ESCAPE):
            return Confirm()

        if keycode == BACKSPACE:
            return Backspace()

        if SPACE <= keycode <= 126:
            return TypeCharacter(chr(keycode))

        return None

    @staticmethod
    def _translate_sub_screen(keycode: int) -> Command | None:
        """On highscores and instructions: any of these keys closes it."""
        if keycode in (ENTER, KEYPAD_ENTER, SPACE, ESCAPE, BACKSPACE):
            return Back()

        return None


class QuitOnClose(InputHandler):
    """Emit a single ``Quit`` command, used when the window is closed."""

    def __init__(self) -> None:
        self._asked = False

    def ask_quit(self) -> None:
        """Record that the player closed the window."""
        self._asked = True

    def poll(self) -> list[Command]:
        """Return a Quit command once, then nothing."""
        if not self._asked:
            return []

        self._asked = False

        return [Quit()]
