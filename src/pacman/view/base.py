"""Base class of every view."""

from abc import abstractmethod

from pacman.protocol import (
    Event,
    FoodCollected,
    FoodSpawned,
    GhostMoved,
    MazeGenerated,
    PacmanCaught,
    PacmanMoved,
    ScoreChanged,
)
from pacman.utils.observer import Observer


class View(Observer[Event]):
    """Receive the model events and draw the current state on render().

    The handlers below default to doing nothing, so a view only
    overrides the events it actually cares about.
    """

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
        elif isinstance(event, ScoreChanged):
            self.on_score_changed(event)
        elif isinstance(event, PacmanCaught):
            self.on_pacman_caught(event)

    def on_maze_generated(self, event: MazeGenerated) -> None:
        """Handle a newly generated maze."""

    def on_food_spawned(self, event: FoodSpawned) -> None:
        """Handle a food item being placed."""

    def on_food_collected(self, event: FoodCollected) -> None:
        """Handle a food item being eaten."""

    def on_pacman_moved(self, event: PacmanMoved) -> None:
        """Handle Pac-Man moving."""

    def on_ghost_moved(self, event: GhostMoved) -> None:
        """Handle a ghost moving."""

    def on_score_changed(self, event: ScoreChanged) -> None:
        """Handle the score changing."""

    def on_pacman_caught(self, event: PacmanCaught) -> None:
        """Handle Pac-Man being touched by a ghost."""

    @abstractmethod
    def render(self) -> None:
        """Draw the current state."""