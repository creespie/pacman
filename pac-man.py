#!/usr/bin/env python3
"""Launcher required by the subject: ``python3 pac-man.py config.json``.

It only makes ``src`` importable when the project has not been installed
(``make install``), then hands over to ``pacman.__main__``.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from pacman.__main__ import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
