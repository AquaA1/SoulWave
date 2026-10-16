"""Comprehensive tests for smooth mascot dance, monotonic clock, and track transitions."""

import time
from unittest.mock import patch

from soulwave.mascot.animator import MascotAnimator, MascotState
from soulwave.mascot.frames import IDLE_F0, PAUSED_F0, SLEEP_F0
from soulwave.ui.widgets.companion_view import CompanionDanceView


def test_continuous_playing_speed_and_cycle():
    """1. A song playing continuously maintains a smooth dance speed without accelerating."""
    anim = MascotAnimator()
    anim.update_playback_state(is_playing=True, is_connected=True, has_track=True)

    fake_time = 100.0
    with patch("time.monotonic", side_effect=lambda: fake_time):
        anim._last_tick_time = fake_time
        for _ in range(50):
            fake_time += 0.08  # 12.5 fps
            anim.tick()

    assert anim.state == MascotState.PLAYING
    assert anim.speed_factor >= 0.85
    # Dance clock advanced proportionally to elapsed time
    assert anim._dance_clock > 3.0


def test_next_track_slowdown_and_settle():
    """2. Pressing N causes the mascot to slow down, settle during transition, and resume smoothly."""
    anim = MascotAnimator()
    anim.update_playback_state(is_playing=True, is_connected=True, has_track=True)
    anim.speed_factor = 1.0
    anim.amplitude_factor = 1.0

    # User presses Next (N)
    anim.begin_track_transition()
    assert anim.state == MascotState.TRACK_TRANSITION

    # Advance time while track is switching
    fake_time = 200.0
    with patch("time.monotonic", side_effect=lambda: fake_time):
        anim._last_tick_time = fake_time
        for _ in range(15):
            fake_time += 0.08
            anim.tick()

    # Mascot should have smoothly decelerated and settled
    assert anim.speed_factor < 0.15
    assert anim.amplitude_factor < 0.15
    assert anim.sway_x == 0
    assert anim.bounce_y == 0

    # When new song is confirmed playing
    anim.set_track("New Track", "New Artist")
    anim.update_playback_state(is_playing=True, is_connected=True, has_track=True)
    assert anim.state == MascotState.RESUMING

    with patch("time.monotonic", side_effect=lambda: fake_time):
        for _ in range(15):
            fake_time += 0.08
            anim.tick()

    assert anim.state == MascotState.PLAYING
    assert anim.speed_factor >= 0.85


def test_previous_track_transition():
    """3. Pressing previous-track control applies the same calm transition behavior."""
    anim = MascotAnimator()
    anim.update_playback_state(is_playing=True, is_connected=True, has_track=True)
    anim.speed_factor = 1.0

    anim.begin_track_transition()
    assert anim.state == MascotState.TRACK_TRANSITION

    fake_time = 300.0
    with patch("time.monotonic", side_effect=lambda: fake_time):
        anim._last_tick_time = fake_time
        for _ in range(10):
            fake_time += 0.08
            anim.tick()

    assert anim.speed_factor < 0.25


def test_missing_track_title_or_duration_stays_calm():
    """4. A temporary missing track title or duration does not cause acceleration."""
    anim = MascotAnimator()
    anim.begin_track_transition()

    fake_time = 400.0
    with patch("time.monotonic", side_effect=lambda: fake_time):
        anim._last_tick_time = fake_time
        for _ in range(10):
            fake_time += 0.08
            anim.tick()

    initial_speed = anim.speed_factor

    # Intermediate update with missing title / artist
    anim.set_track("", "")
    fake_time += 0.08
    with patch("time.monotonic", side_effect=lambda: fake_time):
        anim.tick()

    # Must stay calm and not accelerate
    assert anim.state == MascotState.TRACK_TRANSITION
    assert anim.speed_factor <= initial_speed + 0.05


def test_long_track_loading_delay():
    """5. A long track-loading delay keeps the mascot in a stable, calm transition state."""
    anim = MascotAnimator()
    anim.begin_track_transition()

    fake_time = 500.0
    with patch("time.monotonic", side_effect=lambda: fake_time):
        anim._last_tick_time = fake_time
        # Simulate 100 ticks (~8 seconds of loading delay)
        for _ in range(100):
            fake_time += 0.08
            anim.tick()

    assert anim.state == MascotState.TRACK_TRANSITION
    assert anim.speed_factor < 0.05
    assert anim.sway_x == 0
    assert anim.bounce_y == 0


def test_pause_and_resume():
    """6. Playback being paused and resumed settles and resumes smoothly."""
    anim = MascotAnimator()
    anim.update_playback_state(is_playing=True, is_connected=True, has_track=True)
    anim.speed_factor = 1.0

    # User pauses
    anim.update_playback_state(is_playing=False, is_connected=True, has_track=True)
    assert anim.state == MascotState.PAUSED

    fake_time = 600.0
    with patch("time.monotonic", side_effect=lambda: fake_time):
        anim._last_tick_time = fake_time
        for _ in range(15):
            fake_time += 0.08
            anim.tick()

    assert anim.speed_factor < 0.15

    # User unpauses / resumes
    anim.update_playback_state(is_playing=True, is_connected=True, has_track=True)
    assert anim.state == MascotState.PLAYING
    with patch("time.monotonic", side_effect=lambda: fake_time):
        for _ in range(15):
            fake_time += 0.08
            anim.tick()

    assert anim.speed_factor >= 0.85


def test_no_active_song_calm_idle():
    """7. When there is no active song, mascot remains in a calm idle state."""
    anim = MascotAnimator()
    anim.update_playback_state(is_playing=False, is_connected=False)
    assert anim.state == MascotState.SLEEPING

    anim.update_playback_state(is_playing=False, is_connected=True, has_track=False)
    assert anim.state == MascotState.SLEEPING

    fake_time = 700.0
    with patch("time.monotonic", side_effect=lambda: fake_time):
        anim._last_tick_time = fake_time
        for _ in range(10):
            fake_time += 0.08
            anim.tick()

    assert anim.speed_factor < 0.15


def test_rapid_consecutive_track_changes():
    """8. Rapid consecutive track changes avoid overlapping timers or sudden acceleration."""
    anim = MascotAnimator()
    anim.update_playback_state(is_playing=True, is_connected=True, has_track=True)

    fake_time = 800.0
    with patch("time.monotonic", side_effect=lambda: fake_time):
        anim._last_tick_time = fake_time
        # User rapidly presses N 5 times in quick succession
        for _ in range(5):
            anim.begin_track_transition()
            fake_time += 0.02
            anim.tick()

    assert anim.state == MascotState.TRACK_TRANSITION
    # Never accelerated
    assert anim.speed_factor <= 1.0


def test_failed_track_change_recovery():
    """9. A failed track change recovers cleanly when playback continues."""
    anim = MascotAnimator()
    anim.update_playback_state(is_playing=True, is_connected=True, has_track=True)
    anim.begin_track_transition()
    assert anim.state == MascotState.TRACK_TRANSITION

    # Next track fails, current track continues playing
    anim.update_playback_state(is_playing=True, is_connected=True, has_track=True)
    assert anim.state == MascotState.RESUMING

    fake_time = 900.0
    with patch("time.monotonic", side_effect=lambda: fake_time):
        anim._last_tick_time = fake_time
        for _ in range(15):
            fake_time += 0.08
            anim.tick()

    assert anim.state == MascotState.PLAYING


def test_companion_animations_more_visible_and_transition_settling():
    """10. Companion mascots have active individual movements and settle during transitions."""
    comp = CompanionDanceView()

    # Normal playing state
    comp.update_state(is_playing=True, is_paused=False, accent=(56, 189, 248), energy=0.5)
    rendered_play = comp.render().plain
    assert "Pip" in rendered_play
    assert "Nova" in rendered_play
    assert "Mochi" in rendered_play

    # During track transition, companions settle into calm resting state
    comp.set_track_transition(True)
    assert comp.in_track_transition is True
    rendered_transition = comp.render().plain
    assert "Resting calmly" in rendered_transition or "Pip" in rendered_transition

    # When transition ends and playback resumes
    comp.set_track_transition(False)
    assert comp.in_track_transition is False
    comp.update_state(is_playing=True, is_paused=False, accent=(56, 189, 248))
    rendered_active = comp.render().plain
    assert "Grooving with the beat" in rendered_active
