#!/usr/bin/env python3
"""A-Maze-ing: command-line maze generator.

Usage::

    python3 a_maze_ing.py config.txt

Reads a configuration file, generates a (possibly perfect) maze with an
embedded "42" pattern, writes it to the configured output file using the
hexadecimal wall encoding, and opens an interactive terminal viewer.

All foreseeable errors (bad arguments, missing or invalid configuration,
impossible maze parameters, unwritable output) are reported with a clear
message and a non-zero exit code instead of an uncaught exception.
"""

from __future__ import annotations

import sys

from amaze.config_parser import Config, ConfigError, parse_config
from amaze.maze_io import MazeIOError, write_output
from amaze.renderer import run_interactive
from mazegen import MazeError, MazeGenerator

_USAGE = "usage: python3 a_maze_ing.py config.txt"


def build_generator(config: Config) -> MazeGenerator:
    """Create and run a generator from a validated configuration."""
    gen = MazeGenerator(
        width=config.width,
        height=config.height,
        entry=config.entry,
        exit=config.exit,
        perfect=config.perfect,
        seed=config.seed,
        algorithm=config.algorithm,
        draw_42=config.draw_42,
        braid_factor=config.braid_factor,
    )
    gen.generate()
    return gen


def run(config_path: str) -> int:
    """Generate the maze, write it, then launch the viewer."""
    try:
        config = parse_config(config_path)
        gen = build_generator(config)
    except (ConfigError, MazeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    for warning in gen.warnings:
        print(f"warning: {warning}", file=sys.stderr)

    try:
        write_output(
            config.output_file,
            gen.to_hex_rows(),
            gen.entry,
            gen.exit,
            gen.solution,
        )
    except MazeIOError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Maze written to '{config.output_file}' (seed={gen.seed}).")
    run_interactive(config, gen)
    return 0


def main(argv: list[str]) -> int:
    """Program entry point. Returns the process exit code."""
    if len(argv) != 2:
        print(_USAGE, file=sys.stderr)
        return 1
    if argv[1] in ("-h", "--help"):
        print(_USAGE)
        return 0
    try:
        return run(argv[1])
    except (EOFError, KeyboardInterrupt):
        print()
        return 0
    except Exception as exc:  # noqa: BLE001  (last-resort safety net)
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
