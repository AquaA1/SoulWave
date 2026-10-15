"""Tests specifically targeting Firefox MPRIS behavior, signals, and recovery."""

import sys
import time
import subprocess
import pytest

from soulwave.player.base import PlaybackStatus
from soulwave.player.mpris import MPRISPlayer


@pytest.fixture(scope="module")
def firefox_process():
    bus_name = "org.mpris.MediaPlayer2.firefox_test_suite"
    proc = subprocess.Popen(
        [sys.executable, "tests/mock_firefox_service.py", bus_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    line = proc.stdout.readline()
    assert "READY" in line
    time.sleep(0.1)
    yield proc
    # Cleanup
    proc.terminate()
    try:
        proc.wait(timeout=1.0)
    except subprocess.TimeoutExpired:
        proc.kill()


def test_firefox_properties_and_metadata(firefox_process):
    player = MPRISPlayer(player_name="firefox_test_suite")
    time.sleep(0.15)
    state = player.get_state()

    assert state.status == PlaybackStatus.PLAYING
    assert state.can_seek is True
    assert state.metadata.title == "Kendrick Lamar - Not Like Us"
    assert state.metadata.artist == "Kendrick Lamar"
    assert state.metadata.duration_seconds == 240.0
    assert state.metadata.track_id == "/org/mpris/MediaPlayer2/firefox"

    player.close()


def test_firefox_seek_with_buffering_resilience(firefox_process):
    player = MPRISPlayer(player_name="firefox_test_suite")
    time.sleep(0.15)

    # Initial position is 30.0s. Seek forward +10s -> desired = 40.0s
    player.seek(10.0)

    # Visual thumb must update immediately (0ms lag)
    immediate_pos = player.get_interpolated_position()
    assert abs(immediate_pos - 40.0) < 0.2

    # Even during the 250ms buffering window where Firefox D-Bus returns 0.0s,
    # Soulwave's interpolator must reject 0.0s and remain near 40.0s!
    time.sleep(0.1)
    buffering_pos = player.get_interpolated_position()
    assert buffering_pos >= 39.5  # NOT dropped to 0!

    # Wait for seek verification to finish
    time.sleep(0.35)
    assert player.last_seek_result is not None
    assert player.last_seek_result.success is True
    assert abs(player.last_seek_result.resulting_position - 40.0) < 1.0

    player.close()


def test_firefox_set_position_absolute(firefox_process):
    player = MPRISPlayer(player_name="firefox_test_suite")
    time.sleep(0.15)

    # Absolute seek to 95.0s
    player.set_position(95.0)

    # Visual position updates immediately
    assert abs(player.get_interpolated_position() - 95.0) < 0.2

    time.sleep(0.35)
    assert player.last_seek_result is not None
    assert player.last_seek_result.success is True
    assert abs(player.last_seek_result.resulting_position - 95.0) < 1.0

    player.close()


def test_firefox_rapid_ordered_seeks(firefox_process):
    player = MPRISPlayer(player_name="firefox_test_suite")
    time.sleep(0.15)
    base_pos = player.get_confirmed_position()

    # 3 rapid seeks of +5s each
    player.seek(5.0)
    player.seek(5.0)
    player.seek(5.0)

    # Interpolator immediately reflects accumulated +15s
    assert abs(player.get_interpolated_position() - (base_pos + 15.0)) < 0.5

    time.sleep(0.5)
    assert abs(player.get_confirmed_position() - (base_pos + 15.0)) < 1.0

    player.close()


def test_firefox_disconnection_recovery():
    # Start temporary service
    bus_name = "org.mpris.MediaPlayer2.firefox_temp_disconnect"
    proc = subprocess.Popen(
        [sys.executable, "tests/mock_firefox_service.py", bus_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert "READY" in proc.stdout.readline()
    time.sleep(0.1)

    player = MPRISPlayer(player_name="firefox_temp_disconnect")
    time.sleep(0.15)
    assert player.get_state().status == PlaybackStatus.PLAYING

    # Kill player process
    proc.terminate()
    proc.wait(timeout=1.0)
    time.sleep(0.2)

    # State should recover and report DISCONNECTED
    state = player.get_state()
    assert state.status == PlaybackStatus.DISCONNECTED
    assert state.can_seek is False
    assert state.can_control is False

    player.close()
