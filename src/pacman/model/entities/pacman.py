"""The player character."""

from pacman.model.entities.entity import Entity
from pacman.protocol import Direction


class Pacman(Entity):
    """Represents the Pac-Man player.

    ``direction`` is the way Pac-Man is actually moving, while
    ``next_direction`` is the way the player *asked* to go. The model
    applies the second one as soon as the corridor allows it, which is
    what makes the controls forgiving: a turn can be requested slightly
    before the intersection.
    """

    def __init__(
        self,
        x: float,
        y: float,
        radius: float = 0.3,
        speed: float = 5.0,
        lives: int = 3,
    ) -> None:
        super().__init__(x=x, y=y, radius=radius, speed=speed)

        self._lives = lives
        self._score = 0
        self._base_speed = speed
        self._next_direction = Direction.NONE

    @property
    def base_speed(self) -> float:
        """Return the speed Pac-Man has when no cheat is active."""
        return self._base_speed

    @property
    def next_direction(self) -> Direction:
        """Return the direction requested by the player."""
        return self._next_direction

    @next_direction.setter
    def next_direction(self, direction: Direction) -> None:
        self._next_direction = direction

    @property
    def lives(self) -> int:
        """Return the number of remaining lives."""
        return self._lives

    @property
    def score(self) -> int:
        """Return the current score."""
        return self._score

    def add_score(self, points: int) -> None:
        """Add points to the score. The score never decreases."""
        if points < 0:
            return

        self._score += points

    def add_life(self) -> None:
        """Grant one extra life (used by the cheat mode)."""
        self._lives += 1

    def lose_life(self) -> None:
        """Remove one life."""
        if self._lives > 0:
            self._lives -= 1

    def reset_position(self, x: float, y: float) -> None:
        """Reset Pac-Man position and stop him."""
        self.position = (x, y)
        self.direction = Direction.NONE
        self._next_direction = Direction.NONE

    def update(self, delta_time: float) -> None:
        """Update Pac-Man state."""
        self.move(delta_time)
