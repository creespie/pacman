"""Base class of every view.

A view is an observer that keeps a local copy of what it needs to draw.
``update`` only stores state, ``render`` only reads it: the model can
send a hundred events between two frames without costing a single extra
redraw.

Every handler below does nothing by default, so a concrete view only
overrides the events it actually cares about.
"""

from abc import abstractmethod

from pacman.protocol import (
    CheatsChanged,
    Event,
    FoodCollected,
    FoodSpawned,
    GameOver,
    GameWon,
    GhostMoved,
    GhostStateChanged,
    HighscoresChanged,
    LevelCompleted,
    LevelStarted,
    LivesChanged,
    MazeGenerated,
    MenuChanged,
    NameEntryChanged,
    PacmanCaught,
    PacmanMoved,
    ScoreChanged,
    ScreenChanged,
    TimeChanged,
)
from pacman.utils.observer import Observer


class View(Observer[Event]):
    """Receive the events and draw the current state on ``render``."""

    def update(self, event: Event) -> None:
        """Dispatch an incoming event to the matching handler."""
        if isinstance(event, MazeGenerated):
            self.on_maze_generated(event)
        elif isinstance(event, FoodSpawned):
            self.on_food_spawned(event)
        elif isinstance(event, FoodCollected):
            self.on_food_collected(event)
        elif isinstance(event, PacmanMoved):
            self.on_pacman_moved(event)
        elif isinstance(event, GhostMoved):
            self.on_ghost_moved(event)
        elif isinstance(event, GhostStateChanged):
            self.on_ghost_state_changed(event)
        elif isinstance(event, PacmanCaught):
            self.on_pacman_caught(event)
        elif isinstance(event, ScoreChanged):
            self.on_score_changed(event)
        elif isinstance(event, LivesChanged):
            self.on_lives_changed(event)
        elif isinstance(event, LevelStarted):
            self.on_level_started(event)
        elif isinstance(event, TimeChanged):
            self.on_time_changed(event)
        elif isinstance(event, CheatsChanged):
            self.on_cheats_changed(event)
        elif isinstance(event, LevelCompleted):
            self.on_level_completed(event)
        elif isinstance(event, GameOver):
            self.on_game_over(event)
        elif isinstance(event, GameWon):
            self.on_game_won(event)
        elif isinstance(event, ScreenChanged):
            self.on_screen_changed(event)
        elif isinstance(event, MenuChanged):
            self.on_menu_changed(event)
        elif isinstance(event, HighscoresChanged):
            self.on_highscores_changed(event)
        elif isinstance(event, NameEntryChanged):
            self.on_name_entry_changed(event)

    # -- Level content ---------------------------------------------------

    def on_maze_generated(self, event: MazeGenerated) -> None:
        """Handle a newly generated maze."""

    def on_food_spawned(self, event: FoodSpawned) -> None:
        """Handle a food item being placed."""

    def on_food_collected(self, event: FoodCollected) -> None:
        """Handle a food item being eaten."""

    # -- Entities --------------------------------------------------------

    def on_pacman_moved(self, event: PacmanMoved) -> None:
        """Handle Pac-Man moving."""

    def on_ghost_moved(self, event: GhostMoved) -> None:
        """Handle a ghost moving."""

    def on_ghost_state_changed(self, event: GhostStateChanged) -> None:
        """Handle a ghost becoming edible, eaten or dangerous again."""

    def on_pacman_caught(self, event: PacmanCaught) -> None:
        """Handle Pac-Man being touched by a ghost."""

    # -- HUD -------------------------------------------------------------

    def on_score_changed(self, event: ScoreChanged) -> None:
        """Handle the score changing."""

    def on_lives_changed(self, event: LivesChanged) -> None:
        """Handle the number of lives changing."""

    def on_level_started(self, event: LevelStarted) -> None:
        """Handle a level starting."""

    def on_time_changed(self, event: TimeChanged) -> None:
        """Handle the remaining time changing."""

    def on_cheats_changed(self, event: CheatsChanged) -> None:
        """Handle cheat mode being toggled or a cheat being applied."""

    # -- End of level / end of game --------------------------------------

    def on_level_completed(self, event: LevelCompleted) -> None:
        """Handle a level being cleared."""

    def on_game_over(self, event: GameOver) -> None:
        """Handle the player losing their last life."""

    def on_game_won(self, event: GameWon) -> None:
        """Handle the player completing every level."""

    # -- Screens ---------------------------------------------------------

    def on_screen_changed(self, event: ScreenChanged) -> None:
        """Handle the player moving to another screen."""

    def on_menu_changed(self, event: MenuChanged) -> None:
        """Handle the entries or the cursor of a menu changing."""

    def on_highscores_changed(self, event: HighscoresChanged) -> None:
        """Handle the highscore table being loaded or updated."""

    def on_name_entry_changed(self, event: NameEntryChanged) -> None:
        """Handle the name being typed after a game."""

    @abstractmethod
    def render(self) -> None:
        """Draw the current state."""
