from pacman.model.entities.entity import Entity
from pacman.protocol import Direction


class Pacman(Entity):
    """Represents the Pac-Man player."""

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

    @property
    def lives(self) -> int:
        """Return the number of remaining lives."""
        return self._lives

    @property
    def score(self) -> int:
        """Return the current score."""
        return self._score

    def add_score(self, points: int) -> None:
        """Add points to the score."""
        if points < 0:
            return

        self._score += points

    def lose_life(self) -> None:
        """Remove one life."""
        if self._lives > 0:
            self._lives -= 1

    def reset_position(self, x: float, y: float) -> None:
        """Reset Pac-Man position."""
        self.position = (x, y)
        self.direction = Direction.NONE

    def update(self, delta_time: float) -> None:
        """Update Pac-Man state."""
        self.move(delta_time)
