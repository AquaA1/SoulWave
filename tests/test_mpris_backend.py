"""Backend tests for MPRISPlayer and PositionInterpolator independently of UI."""

import time
import pytest
from soulwave.player.base import PlaybackStatus, LoopStatus, ShuffleStatus, TrackMetadata, PlayerState
from soulwave.player.interpolator import PositionInterpolator
from soulwave.player.mpris import MPRISPlayer, SeekVerificationResult


def test_interpolator_desired_vs_confirmed_position():
    interp = PositionInterpolator()
    t0 = 100.0

    # Sync at 10.0s playing, duration 200s
    interp.sync(10.0, PlaybackStatus.PLAYING, 200.0, timestamp=t0)
    assert interp.get_position(now=t0) == 10.0
    assert interp.get_confirmed_position(now=t0) == 10.0
    assert not interp.is_seeking()

    # User initiates seek to 50.0s
    desired = interp.start_seek(50.0)
    assert desired == 50.0
    assert interp.is_seeking()
    assert interp.get_position(now=t0) == 50.0
    # Confirmed position remains at 10.0s
    assert interp.get_confirmed_position(now=t0) == 10.0

    # Normal polling report of 11.0s (stale/pre-seek) during settle window must be rejected
    interp.sync(11.0, PlaybackStatus.PLAYING, 200.0, timestamp=t0 + 0.2)
    assert interp.is_seeking()
    assert interp.get_position(now=t0 + 0.2) >= 50.0  # Still near desired 50.0s!
    assert abs(interp.get_confirmed_position(now=t0 + 0.2) - 10.2) < 0.01

    # Browser drops position to 0.0s (buffering quirk) during settle window -> must be rejected
    interp.sync(0.0, PlaybackStatus.PLAYING, 200.0, timestamp=t0 + 0.5)
    assert interp.is_seeking()
    assert interp.get_position(now=t0 + 0.5) >= 50.0  # Does NOT drop to 0!

    # Authoritative signal or player reports position close to desired (e.g. 50.2s)
    interp.sync(50.2, PlaybackStatus.PLAYING, 200.0, timestamp=t0 + 0.8)
    assert not interp.is_seeking()
    assert interp.get_confirmed_position(now=t0 + 0.8) == 50.2
    assert interp.get_position(now=t0 + 0.8) == 50.2


def test_interpolator_rapid_relative_seeks():
    interp = PositionInterpolator()
    t0 = 100.0
    interp.sync(20.0, PlaybackStatus.PAUSED, 100.0, timestamp=t0)

    # 3 rapid keypresses of +5s each
    p1 = interp.step_relative_seek(5.0)
    assert p1 == 25.0
    assert interp.get_seek_seq() == 1

    p2 = interp.step_relative_seek(5.0)
    assert p2 == 30.0
    assert interp.get_seek_seq() == 2

    p3 = interp.step_relative_seek(5.0)
    assert p3 == 35.0
    assert interp.get_seek_seq() == 3

    assert interp.get_position() == 35.0
    assert interp.get_confirmed_position() == 20.0


def test_interpolator_clamping():
    interp = PositionInterpolator()
    interp.sync(10.0, PlaybackStatus.PAUSED, 60.0)

    # Clamp at duration
    assert interp.start_seek(100.0) == 60.0
    # Clamp at 0
    assert interp.step_relative_seek(-200.0) == 0.0


def test_mpris_checks_before_seeking():
    player = MPRISPlayer(use_dbus=False)

    # 1. Disconnected player -> rejected
    player._last_state = PlayerState(status=PlaybackStatus.DISCONNECTED)
    can_seek, reason = player._can_seek_check()
    assert not can_seek
    assert "disconnected" in reason.lower()

    # 2. CanSeek is False and duration <= 0 -> rejected
    player._last_state = PlayerState(
        status=PlaybackStatus.PLAYING,
        can_seek=False,
        metadata=TrackMetadata(duration_seconds=0.0),
    )
    can_seek, reason = player._can_seek_check()
    assert not can_seek

    # 3. CanSeek is True with valid duration -> accepted
    player._last_state = PlayerState(
        status=PlaybackStatus.PLAYING,
        can_seek=True,
        metadata=TrackMetadata(duration_seconds=180.0, track_id="/org/mpris/track1"),
    )
    can_seek, reason = player._can_seek_check()
    assert can_seek


def test_mpris_status_and_metadata_parsers():
    assert MPRISPlayer._parse_status("Playing") == PlaybackStatus.PLAYING
    assert MPRISPlayer._parse_status("PAUSED") == PlaybackStatus.PAUSED
    assert MPRISPlayer._parse_status("Stopped") == PlaybackStatus.STOPPED
    assert MPRISPlayer._parse_status("unknown") == PlaybackStatus.DISCONNECTED

    assert MPRISPlayer._parse_loop("track") == LoopStatus.TRACK
    assert MPRISPlayer._parse_loop("playlist") == LoopStatus.PLAYLIST
    assert MPRISPlayer._parse_loop("none") == LoopStatus.NONE

    assert MPRISPlayer._parse_shuffle("true") == ShuffleStatus.ON
    assert MPRISPlayer._parse_shuffle("1") == ShuffleStatus.ON
    assert MPRISPlayer._parse_shuffle("false") == ShuffleStatus.OFF


def test_mpris_timeline_preservation_and_track_change():
    player = MPRISPlayer(use_dbus=False)

    # 1. Normal track metadata
    props1 = {
        "PlaybackStatus": "Playing",
        "Metadata": {
            "mpris:trackid": "/org/mpris/track1",
            "xesam:title": "Song A",
            "xesam:artist": "Artist A",
            "mpris:length": 180_000_000,
        },
        "Position": 25_000_000,
    }
    player._apply_dbus_properties(props1)
    assert player._last_state.metadata.duration_seconds == 180.0
    assert player._last_state.position_seconds == 25.0

    # 2. Transient buffering drop on SAME track: duration dropped to 0/missing
    props_buffering = {
        "Metadata": {
            "mpris:trackid": "/org/mpris/track1",
            "xesam:title": "Song A",
            "xesam:artist": "Artist A",
            # mpris:length is missing
        },
    }
    player._apply_dbus_properties(props_buffering)
    # Duration must be preserved from previous reading for the same track
    assert player._last_state.metadata.duration_seconds == 180.0

    # 3. New track with new length updates cleanly
    props_new_track = {
        "Metadata": {
            "mpris:trackid": "/org/mpris/track2",
            "xesam:title": "Song B",
            "xesam:artist": "Artist B",
            "mpris:length": 210_000_000,
        },
    }
    player._apply_dbus_properties(props_new_track)
    assert player._last_state.metadata.title == "Song B"
    assert player._last_state.metadata.duration_seconds == 210.0
