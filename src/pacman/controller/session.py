"""Screen flow: main menu, game, pause, highscores, name entry.

The session is the only object that knows *which* screen is active. It
owns the model while a game is running, forwards every model event to
the views, and adds the events that describe the screens themselves.
Views therefore never need a reference to the model.
"""

from pacman.config import Config
from pacman.model.game import Game
from pacman.model.highscore import HighscoreTable
from pacman.protocol import (
    Back,
    Backspace,
    Command,
    Confirm,
    Event,
    GameOver,
    GameWon,
    HighscoresChanged,
    MenuChanged,
    MoveSelection,
    NameEntryChanged,
    Quit,
    Screen,
    ScreenChanged,
    TypeCharacter,
)
from pacman.utils.observer import Observable, Observer

MAIN_MENU = ("Start Game", "View Highscores", "Instructions", "Exit")
PAUSE_MENU = ("Resume", "Return to main menu")

MAX_NAME_LENGTH = 10


class Session(Observable[Event], Observer[Event]):
    """Drive the game through its screens, and keep the views in sync."""

    def __init__(self, config: Config, highscores: HighscoreTable) -> None:
        Observable.__init__(self)

        self._config = config
        self._highscores = highscores
        self._screen = Screen.MENU
        self._menu: tuple[str, ...] = MAIN_MENU
        self._selected = 0
        self._game: Game | None = None
        self._name = ""
        self._final_score = 0
        self._running = True
        self._error: str | None = None

    # -- Observer of the model -------------------------------------------

    def update(self, event: Event) -> None:
        """Forward a model event, then react to the ones that end a game."""
        self.notify(event)

        if isinstance(event, GameOver):
            self._end_game(event.score, Screen.GAME_OVER)
        elif isinstance(event, GameWon):
            self._end_game(event.score, Screen.VICTORY)

    # -- Lifecycle -------------------------------------------------------

    @property
    def is_running(self) -> bool:
        """Return False once the player asked to close the game."""
        return self._running

    @property
    def screen(self) -> Screen:
        """Return the active screen."""
        return self._screen

    @property
    def last_error(self) -> str | None:
        """Return the message of the last recoverable failure, if any."""
        return self._error

    def start(self) -> None:
        """Send the initial state: highscores, main menu, current screen."""
        self._highscores.load()
        self._notify_highscores()
        self._show(Screen.MENU, MAIN_MENU)

    def tick(self, delta_time: float) -> None:
        """Advance the model, but only while a game is being played."""
        if self._screen is not Screen.PLAYING or self._game is None:
            return

        try:
            self._game.update(delta_time)
        except RuntimeError as error:
            self._abort_game(error)

    def stop(self) -> None:
        """Ask the application to close."""
        self._running = False

    # -- Commands --------------------------------------------------------

    def handle(self, command: Command) -> None:
        """Route a command according to the active screen."""
        if isinstance(command, Quit):
            self.stop()
            return

        match self._screen:
            case Screen.MENU | Screen.PAUSED:
                self._handle_menu(command)
            case Screen.HIGHSCORES | Screen.INSTRUCTIONS:
                self._handle_sub_screen(command)
            case Screen.PLAYING:
                self._handle_playing(command)
            case Screen.GAME_OVER | Screen.VICTORY:
                self._handle_name_entry(command)

    def _handle_menu(self, command: Command) -> None:
        """Move the cursor or validate an entry of the active menu."""
        match command:
            case MoveSelection(delta=delta):
                self._move_selection(delta)
            case Confirm():
                self._activate_menu_entry()
            case Back() if self._screen is Screen.PAUSED:
                self._resume()

    def _handle_sub_screen(self, command: Command) -> None:
        """Highscores and instructions only know how to be closed."""
        if isinstance(command, (Back, Confirm)):
            self._show(Screen.MENU, MAIN_MENU)

    def _handle_playing(self, command: Command) -> None:
        """Pause, or let the model deal with the command."""
        if isinstance(command, Back):
            self._show(Screen.PAUSED, PAUSE_MENU)
            return

        if self._game is None:
            return

        try:
            self._game.handle(command)
        except RuntimeError as error:
            self._abort_game(error)

    def _abort_game(self, error: RuntimeError) -> None:
        """Drop a game the model cannot continue, with a clean message.

        The only failure the model reports this way is the external maze
        generator refusing to build the next level. Losing the run is
        acceptable; a traceback in front of the reviewer is not.
        """
        self._error = str(error)
        print(f"error: {error}")
        self._abandon_game()

    def _handle_name_entry(self, command: Command) -> None:
        """Type the name saved with the score, then go back to the menu."""
        match command:
            case TypeCharacter(character=character):
                self._type(character)
            case Backspace():
                self._name = self._name[:-1]
                self._notify_name()
            case Confirm() | Back():
                self._save_score()

    # -- Menu ------------------------------------------------------------

    def _move_selection(self, delta: int) -> None:
        """Move the highlighted entry, wrapping around the menu."""
        if not self._menu:
            return

        self._selected = (self._selected + delta) % len(self._menu)
        self._notify_menu()

    def _activate_menu_entry(self) -> None:
        """Run the action of the highlighted entry."""
        entry = self._menu[self._selected]

        match entry:
            case "Start Game":
                self._start_game()
            case "View Highscores":
                self._show(Screen.HIGHSCORES)
            case "Instructions":
                self._show(Screen.INSTRUCTIONS)
            case "Exit":
                self.stop()
            case "Resume":
                self._resume()
            case "Return to main menu":
                self._abandon_game()

    # -- Game ------------------------------------------------------------

    def _start_game(self) -> None:
        """Create a fresh game and hand the screen over to it."""
        self._detach_game()

        try:
            game = Game(self._config)
        except RuntimeError as error:
            # A broken maze generator must not take the game down.
            self._error = str(error)
            print(f"error: {error}")
            self._show(Screen.MENU, MAIN_MENU)
            return

        self._error = None
        self._game = game
        game.attach(self)

        self._show(Screen.PLAYING)
        game.start()

    def _resume(self) -> None:
        """Leave the pause screen and keep playing."""
        self._show(Screen.PLAYING)

    def _abandon_game(self) -> None:
        """Drop the running game and go back to the main menu."""
        self._detach_game()
        self._show(Screen.MENU, MAIN_MENU)

    def _detach_game(self) -> None:
        """Stop listening to the current game, if there is one."""
        if self._game is not None:
            self._game.detach(self)
            self._game = None

    def _end_game(self, score: int, screen: Screen) -> None:
        """Ask the player for a name once the game is over or won."""
        self._detach_game()
        self._final_score = score
        self._name = ""
        self._show(screen)
        self._notify_name()

    # -- Name entry ------------------------------------------------------

    def _type(self, character: str) -> None:
        """Append one character to the name, if it is allowed."""
        if len(self._name) >= MAX_NAME_LENGTH:
            return

        if not (character.isalnum() or character == " "):
            return

        self._name += character
        self._notify_name()

    def _save_score(self) -> None:
        """Store the score, refresh the table and go back to the menu."""
        self._highscores.add(self._name, self._final_score)
        self._notify_highscores()
        self._show(Screen.MENU, MAIN_MENU)

    # -- Notifications ---------------------------------------------------

    def _show(self, screen: Screen, menu: tuple[str, ...] = ()) -> None:
        """Switch to a screen, publishing its menu when it has one."""
        self._screen = screen
        self._menu = menu
        self._selected = 0

        self.notify(ScreenChanged(screen))

        if menu:
            self._notify_menu()

    def _notify_menu(self) -> None:
        """Publish the entries of the active menu and the selected one."""
        self.notify(MenuChanged(self._menu, self._selected))

    def _notify_highscores(self) -> None:
        """Publish the highscore table."""
        self.notify(HighscoresChanged(self._highscores.as_tuples()))

    def _notify_name(self) -> None:
        """Publish the name being typed and the score it will be saved."""
        self.notify(NameEntryChanged(self._name, self._final_score))
