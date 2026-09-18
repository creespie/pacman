"""The loader must never crash on a broken configuration file."""

import json
from pathlib import Path

import pytest

from pacman.config import Config, ConfigError, load_config


def write(tmp_path: Path, text: str) -> Path:
    """Write a configuration file and return its path."""
    path = tmp_path / "config.json"
    path.write_text(text, encoding="utf-8")

    return path


def test_comments_are_ignored(tmp_path: Path) -> None:
    """Both # and // comments are stripped before parsing."""
    path = write(
        tmp_path,
        '# a comment\n{\n"lives": 5, // another\n"seed": 7 # trailing\n}\n',
    )

    config = load_config(path, warn=lambda _message: None)

    assert config.lives == 5
    assert config.seed == 7


def test_hash_inside_a_string_is_kept(tmp_path: Path) -> None:
    """A # inside a JSON string is data, not a comment."""
    path = write(tmp_path, '{"highscore_filename": "sc#ores.json"}')

    config = load_config(path, warn=lambda _message: None)

    assert config.highscore_filename == "sc#ores.json"


def test_missing_keys_fall_back_to_defaults(tmp_path: Path) -> None:
    """A missing key is replaced by its default and reported."""
    messages: list[str] = []
    path = write(tmp_path, "{}")

    config = load_config(path, warn=messages.append)

    assert config == Config()
    assert len(messages) == len(vars(Config()))


def test_invalid_values_are_clamped(tmp_path: Path) -> None:
    """Out of range and wrongly typed values never reach the game."""
    messages: list[str] = []
    path = write(
        tmp_path,
        json.dumps({"lives": -3, "level_max_time": "soon", "width": 10**9}),
    )

    config = load_config(path, warn=messages.append)

    assert config.lives == 1
    assert config.level_max_time == Config().level_max_time
    assert config.width == 101
    assert any("lives" in message for message in messages)


def test_unknown_keys_are_ignored(tmp_path: Path) -> None:
    """An unknown key is reported but does not stop the game."""
    messages: list[str] = []
    path = write(tmp_path, json.dumps({"ghosts_are_friendly": True}))

    load_config(path, warn=messages.append)

    assert any("ghosts_are_friendly" in message for message in messages)


def test_missing_file_raises_a_clean_error(tmp_path: Path) -> None:
    """A missing file is reported as a ConfigError, not an OSError."""
    with pytest.raises(ConfigError, match="file not found"):
        load_config(tmp_path / "nope.json")


def test_broken_json_raises_a_clean_error(tmp_path: Path) -> None:
    """A syntax error is reported with its position."""
    path = write(tmp_path, "{ lives: 3 }")

    with pytest.raises(ConfigError):
        load_config(path)
