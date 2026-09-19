"""Loading and validation of the game configuration file.

The subject asks for a forgiving loader: a missing or invalid *value*
must never stop the game. Such a value is clamped to a safe default, a
clear message is logged, and the game keeps going. Unknown keys are
ignored. Only a file that cannot be read or parsed at all is fatal, and
even then the caller gets a ``ConfigError`` with a readable message
instead of a traceback.
"""

import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any


class ConfigError(Exception):
    """Raised when the configuration file cannot be read or parsed."""


@dataclass(frozen=True)
class Config:
    """Game settings loaded from the JSON configuration file."""

    highscore_filename: str = "highscores.json"
    levels: int = 10
    width: int = 21
    height: int = 21
    lives: int = 3
    pacgum: int = 999
    points_per_pacgum: int = 10
    points_per_super_pacgum: int = 50
    points_per_ghost: int = 200
    seed: int = 42
    level_max_time: int = 150


# Allowed range for each integer setting, as (minimum, maximum).
_RANGES: dict[str, tuple[int, int]] = {
    "levels": (1, 999),
    "width": (7, 101),
    "height": (7, 101),
    "lives": (1, 99),
    "pacgum": (1, 100_000),
    "points_per_pacgum": (0, 1_000_000),
    "points_per_super_pacgum": (0, 1_000_000),
    "points_per_ghost": (0, 1_000_000),
    "seed": (0, 2**31 - 1),
    "level_max_time": (5, 3600),
}

Warn = Callable[[str], None]


def _warn_to_stderr(message: str) -> None:
    """Default warning sink: one line on the standard error stream."""
    print(f"config: {message}", file=sys.stderr)


def load_config(
    path: str | Path = "config.json",
    warn: Warn = _warn_to_stderr,
) -> Config:
    """Read, parse and sanitize the configuration file at ``path``.

    Lines or line ends starting with ``#`` are comments, as are ``//``
    line comments; both are stripped before the JSON is parsed.

    Args:
        path: Path of the configuration file.
        warn: Called once per clamped or ignored setting.

    Returns:
        A ``Config`` where every value is guaranteed to be usable.

    Raises:
        ConfigError: If the file cannot be read or is not valid JSON.
    """
    path = Path(path)
    data = _parse_json(path, _strip_comments(_read_text(path)))

    if not isinstance(data, dict):
        raise ConfigError(
            f"{path}: top-level value must be a JSON object, "
            f"got {_json_type_name(data)}"
        )

    return _build_config(data, warn)


def _read_text(path: Path) -> str:
    """Return the file content, converting I/O errors into ConfigError."""
    try:
        with path.open(encoding="utf-8") as stream:
            return stream.read()
    except FileNotFoundError:
        raise ConfigError(f"{path}: file not found") from None
    except IsADirectoryError:
        raise ConfigError(f"{path}: is a directory, not a file") from None
    except PermissionError:
        raise ConfigError(f"{path}: permission denied") from None
    except UnicodeDecodeError:
        raise ConfigError(f"{path}: not a valid UTF-8 text file") from None
    except OSError as error:
        raise ConfigError(f"{path}: {error.strerror or error}") from None


def _strip_comments(text: str) -> str:
    """Remove ``#`` and ``//`` comments found outside of JSON strings.

    Line numbers are preserved so that a parse error still points at the
    right line of the original file.
    """
    lines = []

    for line in text.splitlines():
        in_string = False
        escaped = False

        for index, char in enumerate(line):
            if escaped:
                escaped = False
            elif char == "\\" and in_string:
                escaped = True
            elif char == '"':
                in_string = not in_string
            elif in_string:
                continue
            elif char == "#":
                line = line[:index]
                break
            elif char == "/" and line[index:index + 2] == "//":
                line = line[:index]
                break

        lines.append(line)

    return "\n".join(lines)


def _parse_json(path: Path, text: str) -> Any:
    """Parse JSON text, converting syntax errors into ConfigError."""
    if not text.strip():
        raise ConfigError(
            f"{path}: no content (file is empty or only comments)"
        )

    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise ConfigError(
            f"{path}:{error.lineno}:{error.colno}: {error.msg}"
        ) from None


def _build_config(data: dict[str, Any], warn: Warn) -> Config:
    """Turn raw JSON data into a Config, clamping whatever is wrong."""
    defaults = Config()
    values: dict[str, Any] = {}

    for spec in fields(Config):
        name = spec.name
        default = getattr(defaults, name)

        if name not in data:
            warn(f"missing key '{name}', using default {default!r}")
            values[name] = default
            continue

        values[name] = _sanitize(name, data[name], default, warn)

    for key in data:
        if key not in values:
            warn(f"unknown key '{key}' ignored")

    return Config(**values)


def _sanitize(name: str, value: Any, default: Any, warn: Warn) -> Any:
    """Return ``value`` if it is usable, else a safe fallback."""
    if isinstance(default, str):
        return _sanitize_str(name, value, default, warn)

    # bool is a subclass of int, so it has to be rejected explicitly.
    if isinstance(value, bool) or not isinstance(value, int):
        warn(
            f"'{name}' must be an integer, got {_json_type_name(value)}, "
            f"using default {default!r}"
        )
        return default

    low, high = _RANGES[name]

    if value < low:
        warn(f"'{name}' must be at least {low}, got {value}, clamped")
        return low

    if value > high:
        warn(f"'{name}' must be at most {high}, got {value}, clamped")
        return high

    return value


def _sanitize_str(name: str, value: Any, default: str, warn: Warn) -> str:
    """Validate a string setting, falling back to its default."""
    if not isinstance(value, str) or not value.strip():
        warn(
            f"'{name}' must be a non-empty string, "
            f"got {_json_type_name(value)}, using default {default!r}"
        )
        return default

    return value


def _json_type_name(value: Any) -> str:
    """Return the JSON name of a value's type."""
    names: dict[type, str] = {
        str: "a string",
        bool: "a boolean",
        int: "an integer",
        float: "a number",
        list: "an array",
        dict: "an object",
        type(None): "null",
    }

    return names.get(type(value), type(value).__name__)
