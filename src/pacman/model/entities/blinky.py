from pacman.model.entities.entity import Entity
from pacman.protocol import Direction


class Blinky(Entity):
    """Represents Blinky, a Pac-Man enemy."""

    def __init__(
        self,
        x: float,
        y: float,
        radius: float = 0.3,
        speed: float = 4.0,
    ) -> None:
        super().__init__(x=x, y=y, radius=radius, speed=speed)

        self.direction = Direction.LEFT

    def update(self, delta_time: float) -> None:
        """Update Blinky state."""
        self.move(delta_time)
