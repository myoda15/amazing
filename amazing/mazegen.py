"""A-Maze-ing: reusable maze generation module.

This standalone module provides :class:`MazeGenerator`, a self-contained
maze generator designed to be imported by other projects. It supports
reproducible random generation (via a seed), "perfect" mazes (exactly
one path between any two cells), an embedded decorative "42" pattern made
of fully closed cells, and a built-in shortest-path solver.

Wall encoding
-------------
Each cell stores its closed walls as a 4-bit mask. A *set* bit means the
wall is **closed**, a cleared bit means it is **open**:

====  =========
Bit   Direction
====  =========
0     North (LSB)
1     East
2     South
3     West
====  =========

Quick start
-----------
Basic usage::

    from mazegen import MazeGenerator

    gen = MazeGenerator(
        width=20,
        height=15,
        entry=(0, 0),
        exit=(19, 14),
        perfect=True,
        seed=42,
    )
    gen.generate()

    grid = gen.grid              # rows of 4-bit wall masks
    path = gen.solution          # list of "N"/"E"/"S"/"W" moves
    for row in gen.to_hex_rows():
        print(row)               # hex rows, as in the output file

Custom parameters
-----------------
``width`` / ``height`` set the maze size in cells. ``entry`` / ``exit``
are ``(x, y)`` coordinates (``x`` grows east, ``y`` grows south).
``seed`` makes generation reproducible (when ``None`` a random seed is
chosen and stored on :attr:`MazeGenerator.seed`). ``perfect`` toggles a
single-solution maze. ``algorithm`` selects the generation strategy,
either ``"backtracker"`` (recursive backtracker) or ``"prim"``
(randomized Prim).

Accessing the structure and the solution
----------------------------------------
After :meth:`MazeGenerator.generate`:

* :attr:`MazeGenerator.grid` -> ``list[list[int]]`` of wall masks.
* :attr:`MazeGenerator.glyph` -> ``set`` of ``(x, y)`` cells forming the
  fully closed "42" pattern.
* :attr:`MazeGenerator.solution` -> shortest path as direction letters.
* :meth:`MazeGenerator.solution_cells` -> the path as ``(x, y)`` cells.
* :meth:`MazeGenerator.to_hex_rows` -> one hex string per maze row.
"""

from __future__ import annotations

import random
from collections import deque

__version__ = "1.0.0"
__all__ = ["MazeGenerator", "MazeError"]

Coord = tuple[int, int]

# All four walls closed.
_FULL = 0xF

# (letter, dx, dy, own_bit, opposite_bit)
_DIRECTIONS: tuple[tuple[str, int, int, int, int], ...] = (
    ("N", 0, -1, 0x1, 0x4),
    ("E", 1, 0, 0x2, 0x8),
    ("S", 0, 1, 0x4, 0x1),
    ("W", -1, 0, 0x8, 0x2),
)

# Pixel font for the decorative "42" pattern (5 rows tall, 4 wide each).
_GLYPH_4: tuple[str, ...] = (
    "X..X",
    "X..X",
    "XXXX",
    "...X",
    "...X",
)
_GLYPH_2: tuple[str, ...] = (
    "XXXX",
    "...X",
    "XXXX",
    "X...",
    "XXXX",
)
_GLYPH_HEIGHT = 5
_GLYPH_GAP = 1
_GLYPH_WIDTH = 4 + _GLYPH_GAP + 4
_GLYPH_MARGIN = 1

#: Minimum maze width that can host the "42" pattern.
MIN_42_WIDTH = _GLYPH_WIDTH + 2 * _GLYPH_MARGIN
#: Minimum maze height that can host the "42" pattern.
MIN_42_HEIGHT = _GLYPH_HEIGHT + 2 * _GLYPH_MARGIN


class MazeError(Exception):
    """Raised when maze parameters are invalid or generation fails."""


class MazeGenerator:
    """Generate a rectangular maze and solve it.

    Args:
        width: Number of cells horizontally (>= 1).
        height: Number of cells vertically (>= 1).
        entry: ``(x, y)`` start cell, inside the bounds.
        exit: ``(x, y)`` goal cell, inside the bounds and != ``entry``.
        perfect: When ``True`` the maze has exactly one path between any
            two cells. When ``False`` extra openings (loops) are added.
        seed: Seed for reproducible output. ``None`` picks one at random
            and stores it on :attr:`seed`.
        algorithm: ``"backtracker"`` or ``"prim"``.
        draw_42: When ``True`` (and the maze is large enough) embed the
            fully-closed "42" pattern.
        braid_factor: Fraction of removable walls opened when
            ``perfect`` is ``False`` (0.0 - 1.0).

    Raises:
        MazeError: If any parameter is invalid.
    """

    def __init__(
        self,
        width: int,
        height: int,
        entry: Coord = (0, 0),
        exit: Coord = (-1, -1),
        perfect: bool = True,
        seed: int | None = None,
        algorithm: str = "backtracker",
        draw_42: bool = True,
        braid_factor: float = 0.12,
    ) -> None:
        if exit == (-1, -1):
            exit = (width - 1, height - 1)
        self._validate(width, height, entry, exit, algorithm, braid_factor)
        self.width = width
        self.height = height
        self.entry = entry
        self.exit = exit
        self.perfect = perfect
        self.algorithm = algorithm
        self.draw_42 = draw_42
        self.braid_factor = braid_factor
        self.seed: int = seed if seed is not None else random.randrange(2**32)
        self._rng = random.Random(self.seed)
        self.cells: list[list[int]] = []
        self.glyph: set[Coord] = set()
        self.has_42 = False
        self.warnings: list[str] = []
        self._solution: list[str] = []
        self._generated = False

    @staticmethod
    def _validate(
        width: int,
        height: int,
        entry: Coord,
        exit: Coord,
        algorithm: str,
        braid_factor: float,
    ) -> None:
        if not isinstance(width, int) or not isinstance(height, int):
            raise MazeError("width and height must be integers")
        if width < 1 or height < 1:
            raise MazeError("width and height must be >= 1")
        if width * height < 2:
            raise MazeError("maze must contain at least two cells")
        for name, coord in (("entry", entry), ("exit", exit)):
            if (
                not isinstance(coord, tuple)
                or len(coord) != 2
                or not all(isinstance(v, int) for v in coord)
            ):
                raise MazeError(f"{name} must be an (x, y) integer pair")
            x, y = coord
            if not (0 <= x < width and 0 <= y < height):
                raise MazeError(f"{name} {coord} is out of bounds")
        if entry == exit:
            raise MazeError("entry and exit must be different cells")
        if algorithm not in ("backtracker", "prim"):
            raise MazeError(f"unknown algorithm: {algorithm!r}")
        if not 0.0 <= braid_factor <= 1.0:
            raise MazeError("braid_factor must be between 0.0 and 1.0")

    def generate(self) -> None:
        """Build the maze and compute its shortest solution."""
        self.cells = [[_FULL] * self.width for _ in range(self.height)]
        self.warnings = []
        self._place_42()
        self._carve_perfect()
        self._ensure_connectivity()
        if not self.perfect:
            self._braid()
        self._solution = self._solve()
        self._generated = True

    @property
    def grid(self) -> list[list[int]]:
        """Return a deep copy of the wall-mask grid."""
        self._require_generated()
        return [row[:] for row in self.cells]

    @property
    def solution(self) -> list[str]:
        """Return the shortest path as a list of direction letters."""
        self._require_generated()
        return list(self._solution)

    def wall_mask(self, x: int, y: int) -> int:
        """Return the 4-bit closed-wall mask of cell ``(x, y)``."""
        self._require_generated()
        return self.cells[y][x]

    def is_closed(self, x: int, y: int, direction: str) -> bool:
        """Return ``True`` if the wall of ``(x, y)`` toward ``direction``
        ("N"/"E"/"S"/"W") is closed."""
        self._require_generated()
        for letter, _dx, _dy, bit, _opp in _DIRECTIONS:
            if letter == direction:
                return bool(self.cells[y][x] & bit)
        raise MazeError(f"invalid direction: {direction!r}")

    def solution_cells(self) -> list[Coord]:
        """Return the solution path as a list of ``(x, y)`` cells."""
        self._require_generated()
        cells: list[Coord] = [self.entry]
        x, y = self.entry
        offsets = {d[0]: (d[1], d[2]) for d in _DIRECTIONS}
        for move in self._solution:
            dx, dy = offsets[move]
            x, y = x + dx, y + dy
            cells.append((x, y))
        return cells

    def to_hex_rows(self) -> list[str]:
        """Return the maze as one uppercase-hex string per row."""
        self._require_generated()
        return ["".join(f"{mask:X}" for mask in row) for row in self.cells]

    def _place_42(self) -> None:
        self.glyph = set()
        self.has_42 = False
        if not self.draw_42:
            return
        if self.width < MIN_42_WIDTH or self.height < MIN_42_HEIGHT:
            self.warnings.append(
                "maze too small to draw the '42' pattern "
                f"(need at least {MIN_42_WIDTH}x{MIN_42_HEIGHT})"
            )
            return
        glyph = self._build_glyph_cells()
        if self.entry in glyph or self.exit in glyph:
            self.warnings.append(
                "'42' pattern skipped: it would overlap entry/exit"
            )
            return
        if not self._region_connected(glyph):
            self.warnings.append(
                "'42' pattern skipped: it would isolate part of the maze"
            )
            return
        self.glyph = glyph
        self.has_42 = True

    def _build_glyph_cells(self) -> set[Coord]:
        gx0 = (self.width - _GLYPH_WIDTH) // 2
        gy0 = (self.height - _GLYPH_HEIGHT) // 2
        glyph: set[Coord] = set()
        for row in range(_GLYPH_HEIGHT):
            for col in range(4):
                if _GLYPH_4[row][col] == "X":
                    glyph.add((gx0 + col, gy0 + row))
                if _GLYPH_2[row][col] == "X":
                    glyph.add((gx0 + 4 + _GLYPH_GAP + col, gy0 + row))
        return glyph

    def _region_connected(self, glyph: set[Coord]) -> bool:
        """Return ``True`` if every non-glyph cell is reachable."""
        total = self.width * self.height - len(glyph)
        if self.entry in glyph:
            return False
        seen: set[Coord] = {self.entry}
        stack: list[Coord] = [self.entry]
        while stack:
            x, y = stack.pop()
            for _letter, nx, ny, _bit, _opp in self._neighbors(x, y):
                cell = (nx, ny)
                if cell not in glyph and cell not in seen:
                    seen.add(cell)
                    stack.append(cell)
        return len(seen) == total

    def _carve_perfect(self) -> None:
        if self.algorithm == "prim":
            self._carve_prim()
        else:
            self._carve_backtracker()

    def _carve_backtracker(self) -> None:
        start = self.entry
        visited: set[Coord] = {start}
        stack: list[Coord] = [start]
        while stack:
            x, y = stack[-1]
            options = [
                (nx, ny, bit, opp)
                for _l, nx, ny, bit, opp in self._neighbors(x, y)
                if (nx, ny) not in self.glyph and (nx, ny) not in visited
            ]
            if not options:
                stack.pop()
                continue
            nx, ny, bit, opp = self._rng.choice(options)
            self._open_wall(x, y, bit, nx, ny, opp)
            visited.add((nx, ny))
            stack.append((nx, ny))

    def _carve_prim(self) -> None:
        start = self.entry
        visited: set[Coord] = {start}
        frontier: list[tuple[int, int, int, int, int, int]] = []
        self._push_frontier(start, visited, frontier)
        while frontier:
            idx = self._rng.randrange(len(frontier))
            x, y, nx, ny, bit, opp = frontier.pop(idx)
            if (nx, ny) in visited:
                continue
            self._open_wall(x, y, bit, nx, ny, opp)
            visited.add((nx, ny))
            self._push_frontier((nx, ny), visited, frontier)

    def _push_frontier(
        self,
        cell: Coord,
        visited: set[Coord],
        frontier: list[tuple[int, int, int, int, int, int]],
    ) -> None:
        x, y = cell
        for _l, nx, ny, bit, opp in self._neighbors(x, y):
            if (nx, ny) not in self.glyph and (nx, ny) not in visited:
                frontier.append((x, y, nx, ny, bit, opp))

    def _ensure_connectivity(self) -> None:
        """Safety net: attach any stranded non-glyph cell to the tree."""
        reachable = self._reachable_cells(self.entry)
        target = self.width * self.height - len(self.glyph)
        if len(reachable) == target:
            return
        for y in range(self.height):
            for x in range(self.width):
                cell = (x, y)
                if cell in self.glyph or cell in reachable:
                    continue
                self._attach_cell(cell, reachable)

    def _attach_cell(self, cell: Coord, reachable: set[Coord]) -> None:
        x, y = cell
        for _l, nx, ny, bit, opp in self._neighbors(x, y):
            if (nx, ny) in reachable:
                self._open_wall(x, y, bit, nx, ny, opp)
                reachable.update(self._reachable_cells(cell))
                return

    def _braid(self) -> None:
        candidates: list[tuple[int, int, int, int, int, int]] = []
        for y in range(self.height):
            for x in range(self.width):
                if (x, y) in self.glyph:
                    continue
                for letter, nx, ny, bit, opp in self._neighbors(x, y):
                    if letter not in ("E", "S"):
                        continue
                    if (nx, ny) in self.glyph:
                        continue
                    if self.cells[y][x] & bit:
                        candidates.append((x, y, nx, ny, bit, opp))
        self._rng.shuffle(candidates)
        for x, y, nx, ny, bit, opp in candidates:
            if self._rng.random() > self.braid_factor:
                continue
            self._open_wall(x, y, bit, nx, ny, opp)
            if self._creates_open_3x3(x, y, nx, ny):
                self._close_wall(x, y, bit, nx, ny, opp)

    def _creates_open_3x3(self, x1: int, y1: int, x2: int, y2: int) -> bool:
        lo_x, hi_x = min(x1, x2), max(x1, x2)
        lo_y, hi_y = min(y1, y2), max(y1, y2)
        for wx in range(max(0, hi_x - 2), min(lo_x, self.width - 3) + 1):
            for wy in range(max(0, hi_y - 2), min(lo_y, self.height - 3) + 1):
                if self._window_open(wx, wy):
                    return True
        return False

    def _window_open(self, wx: int, wy: int) -> bool:
        for dy in range(3):
            for dx in range(3):
                x, y = wx + dx, wy + dy
                if dx < 2 and self.cells[y][x] & 0x2:
                    return False
                if dy < 2 and self.cells[y][x] & 0x4:
                    return False
        return True

    def _solve(self) -> list[str]:
        start, goal = self.entry, self.exit
        prev: dict[Coord, tuple[Coord, str]] = {}
        queue: deque[Coord] = deque([start])
        seen: set[Coord] = {start}
        while queue:
            x, y = queue.popleft()
            if (x, y) == goal:
                break
            for letter, nx, ny, bit, _opp in self._neighbors(x, y):
                if self.cells[y][x] & bit:
                    continue
                if (nx, ny) in seen:
                    continue
                seen.add((nx, ny))
                prev[(nx, ny)] = ((x, y), letter)
                queue.append((nx, ny))
        if goal not in prev and goal != start:
            raise MazeError("no path between entry and exit")
        moves: list[str] = []
        cur = goal
        while cur != start:
            parent, letter = prev[cur]
            moves.append(letter)
            cur = parent
        moves.reverse()
        return moves

    def _reachable_cells(self, start: Coord) -> set[Coord]:
        seen: set[Coord] = {start}
        stack: list[Coord] = [start]
        while stack:
            x, y = stack.pop()
            for letter, nx, ny, bit, _opp in self._neighbors(x, y):
                if self.cells[y][x] & bit:
                    continue
                if (nx, ny) not in seen:
                    seen.add((nx, ny))
                    stack.append((nx, ny))
        return seen

    def _neighbors(
        self, x: int, y: int
    ) -> list[tuple[str, int, int, int, int]]:
        result: list[tuple[str, int, int, int, int]] = []
        for letter, dx, dy, bit, opp in _DIRECTIONS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                result.append((letter, nx, ny, bit, opp))
        return result

    def _open_wall(
        self, x: int, y: int, bit: int, nx: int, ny: int, opp: int
    ) -> None:
        self.cells[y][x] &= ~bit & _FULL
        self.cells[ny][nx] &= ~opp & _FULL

    def _close_wall(
        self, x: int, y: int, bit: int, nx: int, ny: int, opp: int
    ) -> None:
        self.cells[y][x] |= bit
        self.cells[ny][nx] |= opp

    def _require_generated(self) -> None:
        if not self._generated:
            raise MazeError("call generate() before accessing the maze")
