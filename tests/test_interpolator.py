"""Tests for PositionInterpolator."""

from soulwave.player.base import PlaybackStatus
from soulwave.player.interpolator import PositionInterpolator


def test_interpolator_playing():
    interp = PositionInterpolator()
    t0 = 100.0
    interp.sync(position_seconds=10.0, status=PlaybackStatus.PLAYING, duration_seconds=180.0, timestamp=t0)

    # At t0, position should be 10.0
    assert interp.get_position(now=t0) == 10.0

    # At t0 + 2.5s, position should be 12.5
    assert interp.get_position(now=t0 + 2.5) == 12.5

    # Clamping at duration
    assert interp.get_position(now=t0 + 200.0) == 180.0


def test_interpolator_paused():
    interp = PositionInterpolator()
    t0 = 100.0
    interp.sync(position_seconds=15.0, status=PlaybackStatus.PAUSED, duration_seconds=180.0, timestamp=t0)

    # Position should not advance when paused
    assert interp.get_position(now=t0 + 5.0) == 15.0


def test_interpolator_seek_immediate():
    interp = PositionInterpolator()
    interp.sync(position_seconds=10.0, status=PlaybackStatus.PLAYING, duration_seconds=180.0)
    interp.seek_immediate(45.0)
    assert abs(interp.get_position() - 45.0) < 0.1


def test_progress_ratio():
    interp = PositionInterpolator()
    interp.sync(position_seconds=50.0, status=PlaybackStatus.PAUSED, duration_seconds=100.0)
    assert interp.get_progress_ratio() == 0.5


def test_stale_zero_safeguard_rejects_repeated_zeros_during_playback():
    interp = PositionInterpolator()
    t0 = 100.0

    # Initial zero on new track with PLAYING status
    interp.reset_for_new_track(initial_position=0.0, duration=180.0, timestamp=t0, epoch=1)
    interp.sync(position_seconds=0.0, status=PlaybackStatus.PLAYING, duration_seconds=180.0, timestamp=t0, epoch=1)
    assert interp.get_position(now=t0) == 0.0

    # Advance locally to 1.2s
    t1 = t0 + 1.2
    assert abs(interp.get_position(now=t1) - 1.2) < 0.01

    # Browser sends stale 0.0 while buffering
    interp.sync(position_seconds=0.0, status=PlaybackStatus.PLAYING, duration_seconds=180.0, timestamp=t1, epoch=1)

    # Position must NOT drop back to 0.0!
    assert interp.get_position(now=t1) >= 1.2
    assert interp.diagnostics["stale_zero_count"] == 1


def test_stale_zero_recovers_when_valid_nonzero_arrives():
    interp = PositionInterpolator()
    t0 = 100.0

    interp.reset_for_new_track(initial_position=0.0, duration=180.0, timestamp=t0, epoch=1)
    interp.sync(position_seconds=0.0, status=PlaybackStatus.PLAYING, duration_seconds=180.0, timestamp=t0, epoch=1)

    # 3 stale zero reports while timeline progresses to 2.4s
    for i in range(1, 4):
        t = t0 + (i * 0.8)
        interp.sync(position_seconds=0.0, status=PlaybackStatus.PLAYING, duration_seconds=180.0, timestamp=t, epoch=1)

    assert interp.diagnostics["stale_zero_count"] == 3
    assert interp.get_position(now=t0 + 2.5) >= 2.4

    # Player finishes buffering and sends valid non-zero position 2.5s
    interp.sync(position_seconds=2.5, status=PlaybackStatus.PLAYING, duration_seconds=180.0, timestamp=t0 + 2.5, epoch=1)
    assert interp.diagnostics["stale_zero_count"] == 0
    assert abs(interp.get_position(now=t0 + 2.5) - 2.5) < 0.05


def test_explicit_seek_to_zero_is_preserved():
    interp = PositionInterpolator()
    t0 = 100.0
    interp.sync(position_seconds=45.0, status=PlaybackStatus.PLAYING, duration_seconds=180.0, timestamp=t0)

    # User explicitly seeks to 0.0
    desired = interp.start_seek(0.0)
    assert desired == 0.0
    assert interp.get_position(now=t0) == 0.0

    # Confirmation of 0.0 seek
    interp.confirm_seek(0.0)
    assert interp.get_position(now=t0) == 0.0


def test_playback_paused_near_zero_is_accepted():
    interp = PositionInterpolator()
    t0 = 100.0
    interp.reset_for_new_track(initial_position=0.0, duration=180.0, timestamp=t0, epoch=1)

    # Player paused at 0.0 must be accepted without rejection
    interp.sync(position_seconds=0.0, status=PlaybackStatus.PAUSED, duration_seconds=180.0, timestamp=t0 + 1.0, epoch=1)
    assert interp.get_position(now=t0 + 1.0) == 0.0
    assert interp.diagnostics["stale_zero_count"] == 0


def test_track_epoch_discards_stale_track_samples():
    interp = PositionInterpolator()
    t0 = 100.0

    # Track 1 at epoch 1
    interp.reset_for_new_track(initial_position=0.0, duration=180.0, timestamp=t0, epoch=1)
    interp.sync(position_seconds=120.0, status=PlaybackStatus.PLAYING, duration_seconds=180.0, timestamp=t0, epoch=1)
    assert interp.get_position(now=t0) == 120.0

    # Track changes to epoch 2
    interp.reset_for_new_track(initial_position=0.0, duration=240.0, timestamp=t0 + 1.0, epoch=2)
    assert interp.get_position(now=t0 + 1.0) == 0.0

    # Late response from track 1 (epoch 1) arrives
    interp.sync(position_seconds=125.0, status=PlaybackStatus.PLAYING, duration_seconds=180.0, timestamp=t0 + 1.1, epoch=1)

    # Must be completely ignored; track 2 stays at 0.1s
    assert abs(interp.get_position(now=t0 + 1.1) - 0.1) < 0.01


def test_extended_stale_zero_flags_uncertainty():
    interp = PositionInterpolator()
    t0 = 100.0
    interp.reset_for_new_track(initial_position=0.0, duration=180.0, timestamp=t0, epoch=1)

    # 16 consecutive stale zero reports
    for i in range(1, 18):
        t = t0 + (i * 0.8)
        interp.sync(position_seconds=0.0, status=PlaybackStatus.PLAYING, duration_seconds=180.0, timestamp=t, epoch=1)

    assert interp.is_uncertain is True


def test_continuous_playback_with_lagging_reports_60s():
    """Verify 60s of normal playback where player reports consistently lag by 0.5-2.0s.

    Asserts:
    1. Zero backward jumps across the entire 60s duration (monotonic forward progress).
    2. Estimated timeline stays within justified tolerance of real elapsed time (<= 1.5s).
    3. No periodic oscillation or rubberbanding.
    """
    interp = PositionInterpolator()
    t0 = 1000.0
    duration = 300.0
    interp.reset_for_new_track(initial_position=0.0, duration=duration, timestamp=t0, epoch=1)
    interp.sync(position_seconds=0.0, status=PlaybackStatus.PLAYING, duration_seconds=duration, timestamp=t0, epoch=1)

    lag_seconds = 1.2  # Player reports consistently lag by 1.2 seconds
    poll_interval = 0.8  # MPRIS polling every 800ms
    sim_duration = 60.0  # 60 seconds total

    t = t0
    last_displayed_pos = -0.01

    # Simulate 60 seconds of playback with fine-grained UI frames every 100ms
    while (t - t0) <= sim_duration:
        elapsed = t - t0

        # When polling occurs (every 0.8s)
        if (round(elapsed, 2) % poll_interval) < 0.05:
            # Player position lags by lag_seconds
            player_pos = max(0.0, elapsed - lag_seconds)
            interp.sync(
                position_seconds=player_pos,
                status=PlaybackStatus.PLAYING,
                duration_seconds=duration,
                timestamp=t,
                epoch=1,
            )

        # UI renders at timestamp t
        displayed_pos = interp.get_position(now=t)

        # 1. Monotonicity check: MUST NOT jump backward
        assert displayed_pos >= last_displayed_pos - 1e-6, (
            f"Backward jump detected at t={elapsed:.2f}: "
            f"displayed={displayed_pos:.3f} < previous={last_displayed_pos:.3f}"
        )
        last_displayed_pos = displayed_pos

        # Advance by 100ms
        t += 0.1

    # 2. Final position accuracy: within justified tolerance of elapsed time
    final_displayed = interp.get_position(now=t0 + sim_duration)
    assert abs(final_displayed - sim_duration) <= 1.5, (
        f"Timeline drifted too far from real elapsed time: {final_displayed} vs {sim_duration}"
    )


def test_lag_exceeding_threshold_deliberate_resynchronization():
    """Verify that lag exceeding 2.5s causes deliberate resynchronization without periodic oscillation."""
    interp = PositionInterpolator()
    t0 = 100.0
    interp.reset_for_new_track(initial_position=0.0, duration=180.0, timestamp=t0, epoch=1)
    interp.sync(position_seconds=0.0, status=PlaybackStatus.PLAYING, duration_seconds=180.0, timestamp=t0, epoch=1)

    # Advance 10s locally
    t1 = t0 + 10.0
    assert abs(interp.get_position(now=t1) - 10.0) < 0.01

    # Player stalled or buffered and is at 6.0s (lag = 10.0 - 6.0 = 4.0s > 2.5s)
    interp.sync(position_seconds=6.0, status=PlaybackStatus.PLAYING, duration_seconds=180.0, timestamp=t1, epoch=1)

    # Deliberate resync must snap to 6.0s
    resynced_pos = interp.get_position(now=t1)
    assert abs(resynced_pos - 6.0) < 0.01

    # Subsequent updates proceed smoothly from the new anchor without oscillation
    t2 = t1 + 0.8
    interp.sync(position_seconds=6.8, status=PlaybackStatus.PLAYING, duration_seconds=180.0, timestamp=t2, epoch=1)
    assert abs(interp.get_position(now=t2) - 6.8) < 0.05


def test_genuine_backward_and_forward_seeks():
    """Verify genuine backward seeks (-10s) and forward seeks (+15s) update immediately and confirm cleanly."""
    interp = PositionInterpolator()
    t0 = 100.0
    interp.sync(position_seconds=50.0, status=PlaybackStatus.PLAYING, duration_seconds=180.0, timestamp=t0)
    assert interp.get_position(now=t0) == 50.0

    # 1. Backward relative seek of -10s
    target_backward = interp.step_relative_seek(-10.0, timestamp=t0)
    assert target_backward == 40.0
    assert interp.get_position(now=t0) == 40.0  # Instant visual update

    # Player reports 40.2s within settle window -> confirms seek
    interp.sync(position_seconds=40.2, status=PlaybackStatus.PLAYING, duration_seconds=180.0, timestamp=t0 + 0.3)
    assert not interp.is_seeking()
    assert abs(interp.get_position(now=t0 + 0.3) - 40.2) < 0.01

    # 2. Forward relative seek of +15s
    t1 = t0 + 1.0
    # At t1, position has advanced from 40.2 by 0.7s -> 40.9s
    # +15s offset yields 55.9s
    target_forward = interp.step_relative_seek(15.0, timestamp=t1)
    assert abs(target_forward - 55.9) < 0.05
    # Instant visual update reflected
    assert interp.get_position(now=t1) == target_forward

    # Player reports target position -> confirms seek
    interp.sync(position_seconds=target_forward, status=PlaybackStatus.PLAYING, duration_seconds=180.0, timestamp=t1 + 0.2)
    assert not interp.is_seeking()


def test_pause_and_resume_timeline_behavior():
    """Verify pausing freezes interpolation and resume continues smoothly without jumping."""
    interp = PositionInterpolator()
    t0 = 100.0
    interp.sync(position_seconds=30.0, status=PlaybackStatus.PLAYING, duration_seconds=180.0, timestamp=t0)

    # Advance 2 seconds playing
    assert abs(interp.get_position(now=t0 + 2.0) - 32.0) < 0.01

    # Pause at 32.0s
    interp.sync(position_seconds=32.0, status=PlaybackStatus.PAUSED, duration_seconds=180.0, timestamp=t0 + 2.0)

    # 10 seconds later while paused, position must remain frozen at 32.0s
    assert interp.get_position(now=t0 + 12.0) == 32.0

    # Resume playing at t0 + 12.0
    interp.sync(position_seconds=32.0, status=PlaybackStatus.PLAYING, duration_seconds=180.0, timestamp=t0 + 12.0)
    assert interp.get_position(now=t0 + 12.0) == 32.0

    # 3 seconds later playing, position advances smoothly to 35.0s
    assert abs(interp.get_position(now=t0 + 15.0) - 35.0) < 0.01

