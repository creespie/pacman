"""Text view: prints the events instead of drawing them.

It exists for two reasons: it proves that the model is really decoupled
from any graphic library (the same events feed both views), and it keeps
the game usable — and testable — on a machine with no display.
"""

from pacman.protocol import (
    GameOver,
    GameWon,
    HighscoresChanged,
    LevelStarted,
    LivesChanged,
    MenuChanged,
    NameEntryChanged,
    PacmanCaught,
    ScoreChanged,
    ScreenChanged,
    TimeChanged,
)
from pacman.view.base import View


class ConsoleView(View):
    """Log the meaningful events on the standard output."""

    def __init__(self) -> None:
        self._score = 0
        self._lives = 0
        self._level = 1
        self._time_left = 0

    def on_screen_changed(self, event: ScreenChanged) -> None:
        """Announce the new screen."""
        print(f"[screen] {event.screen.value}")

    def on_menu_changed(self, event: MenuChanged) -> None:
        """Print the menu with a marker on the selected entry."""
        entries = " | ".join(
            f"[{item}]" if index == event.selected else item
            for index, item in enumerate(event.items)
        )
        print(f"[menu] {entries}")

    def on_highscores_changed(self, event: HighscoresChanged) -> None:
        """Print the highscore table."""
        if not event.entries:
            print("[highscores] empty")
            return

        for rank, (name, points) in enumerate(event.entries, start=1):
            print(f"[highscores] {rank:2d}. {name:<10} {points:>6}")

    def on_level_started(self, event: LevelStarted) -> None:
        """Announce a new level."""
        self._level = event.level
        self._time_left = event.time_limit
        print(f"[level] {event.level}/{event.total_levels}")

    def on_score_changed(self, event: ScoreChanged) -> None:
        """Print the new score."""
        self._score = event.score
        print(f"[score] {event.score}")

    def on_lives_changed(self, event: LivesChanged) -> None:
        """Print the remaining lives."""
        self._lives = event.lives
        print(f"[lives] {event.lives}")

    def on_time_changed(self, event: TimeChanged) -> None:
        """Print the remaining time every ten seconds."""
        self._time_left = event.seconds_left

        if event.seconds_left % 10 == 0:
            print(f"[time] {event.seconds_left}s left")

    def on_pacman_caught(self, event: PacmanCaught) -> None:
        """Report that a ghost caught Pac-Man."""
        print(f"[caught] by ghost {event.ghost_index}")

    def on_game_over(self, event: GameOver) -> None:
        """Report the end of the game."""
        print(f"[game over] score {event.score}")

    def on_game_won(self, event: GameWon) -> None:
        """Report a victory."""
        print(f"[victory] score {event.score}")

    def on_name_entry_changed(self, event: NameEntryChanged) -> None:
        """Show the name being typed."""
        print(f"[name] {event.name!r} for {event.score} points")

    def render(self) -> None:
        """Nothing to draw: the events were printed as they arrived."""
