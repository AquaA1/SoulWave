"""Comprehensive regression tests for Soulwave lyrics timing, fallback, completeness, and no-replay logic."""

import time
import pytest
from unittest.mock import MagicMock, patch

from soulwave.lyrics.parser import LRCParser, LyricLine
from soulwave.lyrics.client import LyricsClient
from soulwave.lyrics.cache import LyricsCache
from soulwave.player.base import PlayerState, PlaybackStatus, TrackMetadata
from soulwave.player.interpolator import PositionInterpolator
from soulwave.ui.widgets.progress_bar import ProgressBarView
from soulwave.ui.widgets.lyrics_panel import LyricsPanelView
from soulwave.ui.app import SoulwaveApp
from soulwave.config import Config


# ---------------------------------------------------------------------------
# Scenario 1: Valid duration + synced lyrics -> timeline & duration display work
# ---------------------------------------------------------------------------
def test_scenario_1_valid_duration_and_synced_lyrics():
    pbar = ProgressBarView()
    pbar.update_progress(position=45.0, duration=180.0, accent=(56, 189, 248))
    rendered = pbar.render().plain

    assert "00:45" in rendered
    assert "03:00" in rendered
    assert "--:--" not in rendered

    panel = LyricsPanelView()
    lrc = "[00:10.00] First Line\n[00:40.00] Second Line\n[01:10.00] Third Line"
    panel.set_lyrics(lrc, None, duration=180.0)
    panel.update_position(45.0, (56, 189, 248), duration=180.0)

    panel_rendered = panel.render().plain
    assert "SYNCED LYRICS" in panel_rendered
    assert "▸ Second Line" in panel_rendered


# ---------------------------------------------------------------------------
# Scenario 2: Valid duration + plain lyrics -> timeline shows duration, not --:--
# ---------------------------------------------------------------------------
def test_scenario_2_valid_duration_and_plain_lyrics_no_dash_bug():
    pbar = ProgressBarView()
    # Even when lyrics are plain/unsynchronized, timeline must display 03:20 instead of --:--
    pbar.update_progress(position=50.0, duration=200.0, accent=(56, 189, 248))
    rendered = pbar.render().plain

    assert "00:50" in rendered
    assert "03:20" in rendered
    assert "--:--" not in rendered

    panel = LyricsPanelView()
    plain = "Verse 1 line\nVerse 2 line\nChorus line"
    panel.set_lyrics(None, plain, duration=200.0)
    panel.update_position(50.0, (56, 189, 248), duration=200.0)

    panel_rendered = panel.render().plain
    assert "PLAIN LYRICS (UNSYNCHRONIZED)" in panel_rendered
    # Lyrics panel preserves duration_seconds
    assert panel.duration_seconds == 200.0


# ---------------------------------------------------------------------------
# Scenario 3: Lyrics request fails while track duration remains valid
# ---------------------------------------------------------------------------
def test_scenario_3_lyrics_request_fails_preserves_duration():
    pbar = ProgressBarView()
    panel = LyricsPanelView()

    # Track has duration 210s
    track_dur = 210.0
    pbar.update_progress(position=15.0, duration=track_dur, accent=(56, 189, 248))
    assert "03:30" in pbar.render().plain

    # Lyrics request fails (returns None)
    panel.set_lyrics(None, None, duration=track_dur)

    # Duration must NOT be wiped out
    assert panel.duration_seconds == track_dur
    pbar.update_progress(position=20.0, duration=track_dur, accent=(56, 189, 248))
    assert "03:30" in pbar.render().plain
    assert "--:--" not in pbar.render().plain


# ---------------------------------------------------------------------------
# Scenario 4: No lyrics found -> friendly message, 5s countdown, dance fallback
# ---------------------------------------------------------------------------
def test_scenario_4_no_lyrics_countdown_and_dance_fallback():
    panel = LyricsPanelView()
    completed = []

    def on_complete():
        completed.append(True)

    panel.start_no_lyrics_countdown(on_complete=on_complete, countdown_seconds=5)
    assert panel.is_countdown_active is True

    # Initial render shows message and 5-second countdown
    render_init = panel.render().plain
    assert "No lyrics found for this track ♡" in render_init
    assert "Take a little break and enjoy a dance with our Soul Souls!" in render_init
    assert "The Soul Souls are getting ready to dance... 5" in render_init

    # Fast forward countdown by adjusting start time: 3 seconds elapsed (2 remaining)
    panel._countdown_start_time = time.monotonic() - 3.1
    panel.update_position(10.0, (56, 189, 248))
    render_3s = panel.render().plain
    assert "The Soul Souls are getting ready to dance... 2" in render_3s
    assert len(completed) == 0

    # 5.1 seconds elapsed -> countdown triggers completion and switches to mascot dance
    panel._countdown_start_time = time.monotonic() - 5.1
    panel.update_position(10.0, (56, 189, 248))
    assert panel.is_countdown_active is False
    assert panel._dance_fallback_active is True
    assert len(completed) == 1

    # Render now contains the dancing mascots
    render_dance = panel.render().plain
    assert "Pip" in render_dance
    assert "Nova" in render_dance
    assert "Mochi" in render_dance


# ---------------------------------------------------------------------------
# Scenario 5: Lyrics arrive during countdown -> countdown cancelled, lyrics shown
# ---------------------------------------------------------------------------
def test_scenario_5_lyrics_arrive_during_countdown_cancels_it():
    panel = LyricsPanelView()
    completed = []

    panel.start_no_lyrics_countdown(on_complete=lambda: completed.append(True))
    assert panel.is_countdown_active is True

    # Lyrics arrive while countdown is at 4s
    lrc = "[00:05.00] Sun goes down\n[00:15.00] Stars appear"
    panel.set_lyrics(lrc, None, duration=120.0)

    # Countdown must be cancelled immediately
    assert panel.is_countdown_active is False
    assert panel._dance_fallback_active is False
    assert len(completed) == 0

    rendered = panel.render().plain
    assert "SYNCED LYRICS" in rendered
    assert "Sun goes down" in rendered
    assert "The Soul Souls are getting ready to dance" not in rendered


# ---------------------------------------------------------------------------
# Scenario 6: New track starts during countdown -> previous countdown cancelled
# ---------------------------------------------------------------------------
def test_scenario_6_new_track_cancels_previous_countdown():
    panel = LyricsPanelView()
    track1_completed = []

    panel.start_no_lyrics_countdown(on_complete=lambda: track1_completed.append("track1"))
    assert panel.is_countdown_active is True

    # New track starts loading
    panel.set_loading()
    assert panel.is_countdown_active is False
    assert panel._dance_fallback_active is False

    # Simulate time passing past original 5s
    panel.update_position(5.0, (56, 189, 248))
    assert len(track1_completed) == 0
    assert "Looking up lyrics" in panel.render().plain


# ---------------------------------------------------------------------------
# Scenario 7: Plain lyrics scroll progressively, pause, seek, never loop
# ---------------------------------------------------------------------------
def test_scenario_7_plain_lyrics_scrolling_pausing_seeking_no_loop():
    panel = LyricsPanelView()
    plain = """Verse 1: Starting line
Verse 2: Middle line
Verse 3: Climax line
Verse 4: Outro line"""
    duration = 100.0
    panel.set_lyrics(None, plain, duration=duration)

    # t = 0s -> Starting line
    panel.update_position(0.0, (56, 189, 248), duration=duration)
    assert "▸ Verse 1: Starting line" in panel.render().plain

    # t = 50s -> Middle line
    panel.update_position(50.0, (56, 189, 248), duration=duration)
    assert "▸ Verse 2: Middle line" in panel.render().plain or "▸ Verse 3: Climax line" in panel.render().plain

    # Paused at 50s -> remains at same line
    panel.update_position(50.0, (56, 189, 248), duration=duration)
    assert "Verse 1: Starting line" not in panel.render().plain.split("▸")[1].splitlines()[0]

    # Seeking forward to 95s -> Outro line
    panel.update_position(95.0, (56, 189, 248), duration=duration)
    assert "▸ Verse 4: Outro line" in panel.render().plain

    # Song continues playing past duration (e.g. 105s, 120s) -> MUST NEVER loop back to Verse 1!
    panel.update_position(105.0, (56, 189, 248), duration=duration)
    assert "▸ Verse 4: Outro line" in panel.render().plain
    assert "▸ Verse 1" not in panel.render().plain

    panel.update_position(120.0, (56, 189, 248), duration=duration)
    assert "▸ Verse 4: Outro line" in panel.render().plain
    assert "▸ Verse 1" not in panel.render().plain

    # Seeking backward to 10s un-freezes and navigates back to Verse 1
    panel.update_position(10.0, (56, 189, 248), duration=duration)
    assert "▸ Verse 1: Starting line" in panel.render().plain


# ---------------------------------------------------------------------------
# Scenario 8: Synced lyrics never restart after final timestamp while playing
# ---------------------------------------------------------------------------
def test_scenario_8_synced_lyrics_never_restart_after_final_timestamp():
    panel = LyricsPanelView()
    lrc = """[00:10.00] First Verse
[00:30.00] Chorus
[00:60.00] Final Outro Line"""
    duration = 180.0  # 3-minute track with vocals ending at 60s
    panel.set_lyrics(lrc, None, duration=duration)

    # At 65s (past last timestamp 60s)
    panel.update_position(65.0, (56, 189, 248), duration=duration)
    assert "▸ Final Outro Line" in panel.render().plain

    # During long instrumental outro at 90s, 120s, 170s:
    # Must remain on final line, NEVER loop back to First Verse
    panel.update_position(90.0, (56, 189, 248), duration=duration)
    assert "▸ Final Outro Line" in panel.render().plain
    assert "▸ First Verse" not in panel.render().plain

    panel.update_position(150.0, (56, 189, 248), duration=duration)
    assert "▸ Final Outro Line" in panel.render().plain
    assert "▸ First Verse" not in panel.render().plain


# ---------------------------------------------------------------------------
# Scenario 9: Legitimate early-ending vocal track is not classified as incomplete
# ---------------------------------------------------------------------------
def test_scenario_9_early_ending_vocal_track_not_classified_incomplete():
    client = LyricsClient()

    # Track duration = 200s, 12 lines of vocals ending at 110s (55% coverage) + 90s outro
    legitimate_lrc = """[00:10.00] Line 1
[00:20.00] Line 2
[00:30.00] Line 3
[00:40.00] Line 4
[00:50.00] Line 5
[00:60.00] Line 6
[00:70.00] Line 7
[00:80.00] Line 8
[00:90.00] Line 9
[01:00.00] Line 10
[01:05.00] Line 11
[01:10.00] Line 12 outro vocals"""
    assert client._is_suspiciously_incomplete(legitimate_lrc, duration=200.0) is False

    # In contrast: a 200s track with only 2 lines ending at 15s is suspiciously incomplete
    truncated_lrc = """[00:05.00] Intro snippet line
[00:15.00] Second snippet line"""
    assert client._is_suspiciously_incomplete(truncated_lrc, duration=200.0) is True


# ---------------------------------------------------------------------------
# Scenario 10: Repeated chorus lines remain intact without deduplication
# ---------------------------------------------------------------------------
def test_scenario_10_repeated_chorus_lines_intact():
    raw_lrc = """[00:15.00] Singing the chorus
[00:25.00] Singing the chorus
[00:40.00] Verse line
[00:55.00] Singing the chorus
[01:05.00] Singing the chorus"""
    lines = LRCParser.parse(raw_lrc)
    assert len(lines) == 5
    assert lines[0].text == "Singing the chorus"
    assert lines[1].text == "Singing the chorus"
    assert lines[3].text == "Singing the chorus"
    assert lines[4].text == "Singing the chorus"
    assert lines[1].timestamp == 25.0
    assert lines[4].timestamp == 65.0


# ---------------------------------------------------------------------------
# Scenario 11: Rapid track changes do not cause stale lyrics, wrong durations or crashes
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_11_rapid_track_changes_headless():
    app = SoulwaveApp(force_demo=True)
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause(0.2)

        # Track 1
        initial_track = app.current_track_key
        assert app.progress_bar_view.duration > 0.0

        # Rapidly press next track multiple times with sufficient time for Textual pilot processing
        await pilot.press("n")
        await pilot.pause(0.1)
        await pilot.press("n")
        await pilot.pause(0.1)
        await pilot.press("n")
        await pilot.pause(0.2)

        # Progress bar duration must remain positive and valid (not --:--)
        dur = app.progress_bar_view.duration
        assert dur > 0.0
        assert "--:--" not in app.progress_bar_view.render().plain
