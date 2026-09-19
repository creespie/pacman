"""Thin wrapper around MLX: the only module that imports it.

Everything above this file works with pixels and colours, never with
MLX handles. If the graphics library ever changes, only this file does.
"""

from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:  # the real import happens in Canvas, see below
    from mlx import Mlx

# Byte written in the 4th slot of every pixel. MiniLibX historically uses
# 0x00 for "opaque", some bindings use 0xFF.
OPAQUE: int = 0xFF

# mlx_string_put hands the colour to the GPU without swizzling it, while
# the swapchain is BGRA: red and blue come out swapped for text (images
# are fine, they are written byte by byte by to_pixel). Set this to
# False if strings ever come out with the wrong colours on another
# machine; it is the only place that needs changing.
STRING_COLOR_SWAPS_RB = True

# MiniLibX queues every blit in a list of VK_NB_DRAW = 64 entries and
# flushes it to the screen as soon as it is full. One image counts as
# one entry and *every character* of mlx_string_put counts as one too,
# so a frame holding more than ~63 characters gets cut in half and is
# presented in two pieces: the player sees the text being typed on, and
# it flickers. Keep a frame under this budget.
MAX_DRAWS_PER_FRAME = 64

# Metrics of the MLX built-in font atlas (1140 px wide, 95 glyphs): one
# character is exactly 10 px wide. The glyphs are not drawn at ``y``
# itself but a little below it, and a line ends up occupying roughly
# [y + 15, y + 33] - measured on screen, since mlx_string_put offers no
# way to ask. TEXT_HEIGHT is what a caller must reserve for one line.
FONT_WIDTH = 10
TEXT_HEIGHT = 34

ESCAPE_KEY = 65307

# X11 event sent when the window manager closes the window.
DESTROY_NOTIFY = 17


def to_pixel(color: int) -> bytes:
    """Turn 0xRRGGBB into the 4 bytes MLX stores in memory (B, G, R, A)."""
    return bytes((
        color & 0xFF,
        (color >> 8) & 0xFF,
        (color >> 16) & 0xFF,
        OPAQUE,
    ))


def to_string_color(color: int) -> int:
    """Turn 0xRRGGBB into the value mlx_string_put actually draws."""
    if not STRING_COLOR_SWAPS_RB:
        return color

    return (
        (color & 0x0000FF) << 16 | (color & 0x00FF00) | (color >> 16) & 0xFF
    )


class Image:
    """An MLX image, drawn into by writing bytes directly in its buffer."""

    def __init__(
        self, mlx: "Mlx", mlx_ptr: Any, width: int, height: int
    ) -> None:
        self.width = width
        self.height = height
        self.ptr = mlx.mlx_new_image(mlx_ptr, width, height)
        self.data, bits, self.stride, _fmt = mlx.mlx_get_data_addr(self.ptr)
        self.px_size = bits // 8

    def copy_from(self, other: "Image") -> None:
        """Overwrite this whole image with another one (single memcpy)."""
        self.data[:] = other.data

    def fill(self, color: int) -> None:
        """Paint the whole image in one colour."""
        self.rect(0, 0, self.width, self.height, color)

    def rect(self, x: int, y: int, w: int, h: int, color: int) -> None:
        """Filled rectangle, clipped to the image bounds.

        One slice assignment per row instead of one per pixel: the copy
        then happens in C, which is what makes a full redraw affordable.
        """
        x0, y0 = max(0, x), max(0, y)
        x1 = min(self.width, x + w)
        y1 = min(self.height, y + h)
        if x0 >= x1 or y0 >= y1:
            return
        row = to_pixel(color) * (x1 - x0)
        for row_y in range(y0, y1):
            start = row_y * self.stride + x0 * self.px_size
            self.data[start:start + len(row)] = row

    def circle(self, cx: int, cy: int, radius: int, color: int) -> None:
        """Filled circle: one horizontal chord per row."""
        for dy in range(-radius, radius + 1):
            half = int((radius * radius - dy * dy) ** 0.5)
            self.rect(cx - half, cy + dy, 2 * half + 1, 1, color)

    def wedge(self, cx: int, cy: int, radius: int,
              dx: float, dy: float, color: int) -> None:
        """Triangle from the centre towards (dx, dy): Pac-Man's mouth."""
        for step in range(radius + 1):
            half = int(step * 0.7)
            if dx:
                x = cx + int(dx) * step
                self.rect(x, cy - half, 1, 2 * half + 1, color)
            elif dy:
                y = cy + int(dy) * step
                self.rect(cx - half, y, 2 * half + 1, 1, color)


class Canvas:
    """Window, double buffering and input, with no game logic inside.

    Two layers: `background` holds what rarely changes (maze, uneaten
    food), `frame` is rebuilt every tick from the background plus the
    moving entities. Text is queued and flushed after the image, since
    MLX draws strings straight on the window.
    """

    def __init__(self, width: int, height: int, title: str) -> None:
        # Imported here and not at module level: a machine without
        # MiniLibX must get the clean message of make_canvas, not an
        # ImportError traceback at start-up.
        from mlx import Mlx

        self.width = width
        self.height = height
        self._mlx = Mlx()
        self._mlx_ptr = self._mlx.mlx_init()

        # mlx_init returns NULL when the backend cannot start (no
        # display, no Vulkan driver). Passing that NULL to any other
        # MiniLibX call segfaults inside the C library, and a segfault
        # is not something a try/except can turn into a message, so the
        # pointer is checked here instead.
        if not self._mlx_ptr:
            raise RuntimeError(
                "MiniLibX could not initialize its backend "
                "(no display, or no Vulkan driver available)"
            )

        self._win_ptr = self._mlx.mlx_new_window(
            self._mlx_ptr, width, height, title)

        if not self._win_ptr:
            raise RuntimeError("MiniLibX could not open a window")
        self.background = Image(self._mlx, self._mlx_ptr, width, height)
        self.frame = Image(self._mlx, self._mlx_ptr, width, height)
        self._texts: list[tuple[int, int, int, str]] = []

    def begin_frame(self) -> None:
        """Start a new frame from a clean copy of the background."""
        self.frame.copy_from(self.background)

    def text(self, x: int, y: int, color: int, value: str) -> None:
        """Queue a string; it is drawn on top of the image by present()."""
        self._texts.append((x, y, color, value))

    @property
    def draw_count(self) -> int:
        """Blits the next present will cost: the frame, plus one per

        character of queued text. Above MAX_DRAWS_PER_FRAME the frame is
        torn in two by MiniLibX, so this is worth keeping an eye on.
        """
        return 1 + sum(len(text) for _x, _y, _color, text in self._texts)

    def present(self) -> None:
        """Push the frame to the window, then the queued strings."""
        self._mlx.mlx_put_image_to_window(
            self._mlx_ptr, self._win_ptr, self.frame.ptr, 0, 0)

        for x, y, color, value in self._texts:
            self._mlx.mlx_string_put(
                self._mlx_ptr, self._win_ptr, x, y,
                to_string_color(color), value)

        self._texts.clear()

        # Flush the batch here, so that one call to present is one frame
        # on screen instead of whatever MiniLibX decides to cut.
        self._mlx.mlx_do_sync(self._mlx_ptr)

    def on_key(self, handler: Callable[[int], None]) -> None:
        """Register a callback receiving the keycode of each key press."""
        def wrapper(keycode: int, _param: Any) -> int:
            handler(keycode)
            return 0

        self._mlx.mlx_key_hook(self._win_ptr, wrapper, None)

    def on_close(self, handler: Callable[[], None]) -> None:
        """Register a callback for the window close button."""
        def wrapper(_param: Any) -> int:
            handler()
            return 0

        self._mlx.mlx_hook(
            self._win_ptr, DESTROY_NOTIFY, 0, wrapper, None)

    def on_expose(self, handler: Callable[[], None]) -> None:
        """Register a callback for when the window has to repaint.

        A view that only redraws what changed still has to redraw
        everything when the window manager uncovers the window.
        """
        def wrapper(_param: Any) -> None:
            handler()

        self._mlx.mlx_expose_hook(self._win_ptr, wrapper, None)

    def on_tick(self, handler: Callable[[], None]) -> None:
        """Register the callback MLX calls once per frame."""
        def wrapper(_param: Any) -> int:
            handler()
            return 0

        self._mlx.mlx_loop_hook(self._mlx_ptr, wrapper, None)

    def run(self) -> None:
        """Hand control over to MLX. Returns only after stop()."""
        self._mlx.mlx_loop(self._mlx_ptr)

    def stop(self) -> None:
        """Leave the MLX loop so the program can shut down cleanly."""
        self._mlx.mlx_loop_exit(self._mlx_ptr)


def make_canvas(width: int, height: int, title: str) -> Optional[Canvas]:
    """Build a Canvas, returning None instead of raising on failure."""
    try:
        return Canvas(width, height, title)
    except Exception as error:  # no display, library missing, ...
        print(f"graphics unavailable: {error}")
        return None
