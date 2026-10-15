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
