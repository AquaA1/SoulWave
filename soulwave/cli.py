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

    # 1b. Check MPRIS utility availability
    try:
        from soulwave.player.mpris import is_mpris_available, get_playerctl_install_hint
        if not is_mpris_available():
            hint = get_playerctl_install_hint()
            print(f"ℹ Notice: 'playerctl' not detected. Live desktop music tracking will be inactive until installed ({hint}).")
    except Exception:
        pass

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
def run_doctor() -> int:
    """Comprehensive system and runtime diagnostic report for Soulwave."""
    import os
    import platform
    import shutil
    import subprocess

    is_frozen = getattr(sys, "frozen", False)
    mode_str = "Standalone Binary (PyInstaller)" if is_frozen else "Python Package / Virtual Environment"
    
    print("=" * 65)
    print(f"  🩺 Soulwave Doctor — Diagnostic Report (v{__version__})")
    print("=" * 65)
    print()

    # 1. Environment & Architecture
    print(" [1] System Environment")
    print(f"     • OS Platform:    {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"     • Python Version: {platform.python_version()} ({platform.python_implementation()})")
    print(f"     • Install Mode:   {mode_str}")
    print(f"     • Executable:     {sys.executable}")
    print()

    # 2. Core Runtime & UI Resources
    print(" [2] Core Runtime & UI Resources")
    missing_core = []
    for mod_name in ["textual", "rich", "requests", "syncedlyrics"]:
        try:
            mod = __import__(mod_name)
            ver = "installed"
            try:
                import importlib.metadata as md
                ver = f"v{md.version(mod_name)}"
            except Exception:
                ver = f"v{getattr(mod, '__version__', 'available')}"
            print(f"     • {mod_name:<15} [  OK  ] ({ver})")
        except ImportError:
            missing_core.append(mod_name)
            print(f"     • {mod_name:<15} [FAILED] (not installed)")

    # Stylesheet check
    css_ok = False
    try:
        import importlib.resources as pkg_resources
        candidate = Path(str(pkg_resources.files("soulwave.ui").joinpath("styles.tcss")))
        if candidate.is_file() and candidate.stat().st_size > 0:
            css_ok = True
    except Exception:
        pass
    if not css_ok:
        fallback_css = Path(__file__).resolve().parent / "ui" / "styles.tcss"
        if fallback_css.is_file() and fallback_css.stat().st_size > 0:
            css_ok = True

    if css_ok:
        print(f"     • {'styles.tcss':<15} [  OK  ] (UI stylesheet found)")
    else:
        missing_core.append("styles.tcss")
        print(f"     • {'styles.tcss':<15} [FAILED] (UI stylesheet missing or empty)")
    print()

    # 3. D-Bus & Desktop Audio Session
    print(" [3] D-Bus & MPRIS Subsystem")
    dbus_addr = os.environ.get("DBUS_SESSION_BUS_ADDRESS", "")
    if dbus_addr:
        print(f"     • Session Bus:    [  OK  ] ({dbus_addr[:36]}...)")
    else:
        print("     • Session Bus:    [NOTICE] ($DBUS_SESSION_BUS_ADDRESS not set; headless or non-desktop environment)")

    try:
        from soulwave.player.mpris import _DBUS_AVAILABLE
        if _DBUS_AVAILABLE:
            print("     • D-Bus Bindings: [  OK  ] (python-dbus & GLib available)")
        else:
            print("     • D-Bus Bindings: [NOTICE] (python-dbus not loaded; relying on playerctl)")
    except Exception:
        print("     • D-Bus Bindings: [NOTICE] (D-Bus module check failed)")

    playerctl_path = shutil.which("playerctl")
    if playerctl_path:
        ver_str = "available"
        try:
            res = subprocess.run([playerctl_path, "--version"], capture_output=True, text=True, timeout=2)
            if res.returncode == 0:
                ver_str = res.stdout.strip().splitlines()[0]
        except Exception:
            pass
        print(f"     • playerctl CLI:  [  OK  ] ({playerctl_path}, {ver_str})")
    else:
        print("     • playerctl CLI:  [MISSING] (recommended for live Spotify/browser media tracking)")

    # Active MPRIS player probe
    detected_players = []
    try:
        from soulwave.player.mpris import MPRISPlayer
        detected_players = MPRISPlayer.list_players()
    except Exception:
        pass

    if detected_players:
        print(f"     • Active Players: [  OK  ] Detected: {', '.join(detected_players)}")
    else:
        print("     • Active Players: [NOTICE] No active media players found (play music in Spotify/browser, or use 'soulwave -d')")
    print()

    # 4. Audio Visualizer & Sound Server
    print(" [4] Audio Visualizer & Sound Server")
    cava_path = shutil.which("cava")
    if cava_path:
        print(f"     • cava utility:   [  OK  ] ({cava_path} — real-time audio spectrum enabled)")
    else:
        print("     • cava utility:   [OPTIONAL] (not found; Soulwave will use built-in procedural visualizer)")

    # Audio server check
    sound_server = "unknown"
    if shutil.which("pipewire") or shutil.which("pw-cli") or shutil.which("wpctl"):
        sound_server = "PipeWire"
    elif shutil.which("pulseaudio") or shutil.which("pactl"):
        sound_server = "PulseAudio"
    elif shutil.which("sndiod"):
        sound_server = "sndio"
    print(f"     • Sound Server:   [INFO] Detected: {sound_server}")
    print()

    # 5. User Configuration & Cache
    print(" [5] User Configuration & Data Storage")
    cfg_file = Config.get_config_path()
    if cfg_file.is_file():
        print(f"     • Configuration:  [  OK  ] {cfg_file}")
    else:
        print(f"     • Configuration:  [INFO] Using default settings (file not created yet at {cfg_file})")

    cache_dir = Path.home() / ".cache" / "soulwave" / "lyrics"
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        test_file = cache_dir / ".doctor_probe"
        test_file.touch()
        test_file.unlink()
        print(f"     • Lyrics Cache:   [  OK  ] {cache_dir} (writable)")
    except Exception as e:
        print(f"     • Lyrics Cache:   [WARNING] {cache_dir} (failed write test: {e})")
    print()

    # Verdict
    print("=" * 65)
    if missing_core:
        print(f"  ❌ FAILED: Missing essential runtime components: {', '.join(missing_core)}")
        print("     Please reinstall Soulwave using the official installer.")
        return 1

    if not playerctl_path:
        from soulwave.player.mpris import get_playerctl_install_hint
        hint = get_playerctl_install_hint()
        print("  ℹ RECOMMENDATION: Install 'playerctl' to enable live desktop music tracking:")
        print(f"     {hint}")
    else:
        print("  ✓ SYSTEM STATUS: Soulwave is healthy and ready to rock!")
    print("=" * 65)
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
        "--doctor",
        action="store_true",
        help="Run comprehensive system and runtime diagnostic report",
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

    if args.doctor:
        sys.exit(run_doctor())

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

