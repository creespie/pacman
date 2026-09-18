from pacman.model.entities.entity import Entity
from pacman.protocol import Direction, GhostState


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

        # The corner this ghost spawns from and returns to once eaten.
        self._home = (x, y)
        self._state = GhostState.CHASE
        self._state_timer = 0.0

    @property
    def home(self) -> tuple[float, float]:
        """Return the ghost's home (spawn) position."""
        return self._home

    @property
    def state(self) -> GhostState:
        """Return the ghost's current behavioural state."""
        return self._state

    @state.setter
    def state(self, state: GhostState) -> None:
        self._state = state

    @property
    def state_timer(self) -> float:
        """Return the remaining time (seconds) for the current state."""
        return self._state_timer

    @state_timer.setter
    def state_timer(self, seconds: float) -> None:
        self._state_timer = max(0.0, seconds)

    def respawn(self) -> None:
        """Send the ghost back to its home corner, in chase mode."""
        self.position = self._home
        self.direction = Direction.LEFT
        self._state = GhostState.CHASE
        self._state_timer = 0.0

    def update(self, delta_time: float) -> None:
        """Update Blinky state."""
        self.move(delta_time)
