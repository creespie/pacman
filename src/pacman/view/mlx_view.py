"""Concrete view that renders the whole game with MLX.

The view holds no reference to the model: everything it draws comes from
the events it received. Positions carried by those events are cell
centres, so a point ``(x, y)`` sits in the cell ``(int(x), int(y))`` and
its pixel is ``origin + x * cell_size``. No half cell is added here.
"""

from pacman.protocol import (
    CheatsChanged,
    Event,
    Direction,
    FoodCollected,
    FoodSpawned,
    FoodType,
    GhostMoved,
    GhostState,
    GhostStateChanged,
    HighscoresChanged,
    LevelStarted,
    LivesChanged,
    MazeGenerated,
    MenuChanged,
    NameEntryChanged,
    PacmanCaught,
    PacmanMoved,
    ScoreChanged,
    Screen,
    ScreenChanged,
    TimeChanged,
)
from pacman.view.base import View
from pacman.view.canvas import FONT_WIDTH, TEXT_HEIGHT, Canvas

HUD_HEIGHT = 40

WALL_COLOR = 0x2121DE
FLOOR_COLOR = 0x000000
PACGUM_COLOR = 0xFFB897
SUPER_PACGUM_COLOR = 0xFFB897
PACMAN_COLOR = 0xFFFF00
CAUGHT_COLOR = 0xFFFFFF
TEXT_COLOR = 0xFFFFFF
DIM_TEXT_COLOR = 0xA0A0A0
TITLE_COLOR = 0xFFFF00
SELECTED_COLOR = 0xFFB897
CHEAT_COLOR = 0x00FF00
EYE_COLOR = 0xFFFFFF
FRIGHTENED_COLOR = 0x2121DE
GHOST_COLORS = (0xFF0000, 0xFFB8FF, 0x00FFFF, 0xFFB852)

# Number of frames Pac-Man blinks white after being caught.
CAUGHT_FRAMES = 30

# Vertical step between two lines of text on the menu screens.
LINE_HEIGHT = 26

# Pause panel: where it starts, how thick its frame is, and how much
# room is left between the frame and the text inside it.
PANEL_TOP = 110
PANEL_BORDER = 3
PANEL_PADDING = 12
PANEL_BORDER_COLOR = WALL_COLOR

INSTRUCTIONS = (
    "Arrows or WASD    move Pac-Man",
    "ESC               pause / back",
    "ENTER or SPACE    validate",
    "",
    "Eat every pacgum to clear a level.",
    "A super-pacgum makes ghosts edible.",
    "Running out of time costs a life.",
    "",
    "Cheat mode, for peer review:",
    "C toggle     1 invincible   2 freeze",
    "3 speed      4 extra life   5 skip level",
)


class MlxView(View):
    """Turn the stream of events into pixels on a Canvas.

    The maze and the uneaten food live in the canvas background layer,
    so one frame costs a single memcpy plus the few moving entities.
    """

    def __init__(self, canvas: Canvas) -> None:
        self._canvas = canvas

        # A screen where nothing moves is only redrawn when something
        # actually changed: MLX draws text as one blit per character,
        # straight onto the window and on top of the frame that has just
        # erased it, so repainting an unchanged menu sixty times a
        # second makes the text flicker.
        self._dirty = True

        self._screen = Screen.MENU
        self._grid: list[list[int]] = []
        self._food: dict[tuple[float, float], FoodType] = {}
        self._pacman: tuple[float, float] = (0.0, 0.0)
        self._direction = Direction.RIGHT
        self._ghosts: dict[int, tuple[float, float]] = {}
        self._ghost_states: dict[int, GhostState] = {}

        self._score = 0
        self._lives = 0
        self._level = 1
        self._total_levels = 1
        self._time_left = 0
        self._caught_frames = 0

        self._cheats_enabled = False
        self._cheat_flags: tuple[bool, bool, bool] = (False, False, False)

        self._menu: tuple[str, ...] = ()
        self._selected = 0
        self._highscores: tuple[tuple[str, int], ...] = ()
        self._name = ""
        self._final_score = 0

        self._cell = 0
        self._origin_x = 0
        self._origin_y = 0

    # -- geometry --------------------------------------------------------

    def _fit_maze(self, width: int, height: int) -> None:
        """Pick the cell size that fits the maze, and centre it."""
        usable_height = self._canvas.height - HUD_HEIGHT
        self._cell = max(
            1, min(self._canvas.width // width, usable_height // height)
        )
        self._origin_x = (self._canvas.width - width * self._cell) // 2
        self._origin_y = (usable_height - height * self._cell) // 2

    def _pixel(self, x: float, y: float) -> tuple[int, int]:
        """Cell coordinates to the pixel they point at."""
        return (
            self._origin_x + int(x * self._cell),
            self._origin_y + int(y * self._cell),
        )

    def _cell_origin(self, x: float, y: float) -> tuple[int, int]:
        """Cell coordinates to the top-left pixel of their cell."""
        return (
            self._origin_x + int(x) * self._cell,
            self._origin_y + int(y) * self._cell,
        )

    # -- event handlers: state only --------------------------------------

    def update(self, event: Event) -> None:
        """Store the event, and mark the screen as needing a repaint."""
        super().update(event)
        self._dirty = True

    def invalidate(self) -> None:
        """Force a full repaint, e.g. when the window is uncovered."""
        self._dirty = True

    def on_screen_changed(self, event: ScreenChanged) -> None:
        """Remember which screen has to be drawn."""
        self._screen = event.screen

    def on_maze_generated(self, event: MazeGenerated) -> None:
        """Store the new maze and repaint the static layer."""
        self._grid = event.grid
        self._food.clear()
        self._ghosts.clear()
        self._ghost_states.clear()
        self._fit_maze(event.width, event.height)
        self._redraw_background()

    def on_food_spawned(self, event: FoodSpawned) -> None:
        """Remember a food item and paint it in the static layer."""
        self._food[(event.x, event.y)] = event.kind
        self._draw_food(event.x, event.y, event.kind)

    def on_food_collected(self, event: FoodCollected) -> None:
        """Forget the item and repaint that single cell as floor."""
        self._food.pop((event.x, event.y), None)
        x, y = self._cell_origin(event.x, event.y)
        self._canvas.background.rect(
            x, y, self._cell, self._cell, FLOOR_COLOR
        )

    def on_pacman_moved(self, event: PacmanMoved) -> None:
        """Track Pac-Man's position and facing."""
        self._pacman = (event.x, event.y)

        if event.direction is not Direction.NONE:
            self._direction = event.direction

    def on_ghost_moved(self, event: GhostMoved) -> None:
        """Track one ghost's position."""
        self._ghosts[event.index] = (event.x, event.y)

    def on_ghost_state_changed(self, event: GhostStateChanged) -> None:
        """Track one ghost's state, which decides how it is drawn."""
        self._ghost_states[event.index] = event.state

    def on_score_changed(self, event: ScoreChanged) -> None:
        """Update the score shown in the HUD."""
        self._score = event.score

    def on_lives_changed(self, event: LivesChanged) -> None:
        """Update the lives shown in the HUD."""
        self._lives = event.lives

    def on_level_started(self, event: LevelStarted) -> None:
        """Update the level shown in the HUD."""
        self._level = event.level
        self._total_levels = event.total_levels
        self._time_left = event.time_limit

    def on_time_changed(self, event: TimeChanged) -> None:
        """Update the remaining time shown in the HUD."""
        self._time_left = event.seconds_left

    def on_cheats_changed(self, event: CheatsChanged) -> None:
        """Update the cheat indicator of the HUD."""
        self._cheats_enabled = event.enabled
        self._cheat_flags = (
            event.invincible,
            event.ghosts_frozen,
            event.speed_boost,
        )

    def on_pacman_caught(self, event: PacmanCaught) -> None:
        """Flash Pac-Man white for a few frames."""
        self._caught_frames = CAUGHT_FRAMES

    def on_menu_changed(self, event: MenuChanged) -> None:
        """Store the entries of the active menu and the selected one."""
        self._menu = event.items
        self._selected = event.selected

    def on_highscores_changed(self, event: HighscoresChanged) -> None:
        """Store the highscore table."""
        self._highscores = event.entries

    def on_name_entry_changed(self, event: NameEntryChanged) -> None:
        """Store the name being typed and the score it will be saved."""
        self._name = event.name
        self._final_score = event.score

    # -- drawing helpers -------------------------------------------------

    def _redraw_background(self) -> None:
        """Repaint maze and every remaining food item from scratch."""
        background = self._canvas.background
        background.fill(FLOOR_COLOR)

        for row, cells in enumerate(self._grid):
            for col, cell in enumerate(cells):
                if cell == 1:
                    x, y = self._cell_origin(col, row)
                    background.rect(
                        x, y, self._cell, self._cell, WALL_COLOR
                    )

        for (x_pos, y_pos), kind in self._food.items():
            self._draw_food(x_pos, y_pos, kind)

    def _draw_food(self, x: float, y: float, kind: FoodType) -> None:
        """Paint one pacgum in the static layer."""
        if not self._cell:
            return

        center_x, center_y = self._pixel(x, y)

        if kind is FoodType.SUPER_PACGUM:
            radius = max(3, self._cell // 3)
            color = SUPER_PACGUM_COLOR
        else:
            radius = max(1, self._cell // 8)
            color = PACGUM_COLOR

        self._canvas.background.circle(center_x, center_y, radius, color)

    def _draw_pacman(self) -> None:
        """Body then mouth: the mouth is floor-coloured, so it cuts out."""
        center_x, center_y = self._pixel(*self._pacman)
        radius = max(2, self._cell // 2 - 1)
        color = CAUGHT_COLOR if self._caught_frames else PACMAN_COLOR

        self._canvas.frame.circle(center_x, center_y, radius, color)

        step_x, step_y = self._direction.value
        self._canvas.frame.wedge(
            center_x, center_y, radius, step_x, step_y, FLOOR_COLOR
        )

    def _draw_ghosts(self) -> None:
        """Round head, square skirt, two eyes; state picks the colour."""
        radius = max(2, self._cell // 2 - 1)

        for index, (x_pos, y_pos) in self._ghosts.items():
            state = self._ghost_states.get(index, GhostState.CHASE)
            center_x, center_y = self._pixel(x_pos, y_pos)

            if state is not GhostState.EATEN:
                color = (
                    FRIGHTENED_COLOR
                    if state is GhostState.FRIGHTENED
                    else GHOST_COLORS[index % len(GHOST_COLORS)]
                )
                self._canvas.frame.circle(
                    center_x, center_y, radius, color
                )
                self._canvas.frame.rect(
                    center_x - radius,
                    center_y,
                    2 * radius + 1,
                    radius + 1,
                    color,
                )

            # An eaten ghost is drawn as a pair of eyes going home.
            eye = max(1, radius // 3)
            self._canvas.frame.rect(
                center_x - eye - 1, center_y - eye, eye, eye, EYE_COLOR
            )
            self._canvas.frame.rect(
                center_x + 1, center_y - eye, eye, eye, EYE_COLOR
            )

    def _draw_hud(self) -> None:
        """One line of text under the maze.

        The fields are spread over the width of the window instead of
        sitting at fixed pixels, so the HUD still fits when the maze -
        and therefore the window - is configured smaller.
        """
        top = self._canvas.height - TEXT_HEIGHT
        fields = [
            f"SCORE {self._score}",
            f"LIVES {self._lives}",
            f"LEVEL {self._level}/{self._total_levels}",
            f"TIME {self._time_left}",
        ]
        colors = [TEXT_COLOR] * len(fields)

        if self._cheats_enabled:
            fields.append(f"CHEAT {self._cheat_label()}")
            colors.append(CHEAT_COLOR)

        step = self._canvas.width // len(fields)

        for index, (text, color) in enumerate(zip(fields, colors)):
            self._canvas.text(8 + index * step, top, color, text)

    def _cheat_label(self) -> str:
        """Return the initials of the cheats currently active."""
        active = [
            initial
            for initial, flag in zip("IFS", self._cheat_flags)
            if flag
        ]

        return "".join(active) if active else "ON"

    def _centered(self, y: int, color: int, text: str) -> None:
        """Queue a line of text horizontally centred on the window."""
        width = len(text) * FONT_WIDTH
        x = max(0, (self._canvas.width - width) // 2)
        self._canvas.text(x, y, color, text)

    def _clear_frame(self) -> None:
        """Start a text screen from a black frame."""
        self._canvas.frame.fill(FLOOR_COLOR)

    # -- screens ---------------------------------------------------------

    def _render_menu(self) -> None:
        """Main menu: title, entries, and the best score so far."""
        self._clear_frame()
        self._centered(120, TITLE_COLOR, "GHOSTS! MORE GHOSTS!")
        self._centered(150, DIM_TEXT_COLOR, "a Pac-Man clone")

        for index, entry in enumerate(self._menu):
            selected = index == self._selected
            color = SELECTED_COLOR if selected else TEXT_COLOR
            label = f"> {entry} <" if selected else entry
            self._centered(230 + index * LINE_HEIGHT * 2, color, label)

        if self._highscores:
            name, points = self._highscores[0]
            self._centered(
                # One full TEXT_HEIGHT above the hint line below, or the
                # two lines overlap.
                self._canvas.height - 40 - TEXT_HEIGHT,
                DIM_TEXT_COLOR,
                f"best: {name} {points}",
            )

        self._centered(
            self._canvas.height - 40,
            DIM_TEXT_COLOR,
            "arrows to choose, ENTER to validate",
        )

    def _render_highscores(self) -> None:
        """Top ten scores, best first."""
        self._clear_frame()
        self._centered(100, TITLE_COLOR, "HIGHSCORES")

        if not self._highscores:
            self._centered(180, DIM_TEXT_COLOR, "no score yet")
        else:
            for index, (name, points) in enumerate(self._highscores):
                self._centered(
                    160 + index * LINE_HEIGHT,
                    TEXT_COLOR,
                    f"{index + 1:2d}. {name:<10} {points:>6}",
                )

        self._centered(
            self._canvas.height - 40, DIM_TEXT_COLOR, "ESC to go back"
        )

    def _render_instructions(self) -> None:
        """Controls and rules, as a block centred on the window."""
        self._clear_frame()
        self._centered(60, TITLE_COLOR, "INSTRUCTIONS")

        block = len(INSTRUCTIONS) * LINE_HEIGHT
        start = max(100, (self._canvas.height - block) // 2)

        for index, line in enumerate(INSTRUCTIONS):
            self._centered(start + index * LINE_HEIGHT, TEXT_COLOR, line)

        self._centered(
            self._canvas.height - 40, DIM_TEXT_COLOR, "ESC to go back"
        )

    def _render_game(self) -> None:
        """Maze, food, entities and HUD."""
        self._canvas.begin_frame()

        if self._grid:
            self._draw_pacman()
            self._draw_ghosts()

        self._draw_hud()

    def _render_pause(self) -> None:
        """The frozen game, with the pause menu on a panel over it."""
        self._render_game()

        # Title and entries share one uniform step, and the panel is
        # sized from that: it always wraps its content exactly.
        step = TEXT_HEIGHT + LINE_HEIGHT
        lines = 1 + len(self._menu)
        height = PANEL_PADDING * 2 + TEXT_HEIGHT + (lines - 1) * step

        self._draw_panel(PANEL_TOP, height)

        top = PANEL_TOP + PANEL_PADDING
        self._centered(top, TITLE_COLOR, "PAUSED")

        for index, entry in enumerate(self._menu):
            selected = index == self._selected
            color = SELECTED_COLOR if selected else TEXT_COLOR
            label = f"> {entry} <" if selected else entry
            self._centered(top + (index + 1) * step, color, label)

    def _draw_panel(self, top: int, height: int) -> None:
        """Paint a framed box so overlay text reads as a panel.

        Without the frame, the plain black rectangle simply erases a
        band of the maze - and the entities already drawn in it - which
        looks like a rendering glitch rather than a dialog.
        """
        width = self._canvas.width * 3 // 4
        left = (self._canvas.width - width) // 2

        self._canvas.frame.rect(
            left, top, width, height, PANEL_BORDER_COLOR
        )
        self._canvas.frame.rect(
            left + PANEL_BORDER,
            top + PANEL_BORDER,
            width - 2 * PANEL_BORDER,
            height - 2 * PANEL_BORDER,
            FLOOR_COLOR,
        )

    def _render_end(self, title: str, message: str) -> None:
        """Game over and victory screens, with the name prompt."""
        self._clear_frame()
        self._centered(120, TITLE_COLOR, title)
        self._centered(160, TEXT_COLOR, message)
        self._centered(200, TEXT_COLOR, f"FINAL SCORE {self._final_score}")
        self._centered(260, DIM_TEXT_COLOR, "enter your name:")
        self._centered(290, SELECTED_COLOR, f"{self._name}_")
        self._centered(
            self._canvas.height - 40,
            DIM_TEXT_COLOR,
            "letters and spaces, 10 max, ENTER to save",
        )

    def render(self) -> None:
        """Draw one frame, skipping the screens that cannot have moved.

        While a game is running something moves on every frame, so the
        frame is always redrawn. Every other screen is static: redrawing
        it only when an event changed it removes the text flicker.
        """
        if self._screen is not Screen.PLAYING and not self._dirty:
            return

        self._dirty = False

        if self._caught_frames:
            self._caught_frames -= 1

        match self._screen:
            case Screen.MENU:
                self._render_menu()
            case Screen.HIGHSCORES:
                self._render_highscores()
            case Screen.INSTRUCTIONS:
                self._render_instructions()
            case Screen.PLAYING:
                self._render_game()
            case Screen.PAUSED:
                self._render_pause()
            case Screen.GAME_OVER:
                self._render_end("GAME OVER", "the ghosts got you")
            case Screen.VICTORY:
                self._render_end("VICTORY!", "every level cleared, waka-waka")

        self._canvas.present()
