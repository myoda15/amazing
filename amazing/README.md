*This project has been created as part of the 42 curriculum by mande-so, adiogo-f.*

# A-Maze-ing

## Description

**A-Maze-ing** is a configurable maze generator written in Python. From a
simple text configuration file it generates a rectangular maze, solves it,
and writes the result to a file using a compact hexadecimal wall encoding.
It also offers an interactive, coloured terminal viewer.

Highlights:

- Reproducible random generation via a **seed**.
- Optional **perfect** maze (exactly one path between any two cells).
- A decorative **"42"** drawn with fully closed cells in the middle of the
  maze.
- A guarantee that the maze is **valid**: closed outer borders, coherent
  shared walls between neighbours, full connectivity (no isolated cells
  besides the "42"), and no open area larger than 2 cells wide.
- A built-in **shortest-path solver** (BFS).
- An interactive terminal viewer (regenerate, show/hide path, change
  colours).
- The generation logic lives in a **single reusable module**
  (`mazegen.py`) packaged for `pip`.

## Instructions

Requires **Python 3.10+**.

```bash
# 1. (optional) create and activate a virtual environment
python3 -m venv .venv && source .venv/bin/activate

# 2. install the development dependencies (flake8, mypy, build)
make install

# 3. run the generator on the default configuration
make run                 # == python3 a_maze_ing.py config.txt
python3 a_maze_ing.py config.txt

# 4. quality checks
make lint                # flake8 + mypy (mandatory flags)
make lint-strict         # flake8 + mypy --strict

# 5. clean caches / build artifacts
make clean
```

> If your default `python3` is older than 3.10, pass an explicit
> interpreter: `make run PYTHON=python3.12`.

### Interactive viewer

After generating, the program opens a coloured terminal viewer:

```
1. Re-generate a new maze
2. Show/Hide solution path
3. Change wall colours
4. Quit
```

Entry is shown in magenta, exit in red, the solution path in blue, and the
"42" pattern in grey. When standard input is not interactive (e.g. piped),
the viewer exits cleanly.

## Configuration file format

One `KEY=VALUE` pair per line. Blank lines and lines starting with `#` are
comments and are ignored. A working example lives in
[`config.txt`](config.txt).

### Mandatory keys

| Key           | Meaning                              | Example               |
| ------------- | ------------------------------------ | --------------------- |
| `WIDTH`       | Maze width in cells (int ≥ 1)        | `WIDTH=25`            |
| `HEIGHT`      | Maze height in cells (int ≥ 1)       | `HEIGHT=19`           |
| `ENTRY`       | Entry cell as `x,y`                  | `ENTRY=0,0`           |
| `EXIT`        | Exit cell as `x,y` (≠ entry)         | `EXIT=24,18`          |
| `OUTPUT_FILE` | Output filename                      | `OUTPUT_FILE=maze.txt`|
| `PERFECT`     | `True`/`False` (single-path maze)    | `PERFECT=True`        |

### Optional keys

| Key            | Meaning                                  | Default       |
| -------------- | ---------------------------------------- | ------------- |
| `SEED`         | Integer seed for reproducibility         | random        |
| `ALGORITHM`    | `backtracker` or `prim`                  | `backtracker` |
| `DRAW_42`      | `True`/`False`, embed the "42" pattern   | `True`        |
| `BRAID_FACTOR` | `0.0`–`1.0`, extra openings when not perfect | `0.12`    |

Booleans accept `true/false`, `1/0`, `yes/no`, `on/off` (case-insensitive).

## Output file format

The output file encodes **one hexadecimal digit per cell**. A *set* bit
means the wall is **closed**:

| Bit | Direction |
| --- | --------- |
| 0   | North (LSB) |
| 1   | East      |
| 2   | South     |
| 3   | West      |

For example `A` (`1010`) means east and west are closed; `3` (`0011`)
means north and east are closed (south and west are open).

The layout is:

```
<hex row 0>
<hex row 1>
...
<hex row HEIGHT-1>
<empty line>
<entry x>,<entry y>
<exit x>,<exit y>
<shortest path, e.g. SWSESW...>
```

Every line — including the last — ends with `\n`. The path uses the
letters `N`, `E`, `S`, `W`.

## Maze generation algorithm

By default the generator uses the **recursive backtracker** (randomized
depth-first search). A second algorithm, **randomized Prim**, is also
available (`ALGORITHM=prim`).

How the maze is built:

1. Start with every cell fully walled (`0xF`).
2. Reserve the cells of the **"42"** glyph; they stay fully closed and are
   never carved into. (If the maze is too small to host the pattern — less
   than 11×7 — it is skipped and a message is printed.)
3. Carve a **spanning tree** over all remaining cells with the chosen
   algorithm. A spanning tree visits every cell exactly once with no
   cycles, which makes the maze **perfect** and naturally avoids any open
   area (corridors stay one cell wide).
4. If `PERFECT=False`, **braid** the maze: open extra walls to create
   loops, while refusing any opening that would form a 3×3 fully open
   area (corridors never exceed 2 cells).
5. Solve with **breadth-first search** to obtain the shortest path from
   entry to exit.

### Why these algorithms

- The **recursive backtracker** is simple, fast, allocation-light, and
  produces pleasant mazes with long winding corridors and a single
  solution — a perfect fit for the "perfect maze" requirement and for the
  spanning-tree relationship highlighted in the subject.
- **Prim's** algorithm offers a different texture (more branching, shorter
  dead-ends) and demonstrates that the design is not tied to one strategy.
- Both build a spanning tree, so correctness (connectivity, single path,
  no open areas) is guaranteed by construction; borders, wall coherence
  and the solution are checked while the maze is built.

## Reusable module (`mazegen`)

The generation logic is isolated in a single importable file,
[`mazegen.py`](mazegen.py), exposing the `MazeGenerator` class. It has no
third-party dependencies and is packaged for `pip`.

### Build & install the package

```bash
make build                 # == python3 -m build
pip install mazegen-1.0.0-py3-none-any.whl
```

The pre-built artifacts are committed at the repository root
(`mazegen-1.0.0-py3-none-any.whl` and `mazegen-1.0.0.tar.gz`). All sources
needed to rebuild them ([`mazegen.py`](mazegen.py),
[`pyproject.toml`](pyproject.toml)) are included.

### Usage example

```python
from mazegen import MazeGenerator

gen = MazeGenerator(
    width=20,
    height=15,
    entry=(0, 0),
    exit=(19, 14),
    perfect=True,
    seed=42,            # reproducible; omit/None for a random maze
    algorithm="backtracker",  # or "prim"
)
gen.generate()
```

### Passing custom parameters

All generation options are constructor arguments: `width`, `height`,
`entry`, `exit`, `perfect`, `seed`, `algorithm`, `draw_42`, and
`braid_factor`. Invalid parameters raise `mazegen.MazeError`.

### Accessing the structure and the solution

```python
gen.grid             # list[list[int]] of 4-bit wall masks (a copy)
gen.wall_mask(x, y)  # the mask of a single cell
gen.is_closed(x, y, "N")   # True if that wall is closed
gen.glyph            # set of (x, y) cells forming the "42"
gen.solution         # shortest path as ["S", "E", ...]
gen.solution_cells() # the path as [(x, y), ...]
gen.to_hex_rows()    # ["9A3...", ...] one hex string per row
gen.seed             # the seed actually used
```

> The structure returned by the module (4-bit masks) is the same encoding
> used in the output file, but the module is free to evolve independently
> of the file format.

## Advanced features

- **Two generation algorithms** (`backtracker`, `prim`) selectable from the
  config file.
- **Perfect / non-perfect** mazes with a tunable `BRAID_FACTOR`.
- **Reproducibility** through an explicit seed, surfaced in the viewer.
- **Coloured interactive viewer** with regeneration, path toggle, and a
  rotating wall-colour palette.

## Project structure

```
amazing/
├── a_maze_ing.py        # CLI entry point (must keep this name)
├── mazegen.py           # reusable MazeGenerator (the pip module)
├── amaze/               # application package (built on top of mazegen)
│   ├── __init__.py
│   ├── config_parser.py # config file parsing & validation
│   ├── maze_io.py       # output-file writer
│   └── renderer.py      # terminal rendering + interactive menu
├── config.txt           # default configuration
├── pyproject.toml       # build metadata for the mazegen package
├── Makefile             # install / run / debug / clean / lint
├── .flake8              # flake8 configuration
├── .gitignore
└── mazegen-1.0.0-py3-none-any.whl   # built package (root)
```

## Resources

- Jamis Buck, *Mazes for Programmers* (Pragmatic Bookshelf).
- Wikipedia: [Maze generation algorithm](https://en.wikipedia.org/wiki/Maze_generation_algorithm).
- Wikipedia: [Spanning tree](https://en.wikipedia.org/wiki/Spanning_tree).
- Python docs: [`random`](https://docs.python.org/3/library/random.html),
  [`collections.deque`](https://docs.python.org/3/library/collections.html).

### Use of AI

AI was used as a pair-programming assistant for:

- brainstorming the wall-encoding scheme and double-checking it against the
  subject's example (the corner cells `9 / 3 / C / 6`);
- discussing how to keep the "42" glyph from disconnecting the maze and how
  to forbid 3×3 open areas;
- drafting docstrings and this README.

Every suggestion was reviewed, tested, and rewritten by the team until we
could fully explain it. The generation logic and the validity invariants
were verified by hand.

## Team & project management

- **Roles**
  - `mande-so` — maze generation & solver (`mazegen.py`), the "42" glyph
    placement, and the `pip` packaging.
  - `adiogo-f` — config parsing & validation, output-file writer, and the
    interactive terminal renderer.
- **Planning & how it evolved** — we started by agreeing on the wall
  encoding and the output format, then split the work between the reusable
  generator and the application layer (config, I/O, rendering). The "42"
  pattern and the 2-cell corridor constraint were added once the perfect
  maze was solid; the continuous solution-path rendering came last.
- **What worked well / what to improve** — keeping the generator in a
  single dependency-free module made packaging and testing easy. Next time
  we would add automated tests earlier instead of validating by hand.
- **Tools used** — Git, `make`, `flake8`, `mypy`, `build`, and our editors
  of choice.
