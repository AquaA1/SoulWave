"""Tests specifically targeting Chromium MPRIS behavior, Introspect quirks, and recovery."""

import sys
import time
import subprocess
import pytest

from soulwave.player.base import PlaybackStatus
from soulwave.player.mpris import MPRISPlayer


def _can_run_dbus_mock():
    try:
        import dbus
        import dbus.mainloop.glib
        from gi.repository import GLib
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.SessionBus()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _can_run_dbus_mock(),
    reason="D-Bus session bus and dbus/gi libraries required for mock Chromium tests",
)


@pytest.fixture(scope="module")
def chromium_process():
    bus_name = "org.mpris.MediaPlayer2.chromium_test_suite"
    proc = subprocess.Popen(
        [sys.executable, "tests/mock_chromium_service.py", bus_name],
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


def test_chromium_properties_and_introspection_quirk(chromium_process):
    # Chromium returns empty <node></node> for Introspect().
    # Ensure MPRISPlayer handles this without crashing.
    player = MPRISPlayer(player_name="chromium_test_suite")
    time.sleep(0.15)
    state = player.get_state()

    assert state.status == PlaybackStatus.PLAYING
    assert state.can_seek is True
    assert state.metadata.title == "Chromium Audio Stream"
    assert state.metadata.artist == "Chromium Media"
    assert state.metadata.duration_seconds == 120.0
    assert state.metadata.track_id == "/org/chromium/MediaPlayer2/TrackList/Track1E61B6D34409484446263FAA0E042D22"

    player.close()


def test_chromium_set_position_absolute(chromium_process):
    player = MPRISPlayer(player_name="chromium_test_suite")
    time.sleep(0.15)

    # Absolute seek to 45.0s
    player.set_position(45.0)

    # Immediate visual update
    assert abs(player.get_interpolated_position() - 45.0) < 0.2

    # Verification
    time.sleep(0.35)
    assert player.last_seek_result is not None
    assert player.last_seek_result.success is True
    assert abs(player.last_seek_result.resulting_position - 45.0) < 1.0

    player.close()


def test_chromium_seek_relative(chromium_process):
    player = MPRISPlayer(player_name="chromium_test_suite")
    time.sleep(0.15)

    pos_before = player.get_confirmed_position()
    player.seek(15.0)

    # Immediate visual update
    assert abs(player.get_interpolated_position() - (pos_before + 15.0)) < 0.2

    time.sleep(0.35)
    assert player.last_seek_result is not None
    assert player.last_seek_result.success is True
    assert abs(player.last_seek_result.resulting_position - (pos_before + 15.0)) < 1.0

    player.close()


def test_chromium_rapid_ordered_seeks(chromium_process):
    player = MPRISPlayer(player_name="chromium_test_suite")
    time.sleep(0.15)
    base_pos = player.get_confirmed_position()

    # 3 rapid seeks of +10s each
    player.seek(10.0)
    player.seek(10.0)
    player.seek(10.0)

    # Immediate visual accumulation
    assert abs(player.get_interpolated_position() - (base_pos + 30.0)) < 0.5

    time.sleep(0.5)
    assert abs(player.get_confirmed_position() - (base_pos + 30.0)) < 1.0

    player.close()


def test_chromium_disconnection_recovery():
    bus_name = "org.mpris.MediaPlayer2.chromium_temp_disconnect"
    proc = subprocess.Popen(
        [sys.executable, "tests/mock_chromium_service.py", bus_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert "READY" in proc.stdout.readline()
    time.sleep(0.1)

    player = MPRISPlayer(player_name="chromium_temp_disconnect")
    time.sleep(0.15)
    assert player.get_state().status == PlaybackStatus.PLAYING

    proc.terminate()
    proc.wait(timeout=1.0)
    time.sleep(0.2)

    state = player.get_state()
    assert state.status == PlaybackStatus.DISCONNECTED
    assert state.can_seek is False

    player.close()
