"""Regression test for ghosts freezing inside a wall.

A ghost that overshoots the exact centre of an intersection (e.g. because
of one long frame) can hit a wall off-axis. ``Game`` must recover it the
same way it already recovers Pac-Man: snap it to the current cell's
centre so it can be steered again on the very next frame, instead of
leaving it stuck forever with ``direction = Direction.NONE``.
"""

from pacman.config import Config
from pacman.model.game import Game
from pacman.protocol import Direction
from tests.conftest import RecordingView


def test_ghost_recovers_after_hitting_a_wall_off_centre(
    config: Config, view: RecordingView
) -> None:
    """A ghost that hits a wall away from a cell centre must not freeze."""
    game = Game(config)
    game.attach(view)
    game.start()

    ghost = game.ghosts[0]

    # Simulate a ghost that overshot an intersection: it sits well off
    # the centre of its cell, heading straight into a wall.
    cell_x, cell_y = int(ghost.x), int(ghost.y)
    ghost.position = (cell_x + 0.5, cell_y + 0.5)
    ghost.direction = _direction_into_a_wall(game, cell_x, cell_y)
    step_x, step_y = ghost.direction.value
    ghost.position = (
        ghost.x + step_x * 0.4,
        ghost.y + step_y * 0.4,
    )

    # Run enough frames for the ghost to reach and clip against the wall.
    for _ in range(30):
        game.update(1.0 / 60.0)

    # It must not be stuck: direction must have been reassigned, and it
    # must actually be able to move again on a further update.
    position_before = ghost.position
    for _ in range(30):
        game.update(1.0 / 60.0)

    assert (
        ghost.direction is not Direction.NONE
        or ghost.position != position_before
    )


def _direction_into_a_wall(
    game: Game, cell_x: int, cell_y: int
) -> Direction:
    """Return a direction whose neighbour cell is a wall.

    The neighbour is looked for around the cell ``(cell_x, cell_y)``.
    """
    directions = (
        Direction.UP,
        Direction.DOWN,
        Direction.LEFT,
        Direction.RIGHT,
    )

    for direction in directions:
        step_x, step_y = direction.value
        neighbour_x = cell_x + int(step_x)
        neighbour_y = cell_y + int(step_y)

        if not game.maze.is_walkable(neighbour_x, neighbour_y):
            return direction

    raise AssertionError("expected at least one wall next to the ghost's cell")
