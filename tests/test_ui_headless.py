"""Headless integration tests for SoulwaveApp using Textual pilot."""

import pytest
from soulwave.config import Config
from soulwave.player.base import PlaybackStatus
from soulwave.ui.app import SoulwaveApp


@pytest.mark.asyncio
async def test_app_headless_lifecycle():
    cfg = Config(theme="sunset", fps=15)
    app = SoulwaveApp(config=cfg, force_demo=True)

    async with app.run_test(size=(100, 30)) as pilot:
        # Check that widgets mounted
        assert app.mascot_view is not None
        assert app.now_playing_view is not None
        assert app.progress_bar_view is not None
        assert app.controls_view is not None
        assert app.lyrics_view is not None
        assert app.companion_view is not None

        # Give the app a couple of ticks
        await pilot.pause(0.2)

        # Initial playback state in demo should be PLAYING
        assert app._last_state.status == PlaybackStatus.PLAYING

        # Test toggling 'l' to hide lyrics and show companion dance view
        assert app.config.show_lyrics is True
        assert app.lyrics_view.display is True
        assert app.companion_view.display is False

        await pilot.press("l")
        await pilot.pause(0.1)
        assert app.config.show_lyrics is False
        assert app.lyrics_view.display is False
        assert app.companion_view.display is True
        c_text = app.companion_view.render().plain
        assert "Pip" in c_text
        assert "Nova" in c_text
        assert "Mochi" in c_text

        # Toggle 'l' back to restore lyrics view
        await pilot.press("l")
        await pilot.pause(0.1)
        assert app.config.show_lyrics is True
        assert app.lyrics_view.display is True
        assert app.companion_view.display is False

        # Press space to pause
        await pilot.press("space")
        await pilot.pause(0.1)
        assert app._last_state.status == PlaybackStatus.PAUSED

        # Press space to resume
        await pilot.press("space")
        await pilot.pause(0.1)
        assert app._last_state.status == PlaybackStatus.PLAYING

        # Press 'n' for next track
        t1 = app._last_state.metadata.title
        await pilot.press("n")
        await pilot.pause(0.1)
        t2 = app._last_state.metadata.title
        assert t1 != t2

        # Press 'p' for previous track
        await pilot.press("p")
        await pilot.pause(0.1)
        t3 = app._last_state.metadata.title
        assert t3 == t1

        # Press 'm' to toggle mini mode
        assert not app.config.mini_mode
        await pilot.press("m")
        await pilot.pause(0.1)
        assert app.config.mini_mode
        assert app.screen.has_class("mini-mode")

        # Press 't' to cycle theme
        theme1 = app.active_theme_name
        await pilot.press("t")
        await pilot.pause(0.1)
        assert app.active_theme_name != theme1

        # Press 'h' to open help modal
        await pilot.press("h")
        await pilot.pause(0.1)
        from soulwave.ui.app import HelpModal
        assert isinstance(app.screen, HelpModal)

        # Press 'h' again to close help modal
        await pilot.press("h")
        await pilot.pause(0.1)
        assert not isinstance(app.screen, HelpModal)

        # Press 'h' then 'escape' to close
        await pilot.press("h")
        await pilot.pause(0.1)
        assert isinstance(app.screen, HelpModal)
        await pilot.press("escape")
        await pilot.pause(0.1)
        assert not isinstance(app.screen, HelpModal)

        # Press 'q' to quit
        await pilot.press("q")


@pytest.mark.asyncio
async def test_lyrics_update_after_mascot_dance_and_track_change():
    """Verify that toggling to mascot dance, changing track, and toggling back to lyrics updates to the new track's lyrics."""
    cfg = Config(theme="sunset", fps=15)
    app = SoulwaveApp(config=cfg, force_demo=True)

    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause(0.2)
        # Verify initial track 0 is Midnight Coffee with its lyrics loaded
        assert app._last_state.metadata.title == "Midnight Coffee"
        assert len(app.lyrics_view.lines) > 0
        assert "Soft glow" in app.lyrics_view.lines[0].text

        # 1. Switch to mascot companion dance ('l')
        await pilot.press("l")
        await pilot.pause(0.1)
        assert app.config.show_lyrics is False
        assert app.companion_view.display is True
        assert app.lyrics_view.display is False

        # 2. Change song to next track ('n') while in mascot dance
        await pilot.press("n")
        await pilot.pause(0.2)
        assert app._last_state.metadata.title == "Synthwave Sunset"

        # 3. Switch back to lyrics ('l')
        await pilot.press("l")
        await pilot.pause(0.2)
        assert app.config.show_lyrics is True
        assert app.lyrics_view.display is True

        # Check that lyrics are updated to Synthwave Sunset, NOT the old Midnight Coffee!
        assert len(app.lyrics_view.lines) > 0
        assert "Driving down" in app.lyrics_view.lines[0].text
        assert "Soft glow" not in app.lyrics_view.lines[0].text
