"""Step 1: disegnare un labirinto statico con MLX.

Da lanciare a mano:  python3 maze_test.py
ESC per uscire.
"""

from typing import Any

from mlx import Mlx

CELL = 24          # pixel per cella
WALL = 0x2121DE    # blu Pac-Man
FLOOR = 0x000000   # nero
GUM = 0xFFB897     # pacgum

# Labirinto finto: '#' muro, '.' pacgum, ' ' corridoio vuoto.
MAZE = [
    "###############",
    "#.............#",
    "#.###.###.###.#",
    "#.#.......#...#",
    "#.#.#####.#.###",
    "#...#   #.#...#",
    "###.#   #.###.#",
    "#.........#...#",
    "#.###.###.#.###",
    "#...........  #",
    "###############",
]


def to_bgra(color: int) -> bytes:
    """0xRRGGBB -> i 4 byte che MLX si aspetta in memoria (B, G, R, A)."""
    return bytes((color & 0xFF, (color >> 8) & 0xFF, (color >> 16) & 0xFF, 0xFF))


class Frame:
    """Un'immagine MLX su cui disegnare scrivendo direttamente nei byte."""

    def __init__(self, mlx: Mlx, mlx_ptr: Any,
                 width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.img = mlx.mlx_new_image(mlx_ptr, width, height)
        self.data, bpp, self.stride, _fmt = mlx.mlx_get_data_addr(self.img)
        self.px_size = bpp // 8  # 32 bit / 8 = 4 byte per pixel

    def offset(self, x: int, y: int) -> int:
        """Indice del primo byte del pixel (x, y) dentro il buffer."""
        return y * self.stride + x * self.px_size

    def fill(self, color: int) -> None:
        """Riempie tutta l'immagine di un colore."""
        row = to_bgra(color) * self.width
        for y in range(self.height):
            start = self.offset(0, y)
            self.data[start:start + len(row)] = row

    def fill_rect(self, x: int, y: int, w: int, h: int, color: int) -> None:
        """Rettangolo pieno, con clipping ai bordi dell'immagine."""
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.width, x + w), min(self.height, y + h)
        if x0 >= x1 or y0 >= y1:
            return
        row = to_bgra(color) * (x1 - x0)
        for row_y in range(y0, y1):
            start = self.offset(x0, row_y)
            self.data[start:start + len(row)] = row

    def fill_circle(self, cx: int, cy: int, radius: int, color: int) -> None:
        """Cerchio pieno: per ogni riga calcolo la mezza corda e riempio."""
        for dy in range(-radius, radius + 1):
            half = int((radius * radius - dy * dy) ** 0.5)
            self.fill_rect(cx - half, cy + dy, 2 * half, 1, color)


def draw_maze(frame: Frame, maze: list[str]) -> None:
    """Disegna la griglia: una cella = un rettangolo CELL x CELL."""
    for row, line in enumerate(maze):
        for col, cell in enumerate(line):
            x = col * CELL
            y = row * CELL
            if cell == "#":
                frame.fill_rect(x, y, CELL, CELL, WALL)
            else:
                frame.fill_rect(x, y, CELL, CELL, FLOOR)
                if cell == ".":
                    frame.fill_circle(x + CELL // 2, y + CELL // 2, 3, GUM)


def main() -> None:
    width = len(MAZE[0]) * CELL
    height = len(MAZE) * CELL + 32  # 32 px in basso per l'HUD

    mlx = Mlx()
    mlx_ptr = mlx.mlx_init()
    win_ptr = mlx.mlx_new_window(mlx_ptr, width, height, "Pacman - maze test")

    frame = Frame(mlx, mlx_ptr, width, height)
    frame.fill(FLOOR)
    draw_maze(frame, MAZE)

    def render(_param: Any) -> int:
        mlx.mlx_put_image_to_window(mlx_ptr, win_ptr, frame.img, 0, 0)
        # il testo va DOPO l'immagine, altrimenti viene coperto
        mlx.mlx_string_put(mlx_ptr, win_ptr, 10, height - 24, 0xFFFFFF,
                           "Score: 0   Lives: 3   Level: 1")
        frame.fill_circle(45, 25, 10, 0xff3300)
        return 0

    def on_key(keycode: int, _param: Any) -> int:
        if keycode == 65307:  # ESC
            mlx.mlx_loop_exit(mlx_ptr)
        return 0

    mlx.mlx_key_hook(win_ptr, on_key, None)
    mlx.mlx_loop_hook(mlx_ptr, render, None)
    mlx.mlx_loop(mlx_ptr)


if __name__ == "__main__":
    main()