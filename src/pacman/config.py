"""Loading and validation of the game configuration file."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, get_type_hints


class ConfigError(Exception):
    """Raised when the configuration file cannot be read or is invalid."""


@dataclass(frozen=True)
class Config:
    """Game settings loaded from ``config.json``."""

    highscore_filename: str
    levels: int
    width: int
    height: int
    lives: int
    pacgum: int
    points_per_pacgum: int
    points_per_super_pacgum: int
    points_per_ghost: int
    seed: int
    level_max_time: int


# Minimum allowed value for each integer setting.
_MINIMUMS: dict[str, int] = {
    "levels": 1,
    "width": 1,
    "height": 1,
    "lives": 1,
    "pacgum": 1,
    "points_per_pacgum": 0,
    "points_per_super_pacgum": 0,
    "points_per_ghost": 0,
    "seed": 0,
    "level_max_time": 1,
}

# JSON names of the Python types produced by ``json.loads``.
_JSON_TYPE_NAMES: dict[type, str] = {
    str: "a string",
    int: "an integer",
    float: "a number",
    bool: "a boolean",
    list: "an array",
    dict: "an object",
    type(None): "null",
}


def load_config(path: str | Path = "config.json") -> Config:
    """Read, parse and validate the configuration file at ``path``.

    Everything after a ``#`` that is outside of a JSON string is treated
    as a comment and ignored.

    Raises:
        ConfigError: if the file cannot be read, is not valid JSON, or
            contains missing, unknown or invalid settings.
    """
    path = Path(path)

    text = _read_text(path)
    data = _parse_json(path, _strip_comments(text))

    return _build_config(path, data)


def _read_text(path: Path) -> str:
    """Return the file content, converting I/O errors into ConfigError."""
    try:
        return path.read_text(encoding="utf-8")
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
    """Remove ``#`` comments outside of JSON strings, keeping line numbers."""
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
            elif char == "#" and not in_string:
                line = line[:index]
                break

        lines.append(line)

    return "\n".join(lines)


def _parse_json(path: Path, text: str) -> Any:
    """Parse JSON text, converting syntax errors into ConfigError."""
    if not text.strip():
        raise ConfigError(
            f"{path}: no content (file is empty or contains only comments)"
        )

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}

        for key, value in pairs:
            if key in result:
                raise ConfigError(f"{path}: duplicate key '{key}'")
            result[key] = value

        return result

    try:
        return json.loads(text, object_pairs_hook=reject_duplicate_keys)
    except json.JSONDecodeError as error:
        raise ConfigError(
            f"{path}:{error.lineno}:{error.colno}: {error.msg}"
        ) from None


def _build_config(path: Path, data: Any) -> Config:
    """Validate the parsed JSON and build a Config, reporting every error."""
    if not isinstance(data, dict):
        raise ConfigError(
            f"{path}: top-level value must be an object, "
            f"got {_json_type_name(data)}"
        )

    expected_types = get_type_hints(Config)
    errors: list[str] = []

    for name, expected_type in expected_types.items():
        if name not in data:
            errors.append(f"missing key '{name}'")
            continue

        error = _validate_value(name, data[name], expected_type)

        if error is not None:
            errors.append(error)

    errors.extend(
        f"unknown key '{key}'" for key in data if key not in expected_types
    )

    if errors:
        details = "\n".join(f"  - {error}" for error in errors)
        raise ConfigError(f"{path}: invalid configuration:\n{details}")

    return Config(**data)


def _validate_value(name: str, value: Any, expected_type: type) -> str | None:
    """Return an error message if ``value`` is invalid, else ``None``."""
    # bool is a subclass of int, so it has to be rejected explicitly.
    if isinstance(value, bool) or not isinstance(value, expected_type):
        return (
            f"'{name}' must be {_JSON_TYPE_NAMES[expected_type]}, "
            f"got {_json_type_name(value)}"
        )

    if isinstance(value, str):
        if not value.strip():
            return f"'{name}' must not be empty"

    elif isinstance(value, int):
        minimum = _MINIMUMS.get(name)

        if minimum is not None and value < minimum:
            return f"'{name}' must be at least {minimum}, got {value}"

    return None


def _json_type_name(value: Any) -> str:
    """Return the JSON name of a value's type."""
    return _JSON_TYPE_NAMES.get(type(value), type(value).__name__)
