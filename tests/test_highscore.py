"""The highscore table survives anything found on disk."""

from pathlib import Path

from pacman.model.highscore import (
    MAX_ENTRIES,
    HighscoreTable,
    sanitize_name,
)


def test_names_are_sanitized() -> None:
    """Only alphanumerics and spaces, ten characters at most."""
    assert sanitize_name("Jean-Mi!") == "JeanMi"
    assert sanitize_name("a very long player name") == "a very lon"
    assert sanitize_name("***") == "PLAYER"


def test_missing_file_starts_empty(tmp_path: Path) -> None:
    """A first run has no file and no scores, and does not fail."""
    table = HighscoreTable(tmp_path / "highscores.json")
    table.load()

    assert table.scores == []


def test_broken_file_starts_empty(tmp_path: Path) -> None:
    """Invalid JSON is reported and ignored."""
    path = tmp_path / "highscores.json"
    path.write_text("not json at all", encoding="utf-8")

    table = HighscoreTable(path)
    table.load()

    assert table.scores == []


def test_invalid_entries_are_dropped(tmp_path: Path) -> None:
    """Entries with the wrong shape never reach the table."""
    path = tmp_path / "highscores.json"
    path.write_text(
        '[{"name": "ok", "points": 10}, {"name": 1, "points": 2}, '
        '{"name": "neg", "points": -5}, "garbage"]',
        encoding="utf-8",
    )

    table = HighscoreTable(path)
    table.load()

    assert [score.name for score in table.scores] == ["ok"]


def test_only_the_ten_best_are_kept(tmp_path: Path) -> None:
    """Adding scores keeps the table sorted and capped."""
    table = HighscoreTable(tmp_path / "highscores.json")
    table.load()

    for points in range(20):
        table.add(f"p{points}", points)

    assert len(table.scores) == MAX_ENTRIES
    assert table.scores[0].points == 19
    assert table.scores[-1].points == 10


def test_scores_are_persisted(tmp_path: Path) -> None:
    """What is written can be read back by another table."""
    path = tmp_path / "highscores.json"
    HighscoreTable(path).add("Foliole", 4200)

    reloaded = HighscoreTable(path)
    reloaded.load()

    assert reloaded.as_tuples() == (("Foliole", 4200),)
