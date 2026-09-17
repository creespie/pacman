from math import hypot

from pacman.model.entities import Entity
from pacman.model.maze import Maze


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
