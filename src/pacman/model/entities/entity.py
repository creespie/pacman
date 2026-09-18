from abc import ABC, abstractmethod

from pacman.protocol import Direction


class Entity(ABC):
    """Base class for all game entities."""

    def __init__(
        self,
        x: float,
        y: float,
        radius: float,
        speed: float,
    ) -> None:
        self._x = x
        self._y = y
        self._radius = radius
        self._speed = speed
        self._direction = Direction.NONE

    @property
    def x(self) -> float:
        """Return the X position."""
        return self._x

    @property
    def y(self) -> float:
        """Return the Y position."""
        return self._y

    @property
    def position(self) -> tuple[float, float]:
        """Return the (x, y) position."""
        return self._x, self._y

    @position.setter
    def position(self, position: tuple[float, float]) -> None:
        self._x, self._y = position

    @property
    def radius(self) -> float:
        """Return the entity radius."""
        return self._radius

    @property
    def speed(self) -> float:
        """Return the entity speed, in cells per second."""
        return self._speed

    @speed.setter
    def speed(self, speed: float) -> None:
        self._speed = max(0.0, speed)

    @property
    def direction(self) -> Direction:
        """Return the current direction."""
        return self._direction

    @direction.setter
    def direction(self, direction: Direction) -> None:
        self._direction = direction

    def move(self, delta_time: float) -> None:
        """Move the entity according to its direction."""
        direction_x, direction_y = self._direction.value

        self._x += direction_x * self._speed * delta_time
        self._y += direction_y * self._speed * delta_time

    @abstractmethod
    def update(self, delta_time: float) -> None:
        """Update the entity state."""
