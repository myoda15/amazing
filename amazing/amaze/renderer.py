"""Terminal rendering and interactive menu for A-Maze-ing.

The maze is drawn with ANSI 256-colour background blocks. Each maze cell
becomes a 2x2 group of "sub-cells" (interior, walls and corners) so that
walls are clearly visible. An interactive menu lets the user regenerate
the maze, toggle the solution path, cycle wall colours, or quit.
"""

from __future__ import annotations

import random

from mazegen import MazeGenerator

from .config_parser import Config
from .maze_io import MazeIOError, write_output

Coord = tuple[int, int]

# ANSI 256-colour codes.
_FLOOR = 16
_ENTRY = 201
_EXIT = 196
_PATH = 39
_GLYPH = 244

#: Rotatable wall colours as ``(name, ansi_code)`` pairs.
WALL_PALETTE: tuple[tuple[str, int], ...] = (
    ("white", 252),
    ("yellow", 190),
    ("cyan", 51),
    ("green", 46),
    ("orange", 208),
    ("purple", 135),
)

_CLEAR = "\x1b[2J\x1b[H"
_RESET = "\x1b[0m"


def _block(code: int) -> str:
    """Return a 2-character coloured block for ANSI ``code``."""
    return f"\x1b[48;5;{code}m  {_RESET}"


def _h_closed(gen: MazeGenerator, x: int, line_y: int) -> bool:
    """Closed state of the horizontal wall at grid line ``line_y``."""
    if not 0 <= x < gen.width:
        return True
    if line_y <= 0:
        return bool(gen.cells[0][x] & 0x1)
    if line_y >= gen.height:
        return bool(gen.cells[gen.height - 1][x] & 0x4)
    return bool(gen.cells[line_y][x] & 0x1)


def _v_closed(gen: MazeGenerator, line_x: int, y: int) -> bool:
    """Closed state of the vertical wall at grid line ``line_x``."""
    if not 0 <= y < gen.height:
        return True
    if line_x <= 0:
        return bool(gen.cells[y][0] & 0x8)
    if line_x >= gen.width:
        return bool(gen.cells[y][gen.width - 1] & 0x2)
    return bool(gen.cells[y][line_x] & 0x8)


def _corner_code(gen: MazeGenerator, x: int, y: int, wall: int) -> int:
    around = ((x - 1, y - 1), (x, y - 1), (x - 1, y), (x, y))
    if any(cell in gen.glyph for cell in around):
        return _GLYPH
    open_corner = (
        not _h_closed(gen, x - 1, y)
        and not _h_closed(gen, x, y)
        and not _v_closed(gen, x, y - 1)
        and not _v_closed(gen, x, y)
    )
    return _FLOOR if open_corner else wall


def _subcell_code(
    gen: MazeGenerator,
    r: int,
    c: int,
    path: set[Coord],
    wall: int,
) -> int:
    odd_r, odd_c = r % 2, c % 2
    if odd_r and odd_c:
        cell = ((c - 1) // 2, (r - 1) // 2)
        if cell in gen.glyph:
            return _GLYPH
        if cell == gen.entry:
            return _ENTRY
        if cell == gen.exit:
            return _EXIT
        if cell in path:
            return _PATH
        return _FLOOR
    if not odd_r and not odd_c:
        return _corner_code(gen, c // 2, r // 2, wall)
    if not odd_r and odd_c:
        x, line_y = (c - 1) // 2, r // 2
        if (x, line_y - 1) in gen.glyph or (x, line_y) in gen.glyph:
            return _GLYPH
        return wall if _h_closed(gen, x, line_y) else _FLOOR
    y, line_x = (r - 1) // 2, c // 2
    if (line_x - 1, y) in gen.glyph or (line_x, y) in gen.glyph:
        return _GLYPH
    return wall if _v_closed(gen, line_x, y) else _FLOOR


def render_to_string(
    gen: MazeGenerator,
    show_path: bool = False,
    wall_index: int = 0,
) -> str:
    """Render the maze as a multi-line ANSI string.

    Args:
        gen: A generated :class:`MazeGenerator`.
        show_path: Whether to highlight the solution path.
        wall_index: Index into :data:`WALL_PALETTE` for wall colour.

    Returns:
        The rendered maze, one canvas row per text line.
    """
    wall = WALL_PALETTE[wall_index % len(WALL_PALETTE)][1]
    path = set(gen.solution_cells()) if show_path else set()
    lines: list[str] = []
    for r in range(2 * gen.height + 1):
        cells = [
            _block(_subcell_code(gen, r, c, path, wall))
            for c in range(2 * gen.width + 1)
        ]
        lines.append("".join(cells))
    return "\n".join(lines)


def _legend(gen: MazeGenerator, show_path: bool, wall_index: int) -> str:
    name = WALL_PALETTE[wall_index % len(WALL_PALETTE)][0]
    head = (
        f"=== A-Maze-ing ===  {gen.width}x{gen.height}  "
        f"seed={gen.seed}  algo={gen.algorithm}  "
        f"perfect={gen.perfect}  walls={name}"
    )
    swatches = (
        f"{_block(_ENTRY)} entry   {_block(_EXIT)} exit   "
        f"{_block(_PATH)} path   {_block(_GLYPH)} 42"
    )
    state = "shown" if show_path else "hidden"
    menu = (
        "1. Re-generate a new maze\n"
        f"2. Show/Hide solution path (now: {state})\n"
        "3. Change wall colours\n"
        "4. Quit"
    )
    return f"{head}\n{swatches}\n{menu}"


def _print_frame(
    gen: MazeGenerator, show_path: bool, wall_index: int
) -> None:
    print(_CLEAR, end="")
    print(render_to_string(gen, show_path, wall_index))
    print(_legend(gen, show_path, wall_index))


def _read_choice() -> str:
    try:
        return input("Choice? (1-4): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return "4"


def _regenerate(config: Config, rng: random.Random) -> MazeGenerator:
    gen = MazeGenerator(
        width=config.width,
        height=config.height,
        entry=config.entry,
        exit=config.exit,
        perfect=config.perfect,
        seed=rng.randrange(2**32),
        algorithm=config.algorithm,
        draw_42=config.draw_42,
        braid_factor=config.braid_factor,
    )
    gen.generate()
    return gen


def run_interactive(config: Config, gen: MazeGenerator) -> None:
    """Run the interactive viewer loop.

    Args:
        config: The configuration used to (re)generate mazes.
        gen: The already-generated initial maze to display first.
    """
    show_path = False
    wall_index = 0
    rng = random.Random()
    current = gen
    while True:
        _print_frame(current, show_path, wall_index)
        choice = _read_choice()
        if choice in ("4", "q", "quit"):
            print("Bye!")
            return
        if choice == "1":
            current = _regenerate(config, rng)
            for warning in current.warnings:
                print(f"warning: {warning}")
            try:
                write_output(
                    config.output_file,
                    current.to_hex_rows(),
                    current.entry,
                    current.exit,
                    current.solution,
                )
            except MazeIOError as exc:
                print(f"error: {exc}")
        elif choice == "2":
            show_path = not show_path
        elif choice == "3":
            wall_index = (wall_index + 1) % len(WALL_PALETTE)
        else:
            print("Invalid choice, please pick 1-4.")
