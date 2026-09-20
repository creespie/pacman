"""The model must describe its whole state through events."""

from pacman.config import Config
from pacman.model.game import Game
from pacman.protocol import (
    Cheat,
    Direction,
    FoodCollected,
    FoodSpawned,
    GameOver,
    GameWon,
    GhostStateChanged,
    LevelStarted,
    LivesChanged,
    MazeGenerated,
    PacmanMoved,
    ScoreChanged,
    SetDirection,
    TimeChanged,
    ToggleCheatMode,
    UseCheat,
)
from tests.conftest import RecordingView

FRAME = 1.0 / 60.0


def play(game: Game, seconds: float) -> None:
    """Advance the game frame by frame, as the application does."""
    for _ in range(int(seconds / FRAME)):
        game.update(FRAME)


def test_start_describes_the_whole_level(
    config: Config, view: RecordingView
) -> None:
    """A view that only listens can draw the level from start()."""
    game = Game(config)
    game.attach(view)
    game.start()

    assert view.of_type(MazeGenerated)
    assert view.of_type(FoodSpawned)
    assert view.of_type(PacmanMoved)
    assert view.of_type(LevelStarted)
    assert view.of_type(LivesChanged)
    assert view.of_type(TimeChanged)


def test_positions_are_cell_centres(
    config: Config, view: RecordingView
) -> None:
    """Every position sits in the middle of a walkable cell."""
    game = Game(config)
    game.attach(view)
    game.start()

    for event in view.of_type(FoodSpawned):
        assert event.x % 1 == 0.5 and event.y % 1 == 0.5
        assert game.maze.is_walkable(int(event.x), int(event.y))


def test_pacman_moves_and_eats(config: Config, view: RecordingView) -> None:
    """Moving through a corridor collects food and raises the score."""
    game = Game(config)
    game.attach(view)
    game.start()

    for direction in Direction:
        game.handle(SetDirection(direction))
        play(game, 1.0)

        if view.of_type(FoodCollected):
            break

    assert view.of_type(FoodCollected)
    assert game.score > 0
    assert view.of_type(ScoreChanged)


def test_pacman_never_walks_through_a_wall(config: Config) -> None:
    """Whatever the player presses, Pac-Man stays on a corridor."""
    game = Game(config)
    game.start()

    for direction in (Direction.UP, Direction.LEFT, Direction.DOWN):
        game.handle(SetDirection(direction))
        play(game, 2.0)

        assert not game.maze.is_colliding(
            game.pacman.x, game.pacman.y, game.pacman.radius
        )


def test_running_out_of_time_costs_a_life(
    config: Config, view: RecordingView
) -> None:
    """The level timer eventually takes a life and restarts the level."""
    game = Game(config)
    game.attach(view)
    game.start()

    # Only the timer may end this level: the ghosts are neutralised.
    game.handle(ToggleCheatMode())
    game.handle(UseCheat(Cheat.FREEZE_GHOSTS))
    game.handle(UseCheat(Cheat.INVINCIBILITY))

    play(game, config.level_max_time + 0.5)

    assert game.pacman.lives == config.lives - 1
    assert view.of_type(LivesChanged)


def test_losing_every_life_ends_the_game(
    config: Config, view: RecordingView
) -> None:
    """Game over is announced once, and the model then stands still."""
    game = Game(config)
    game.attach(view)
    game.start()

    play(game, config.level_max_time * config.lives + 1.0)

    assert game.is_over
    assert len(view.of_type(GameOver)) == 1


def test_super_pacgum_frightens_the_ghosts(
    config: Config, view: RecordingView
) -> None:
    """Eating a super-pacgum switches every ghost to frightened."""
    game = Game(config)
    game.attach(view)
    game.start()

    game.handle(ToggleCheatMode())
    game.handle(UseCheat(Cheat.FREEZE_GHOSTS))

    corner = next(
        food for food in game.foods if food.kind.name == "SUPER_PACGUM"
    )
    game.pacman.position = (corner.x, corner.y)
    game.update(FRAME)

    states = [
        event.state.value for event in view.of_type(GhostStateChanged)
    ]

    assert "frightened" in states


def test_cheats_do_nothing_until_cheat_mode_is_on(config: Config) -> None:
    """A cheat key pressed by mistake must not change the game."""
    game = Game(config)
    game.start()

    game.handle(UseCheat(Cheat.EXTRA_LIFE))

    assert game.pacman.lives == config.lives

    game.handle(ToggleCheatMode())
    game.handle(UseCheat(Cheat.EXTRA_LIFE))

    assert game.pacman.lives == config.lives + 1


def test_skipping_every_level_wins_the_game(
    config: Config, view: RecordingView
) -> None:
    """The skip-level cheat walks through the whole progression."""
    game = Game(config)
    game.attach(view)
    game.start()
    game.handle(ToggleCheatMode())

    for _ in range(config.levels):
        game.handle(UseCheat(Cheat.SKIP_LEVEL))

    assert game.is_won
    assert len(view.of_type(GameWon)) == 1
    assert len(view.of_type(LevelStarted)) == config.levels


def _open_directions(game: Game) -> list[Direction]:
    """Directions Pac-Man could take from the cell he stands in."""
    cell_x, cell_y = int(game.pacman.x), int(game.pacman.y)

    return [
        direction
        for direction in (
            Direction.UP,
            Direction.DOWN,
            Direction.LEFT,
            Direction.RIGHT,
        )
        if game.maze.is_walkable(
            cell_x + int(direction.value[0]),
            cell_y + int(direction.value[1]),
        )
    ]


def test_a_turn_is_taken_before_reaching_the_centre(config: Config) -> None:
    """The turn window is what keeps the controls responsive.

    A centre goes by every 200 ms at Pac-Man's speed, so a window of one
    frame would throw most inputs away and the game would feel sluggish.
    """
    game = Game(config)
    game.start()

    wanted = next(
        direction
        for direction in _open_directions(game)
        if direction in (Direction.UP, Direction.DOWN)
    )

    # Stand short of the centre by most of the window, as a player
    # pressing the key slightly early would be.
    cell_x, cell_y = int(game.pacman.x), int(game.pacman.y)
    game.pacman.position = (
        cell_x + 0.5 - Game.TURN_WINDOW * 0.9,
        cell_y + 0.5,
    )

    game.handle(SetDirection(wanted))
    game.update(FRAME)

    assert game.pacman.direction is wanted

    # Whatever the window allowed, Pac-Man is back on the grid.
    assert game.pacman.x == cell_x + 0.5


def test_an_old_turn_request_is_dropped(config: Config) -> None:
    """A turn that never became possible must not fire much later.

    Keeping it would make Pac-Man turn on his own at some unrelated
    intersection, seconds after the key was pressed.
    """
    game = Game(config)
    game.start()

    game.handle(ToggleCheatMode())
    game.handle(UseCheat(Cheat.FREEZE_GHOSTS))
    game.handle(UseCheat(Cheat.INVINCIBILITY))

    open_directions = _open_directions(game)
    blocked = next(
        direction
        for direction in (
            Direction.UP,
            Direction.DOWN,
            Direction.LEFT,
            Direction.RIGHT,
        )
        if direction not in open_directions
    )

    game.handle(SetDirection(blocked))
    play(game, Game.TURN_REQUEST_TIMEOUT + 0.2)

    assert game.pacman.next_direction is Direction.NONE
    assert game.pacman.direction is not blocked
