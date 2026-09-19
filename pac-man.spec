# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification: one self-contained folder to publish.

Build it on the machine (and the distribution) you ship for, because the
MiniLibX shared object and the X11 libraries it links against are
platform specific:

    make package        # -> dist/pac-man/

The result is the folder to zip and upload to itch.io as a Linux build.
The game is started with ``./pac-man config.json``; ``config.json`` is
shipped next to the executable so that players can edit it.
"""

from pathlib import Path

import mlx

MLX_DIR = Path(mlx.__file__).resolve().parent

block_cipher = None

a = Analysis(
    ["pac-man.py"],
    pathex=["src"],
    binaries=[(str(MLX_DIR / "libmlx.so"), "mlx")],
    datas=[("config.json", "."), ("README.md", ".")],
    hiddenimports=["mazegenerator", "mlx"],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="pac-man",
    debug=False,
    strip=False,
    upx=False,
    console=True,
    # PyInstaller 6 hides everything in a "_internal" sub-folder by
    # default, config.json included, which breaks the documented
    # "./pac-man config.json". Keeping the contents next to the
    # executable is what makes the shipped configuration editable by
    # the player, which the subject asks for.
    contents_directory=".",
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="pac-man",
)
