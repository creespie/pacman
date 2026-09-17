from pacman.protocol import FoodType


class Food:
    """Represent a food item in the maze."""

    def __init__(
        self,
        x: float,
        y: float,
        kind: FoodType = FoodType.PACGUM,
    ) -> None:
        self._x = x
        self._y = y
        self._kind = kind
        self._collected = False

    @property
    def x(self) -> float:
        """Return the X position."""
        return self._x

    @property
    def y(self) -> float:
        """Return the Y position."""
        return self._y

    @property
    def kind(self) -> FoodType:
        """Return the food type."""
        return self._kind

    @property
    def collected(self) -> bool:
        """Return True if the food was collected."""
        return self._collected

    def collect(self) -> None:
        """Mark the food as collected."""
        self._collected = True
