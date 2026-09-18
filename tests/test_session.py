"""The session drives the screens described by the subject."""

from pathlib import Path

from pacman.config import Config
from pacman.controller.keyboard import ESCAPE, KeyboardInput
from pacman.controller.session import Session
from pacman.model.highscore import HighscoreTable
from pacman.protocol import (
    Back,
    Confirm,
    Direction,
    MazeGenerated,
    MoveSelection,
    Screen,
    ScreenChanged,
    SetDirection,
    TypeCharacter,
)
from tests.conftest import RecordingView


def screen_of(session: Session) -> Screen:
    """Read the active screen (through a call, so it is re-evaluated)."""
    return session.screen


def make_session(config: Config, tmp_path: Path) -> Session:
    """A session storing its highscores in a temporary file."""
    return Session(config, HighscoreTable(tmp_path / "highscores.json"))


def test_menu_to_game_and_back(
    config: Config, view: RecordingView, tmp_path: Path
) -> None:
    """Start Game builds a level; the pause menu goes back to the menu."""
    session = make_session(config, tmp_path)
    session.attach(view)
    session.start()

    assert screen_of(session) is Screen.MENU

    session.handle(Confirm())

    assert screen_of(session) is Screen.PLAYING
    assert view.of_type(MazeGenerated)

    session.handle(Back())

    assert screen_of(session) is Screen.PAUSED

    session.handle(MoveSelection(1))
    session.handle(Confirm())

    assert screen_of(session) is Screen.MENU


def test_paused_game_does_not_advance(
    config: Config, view: RecordingView, tmp_path: Path
) -> None:
    """Ticking while paused leaves the model untouched."""
    session = make_session(config, tmp_path)
    session.attach(view)
    session.start()
    session.handle(Confirm())
    session.handle(SetDirection(Direction.LEFT))
    session.handle(Back())

    before = len(view.events)

    for _ in range(60):
        session.tick(1 / 60)

    assert len(view.events) == before


def test_highscores_screen_is_reachable(
    config: Config, view: RecordingView, tmp_path: Path
) -> None:
    """The second entry of the main menu opens the highscores."""
    session = make_session(config, tmp_path)
    session.attach(view)
    session.start()

    session.handle(MoveSelection(1))
    session.handle(Confirm())

    assert screen_of(session) is Screen.HIGHSCORES

    session.handle(Back())

    assert screen_of(session) is Screen.MENU


def test_name_entry_saves_the_score(
    config: Config, view: RecordingView, tmp_path: Path
) -> None:
    """After a game the typed name is stored with the final score."""
    table = HighscoreTable(tmp_path / "highscores.json")
    session = Session(config, table)
    session.attach(view)
    session.start()
    session.handle(Confirm())

    frames = int(config.level_max_time * config.lives * 60) + 120

    for _ in range(frames):
        session.tick(1 / 60)

    assert screen_of(session) is Screen.GAME_OVER

    for character in "Foliole":
        session.handle(TypeCharacter(character))

    session.handle(Confirm())

    assert screen_of(session) is Screen.MENU
    assert table.as_tuples()[0][0] == "Foliole"


def test_exit_stops_the_session(config: Config, tmp_path: Path) -> None:
    """The last entry of the main menu closes the game."""
    session = make_session(config, tmp_path)
    session.start()

    session.handle(MoveSelection(-1))
    session.handle(Confirm())

    assert not session.is_running


def test_keyboard_follows_the_screen() -> None:
    """The same key is a direction in game and a menu action in a menu."""
    keyboard = KeyboardInput()
    keyboard.update(ScreenChanged(Screen.PLAYING))
    keyboard.press(65361)

    assert keyboard.poll() == [SetDirection(Direction.LEFT)]

    keyboard.update(ScreenChanged(Screen.MENU))
    keyboard.press(65364)
    keyboard.press(ESCAPE)

    assert keyboard.poll() == [MoveSelection(1), Back()]

    keyboard.update(ScreenChanged(Screen.GAME_OVER))
    keyboard.press(ord("a"))

    assert keyboard.poll() == [TypeCharacter("a")]
