"""Command-line interface entry point for Soulwave."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .config import Config
from .ui.app import SoulwaveApp


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="soulwave",
        description="🎧 Soulwave: A cute terminal music controller with a grooving pixel-art soul mascot",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"Soulwave v{__version__}",
    )
    parser.add_argument(
        "-d", "--demo",
        action="store_true",
        help="Run in demo mode with built-in tracks and synced lyrics (no MPRIS player needed)",
    )
    parser.add_argument(
        "-p", "--player",
        type=str,
        default="",
        help="Specify preferred MPRIS player name (e.g. spotify, firefox, chromium, mpv)",
    )
    parser.add_argument(
        "-m", "--mini",
        action="store_true",
        help="Start directly in compact mini-widget mode",
    )
    parser.add_argument(
        "-t", "--theme",
        type=str,
        default="",
        help="Color theme: night, sunset, mint, sakura, cyberpunk, mono",
    )
    parser.add_argument(
        "--no-lyrics",
        action="store_true",
        help="Disable the lyrics panel on startup",
    )
    parser.add_argument(
        "--no-vis",
        action="store_true",
        help="Disable the bottom audio visualizer",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="",
        help="Path to custom config.toml",
    )

    args = parser.parse_args()

    cfg_path = Path(args.config) if args.config else None
    config = Config.load(cfg_path)

    if args.theme:
        config.theme = args.theme
    if args.no_lyrics:
        config.show_lyrics = False
    if args.no_vis:
        config.show_visualizer = False

    app = SoulwaveApp(
        config=config,
        force_demo=args.demo,
        start_mini=args.mini,
        preferred_player=args.player,
    )
    app.run()


if __name__ == "__main__":
    main()
