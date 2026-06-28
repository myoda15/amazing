"""A-Maze-ing application package.

This package holds the command-line application helpers built on top of
the reusable :mod:`mazegen` module:

* :mod:`amaze.config_parser` - parse and validate the configuration file.
* :mod:`amaze.maze_io` - write the maze to the output file.
* :mod:`amaze.renderer` - terminal rendering and the interactive viewer.

The reusable maze-generation logic itself lives in the standalone
top-level module :mod:`mazegen`, which is packaged separately for pip.
"""
