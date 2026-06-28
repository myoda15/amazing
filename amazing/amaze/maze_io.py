"""Output file writing for A-Maze-ing.

The output file layout, as required by the subject, is::

    <hex row 0>
    <hex row 1>
    ...
    <hex row H-1>
    <empty line>
    <entry x>,<entry y>
    <exit x>,<exit y>
    <solution path, e.g. SWSE...>

Every line, including the hex rows and the trailing path, ends with a
newline character.
"""

from __future__ import annotations

from typing import Iterable, Sequence

Coord = tuple[int, int]


class MazeIOError(Exception):
    """Raised when the maze output file cannot be written."""


def format_output(
    hex_rows: Iterable[str],
    entry: Coord,
    exit: Coord,
    solution: Sequence[str],
) -> str:
    """Build the full output-file content as a single string.

    Args:
        hex_rows: One uppercase-hex string per maze row.
        entry: ``(x, y)`` entry cell.
        exit: ``(x, y)`` exit cell.
        solution: Path from entry to exit as direction letters.

    Returns:
        The complete file content, newline-terminated.
    """
    lines: list[str] = list(hex_rows)
    lines.append("")
    lines.append(f"{entry[0]},{entry[1]}")
    lines.append(f"{exit[0]},{exit[1]}")
    lines.append("".join(solution))
    return "\n".join(lines) + "\n"


def write_output(
    path: str,
    hex_rows: Iterable[str],
    entry: Coord,
    exit: Coord,
    solution: Sequence[str],
) -> None:
    """Write the maze to ``path`` in the required output format.

    Args:
        path: Destination filename.
        hex_rows: One uppercase-hex string per maze row.
        entry: ``(x, y)`` entry cell.
        exit: ``(x, y)`` exit cell.
        solution: Path from entry to exit as direction letters.

    Raises:
        MazeIOError: If the file cannot be written.
    """
    content = format_output(hex_rows, entry, exit, solution)
    try:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
    except OSError as exc:
        raise MazeIOError(f"cannot write output file {path!r}: {exc}") from exc
