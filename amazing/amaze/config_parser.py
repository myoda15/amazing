"""Configuration file parsing for A-Maze-ing.

The configuration file is a plain-text file with one ``KEY=VALUE`` pair
per line. Blank lines and lines starting with ``#`` are ignored.

Mandatory keys
--------------
====================  =====================================
Key                   Meaning
====================  =====================================
``WIDTH``             Maze width in cells (int >= 1)
``HEIGHT``            Maze height in cells (int >= 1)
``ENTRY``             Entry cell as ``x,y``
``EXIT``              Exit cell as ``x,y``
``OUTPUT_FILE``       Output filename
``PERFECT``           ``True``/``False`` (single-path maze)
====================  =====================================

Optional keys
-------------
====================  =====================================
Key                   Meaning
====================  =====================================
``SEED``              Integer seed for reproducibility
``ALGORITHM``         ``backtracker`` or ``prim``
``DRAW_42``           ``True``/``False`` (embed "42")
``BRAID_FACTOR``      Float 0.0-1.0 (loops when not perfect)
====================  =====================================
"""

from __future__ import annotations

from dataclasses import dataclass

Coord = tuple[int, int]

_MANDATORY_KEYS = (
    "WIDTH", "HEIGHT", "ENTRY", "EXIT", "OUTPUT_FILE", "PERFECT",
)
_BOOL_TRUE = {"true", "1", "yes", "on"}
_BOOL_FALSE = {"false", "0", "no", "off"}


class ConfigError(Exception):
    """Raised when the configuration file is missing or invalid."""


@dataclass
class Config:
    """Validated maze configuration.

    Attributes:
        width: Maze width in cells.
        height: Maze height in cells.
        entry: ``(x, y)`` entry cell.
        exit: ``(x, y)`` exit cell.
        output_file: Destination filename for the maze.
        perfect: Whether the maze must have a single solution.
        seed: Optional reproducibility seed.
        algorithm: Generation algorithm name.
        draw_42: Whether to embed the "42" pattern.
        braid_factor: Fraction of extra openings when not perfect.
    """

    width: int
    height: int
    entry: Coord
    exit: Coord
    output_file: str
    perfect: bool
    seed: int | None = None
    algorithm: str = "backtracker"
    draw_42: bool = True
    braid_factor: float = 0.12


def parse_config(path: str) -> Config:
    """Read and validate a configuration file.

    Args:
        path: Path to the configuration file.

    Returns:
        A validated :class:`Config` instance.

    Raises:
        ConfigError: If the file cannot be read or is invalid.
    """
    values = _read_pairs(path)
    missing = [key for key in _MANDATORY_KEYS if key not in values]
    if missing:
        raise ConfigError(f"missing mandatory key(s): {', '.join(missing)}")
    return Config(
        width=_parse_positive_int("WIDTH", values["WIDTH"]),
        height=_parse_positive_int("HEIGHT", values["HEIGHT"]),
        entry=_parse_coord("ENTRY", values["ENTRY"]),
        exit=_parse_coord("EXIT", values["EXIT"]),
        output_file=_parse_filename("OUTPUT_FILE", values["OUTPUT_FILE"]),
        perfect=_parse_bool("PERFECT", values["PERFECT"]),
        seed=_parse_optional_seed(values.get("SEED")),
        algorithm=_parse_algorithm(values.get("ALGORITHM")),
        draw_42=_parse_optional_bool("DRAW_42", values.get("DRAW_42"), True),
        braid_factor=_parse_braid(values.get("BRAID_FACTOR")),
    )


def _read_pairs(path: str) -> dict[str, str]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            lines = handle.readlines()
    except FileNotFoundError as exc:
        raise ConfigError(f"configuration file not found: {path}") from exc
    except OSError as exc:
        raise ConfigError(f"cannot read configuration file: {exc}") from exc
    values: dict[str, str] = {}
    for number, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ConfigError(f"line {number}: expected KEY=VALUE")
        key, value = line.split("=", 1)
        key = key.strip().upper()
        if not key:
            raise ConfigError(f"line {number}: empty key")
        values[key] = value.strip()
    return values


def _parse_positive_int(key: str, value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise ConfigError(f"{key} must be an integer, got {value!r}") from exc
    if number < 1:
        raise ConfigError(f"{key} must be >= 1, got {number}")
    return number


def _parse_coord(key: str, value: str) -> Coord:
    parts = value.split(",")
    if len(parts) != 2:
        raise ConfigError(f"{key} must be 'x,y', got {value!r}")
    try:
        x = int(parts[0].strip())
        y = int(parts[1].strip())
    except ValueError as exc:
        raise ConfigError(f"{key} must be integers 'x,y'") from exc
    return (x, y)


def _parse_filename(key: str, value: str) -> str:
    if not value:
        raise ConfigError(f"{key} must not be empty")
    return value


def _parse_bool(key: str, value: str) -> bool:
    token = value.strip().lower()
    if token in _BOOL_TRUE:
        return True
    if token in _BOOL_FALSE:
        return False
    raise ConfigError(f"{key} must be True or False, got {value!r}")


def _parse_optional_bool(key: str, value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return _parse_bool(key, value)


def _parse_optional_seed(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ConfigError(f"SEED must be an integer, got {value!r}") from exc


def _parse_algorithm(value: str | None) -> str:
    if value is None or value == "":
        return "backtracker"
    token = value.strip().lower()
    if token not in ("backtracker", "prim"):
        raise ConfigError(
            f"ALGORITHM must be 'backtracker' or 'prim', got {value!r}"
        )
    return token


def _parse_braid(value: str | None) -> float:
    if value is None or value == "":
        return 0.12
    try:
        factor = float(value)
    except ValueError as exc:
        raise ConfigError(
            f"BRAID_FACTOR must be a number, got {value!r}"
        ) from exc
    if not 0.0 <= factor <= 1.0:
        raise ConfigError(f"BRAID_FACTOR must be 0.0-1.0, got {factor}")
    return factor
