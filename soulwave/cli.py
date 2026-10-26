"""Command-line interface entry point for Soulwave."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    # Executed directly as a script without package context
    _parent = str(Path(__file__).resolve().parent.parent)
    if _parent not in sys.path:
        sys.path.insert(0, _parent)
    from soulwave import __version__
    from soulwave.config import Config
else:
    from . import __version__
    from .config import Config


def check_installation() -> int:
    """Non-interactive health check verifying all runtime dependencies and UI stylesheets."""
    print("Checking Soulwave installation...")
    # 1. Verify runtime dependencies
    try:
        import textual  # noqa: F401
        import rich  # noqa: F401
        import requests  # noqa: F401
        import syncedlyrics  # noqa: F401
    except ImportError as e:
        sys.stderr.write(f"ERROR: Missing runtime dependency: {e}\n")
        return 1

    # 2. Verify stylesheet package resource
    try:
        css_file = None
        # Try importlib.resources first
        try:
            import importlib.resources as pkg_resources
            candidate = Path(str(pkg_resources.files("soulwave.ui").joinpath("styles.tcss")))
            if candidate.is_file() and candidate.stat().st_size > 0:
                css_file = candidate
        except Exception:
            pass

        # Try relative to module file or sys._MEIPASS (PyInstaller frozen bundle)
        if css_file is None:
            meipass = getattr(sys, "_MEIPASS", None)
            search_paths = [
                Path(__file__).resolve().parent / "ui" / "styles.tcss",
            ]
            if meipass:
                search_paths.append(Path(meipass) / "soulwave" / "ui" / "styles.tcss")
            for sp in search_paths:
                if sp.is_file() and sp.stat().st_size > 0:
                    css_file = sp
                    break

        if css_file is None or not css_file.is_file():
            sys.stderr.write("ERROR: Stylesheet file styles.tcss not found\n")
            return 1
        if css_file.stat().st_size == 0:
            sys.stderr.write(f"ERROR: Stylesheet file is empty at: {css_file}\n")
            return 1
    except Exception as e:
        sys.stderr.write(f"ERROR: Failed checking stylesheet resource: {e}\n")
        return 1

    # 3. Verify Textual UI instantiation and headless mount
    try:
        import asyncio
        if __package__ is None or __package__ == "":
            from soulwave.ui.app import SoulwaveApp
        else:
            from .ui.app import SoulwaveApp

        async def _test_mount():
            cfg = Config(theme="night", fps=15)
            app = SoulwaveApp(config=cfg, force_demo=True)
            async with app.run_test(size=(80, 24)) as pilot:
                await pilot.pause(0.05)
                assert app.mascot_view is not None
                assert app.progress_bar_view is not None

        asyncio.run(_test_mount())
    except Exception as e:
        sys.stderr.write(f"ERROR: Headless UI mount verification failed: {e}\n")
        return 1

    print(f"✓ Soulwave v{__version__} health check passed (all runtime dependencies and UI stylesheets verified).")
    return 0


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
        "--check",
        action="store_true",
        help="Run non-interactive installation and resource health check",
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

    if args.check:
        sys.exit(check_installation())

    cfg_path = Path(args.config) if args.config else None
    config = Config.load(cfg_path)

    if args.theme:
        config.theme = args.theme
    if args.no_lyrics:
        config.show_lyrics = False
    if args.no_vis:
        config.show_visualizer = False

    if __package__ is None or __package__ == "":
        from soulwave.ui.app import SoulwaveApp
    else:
        from .ui.app import SoulwaveApp

    app = SoulwaveApp(
        config=config,
        force_demo=args.demo,
        start_mini=args.mini,
        preferred_player=args.player,
    )
    app.run()


if __name__ == "__main__":
    main()
