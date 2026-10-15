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
