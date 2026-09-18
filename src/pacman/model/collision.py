from math import hypot

from pacman.model.entities import Entity
from pacman.model.maze import Maze

# Number of binary-search steps used by clip_to_wall(). Each step halves
# the remaining uncertainty, so this many steps land well under a
# thousandth of a cell: far more precise than a single frame's movement.
_CLIP_ITERATIONS = 8


class CollisionDetector:
    """Detect collisions between game objects."""

    def __init__(self, maze: Maze) -> None:
        """Initialize the collision detector."""
        self._maze = maze

    def entities_collide(self, entity_a: Entity, entity_b: Entity) -> bool:
        """Return True if two entities are colliding."""
        distance = hypot(entity_a.x - entity_b.x, entity_a.y - entity_b.y)

        return distance < entity_a.radius + entity_b.radius

    def entity_hits_wall(self, entity: Entity) -> bool:
        """Return True if an entity hits a maze wall."""
        return self._maze.is_colliding(entity.x, entity.y, entity.radius)

    def clip_to_wall(
        self,
        radius: float,
        from_position: tuple[float, float],
        to_position: tuple[float, float],
    ) -> tuple[float, float]:
        """Push a blocked move back to the furthest free point it can
        reach, instead of rejecting it outright.

        ``from_position`` is assumed to be wall-free (true of any position
        that was valid on the previous frame). The point returned is the
        closest point to ``to_position``, along the straight line from
        ``from_position``, that does not collide with a wall.
        """
        if not self._maze.is_colliding(*to_position, radius):
            return to_position

        allowed = from_position
        blocked = to_position

        for _ in range(_CLIP_ITERATIONS):
            midpoint = (
                (allowed[0] + blocked[0]) / 2,
                (allowed[1] + blocked[1]) / 2,
            )

            if self._maze.is_colliding(*midpoint, radius):
                blocked = midpoint
            else:
                allowed = midpoint

        return allowed
