# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification file for building standalone SoulWave Linux executables.

Collects Textual, Rich, and internal assets (soulwave/ui/styles.tcss) into a
single standalone ELF binary.
"""

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files

SPEC_DIR = Path(SPEC).resolve().parent
REPO_ROOT = SPEC_DIR.parent.parent

datas = [
    (str(REPO_ROOT / "soulwave" / "ui" / "styles.tcss"), "soulwave/ui"),
]

# Collect all data, binaries, and hidden imports for Textual and Rich
textual_datas, textual_binaries, textual_hiddenimports = collect_all("textual")
rich_datas, rich_binaries, rich_hiddenimports = collect_all("rich")

datas += textual_datas + rich_datas
binaries = textual_binaries + rich_binaries
hiddenimports = textual_hiddenimports + rich_hiddenimports + [
    "soulwave",
    "soulwave.cli",
    "soulwave.config",
    "soulwave.ui",
    "soulwave.ui.app",
    "soulwave.player",
    "soulwave.player.base",
    "soulwave.player.manager",
    "soulwave.player.mpris",
    "soulwave.player.mock_player",
    "soulwave.player.interpolator",
    "soulwave.audio",
    "soulwave.audio.cava_reader",
    "soulwave.audio.visualizer",
    "soulwave.lyrics",
    "soulwave.lyrics.client",
    "soulwave.lyrics.cache",
    "soulwave.lyrics.parser",
    "soulwave.mascot",
    "soulwave.mascot.animator",
    "soulwave.mascot.frames",
    "soulwave.mascot.scene",
    "soulwave.mascot.sprite",
    "soulwave.theme",
    "soulwave.theme.dynamic",
    "soulwave.theme.palettes",
    "requests",
    "syncedlyrics",
]

block_cipher = None

a = Analysis(
    [str(REPO_ROOT / "soulwave" / "cli.py")],
    pathex=[str(REPO_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "PySide6", "PyQt5", "PyQt6", "matplotlib"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="soulwave",
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
