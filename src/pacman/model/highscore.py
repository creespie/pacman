"""Persistent highscore table, stored as a JSON file.

The table is deliberately dumb and defensive: any unreadable file, any
malformed entry, any name the player types is turned into something
valid instead of raising. Losing a highscore is never a reason to crash
a game.
"""

import json
from dataclasses import dataclass
from pathlib import Path

MAX_ENTRIES = 10
MAX_NAME_LENGTH = 10
DEFAULT_NAME = "PLAYER"


@dataclass(frozen=True)
class Score:
    """One line of the highscore table."""

    name: str
    points: int


def sanitize_name(name: str) -> str:
    """Return a valid player name: alphanumerics and spaces, 10 max."""
    kept = [char for char in name if char.isalnum() or char == " "]
    cleaned = "".join(kept).strip()[:MAX_NAME_LENGTH].strip()

    return cleaned or DEFAULT_NAME


class HighscoreTable:
    """Load, update and save the top ten scores."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._scores: list[Score] = []

    @property
    def path(self) -> Path:
        """Return the file the table is read from and written to."""
        return self._path

    @property
    def scores(self) -> list[Score]:
        """Return the stored scores, best first."""
        return list(self._scores)

    def as_tuples(self) -> tuple[tuple[str, int], ...]:
        """Return the scores in the primitive form used by the events."""
        return tuple((score.name, score.points) for score in self._scores)

    def load(self) -> None:
        """Read the table from disk, ignoring anything unusable."""
        self._scores = []

        try:
            with self._path.open(encoding="utf-8") as stream:
                data = json.load(stream)
        except FileNotFoundError:
            return
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
            print(f"highscores: {self._path}: {error}; starting empty")
            return

        if not isinstance(data, list):
            print(f"highscores: {self._path}: expected a list; starting empty")
            return

        self._scores = sorted(
            (score for score in map(self._parse_entry, data) if score),
            key=lambda score: score.points,
            reverse=True,
        )[:MAX_ENTRIES]

    @staticmethod
    def _parse_entry(entry: object) -> Score | None:
        """Turn one JSON entry into a Score, or None if it is broken."""
        if not isinstance(entry, dict):
            return None

        name = entry.get("name")
        points = entry.get("points")

        if not isinstance(name, str):
            return None

        if isinstance(points, bool) or not isinstance(points, int):
            return None

        if points < 0:
            return None

        return Score(sanitize_name(name), points)

    def add(self, name: str, points: int) -> Score:
        """Insert a score, keeping only the ten best, and save the file."""
        score = Score(sanitize_name(name), max(0, points))

        self._scores.append(score)
        self._scores.sort(key=lambda entry: entry.points, reverse=True)
        del self._scores[MAX_ENTRIES:]

        self.save()

        return score

    def save(self) -> None:
        """Write the table to disk, reporting but swallowing I/O errors."""
        payload = [
            {"name": score.name, "points": score.points}
            for score in self._scores
        ]

        try:
            parent = self._path.parent

            if str(parent):
                parent.mkdir(parents=True, exist_ok=True)

            with self._path.open("w", encoding="utf-8") as stream:
                json.dump(payload, stream, indent=2)
                stream.write("\n")
        except OSError as error:
            print(f"highscores: cannot save {self._path}: {error}")
