"""Regression tests for progress bar data flow and interpolation across all player lifecycles."""

import time
import asyncio
from unittest.mock import patch, MagicMock
import pytest

from soulwave.player.base import PlaybackStatus, PlayerState, TrackMetadata
from soulwave.player.mpris import MPRISPlayer
from soulwave.player.manager import PlayerManager
from soulwave.player.interpolator import PositionInterpolator
from soulwave.ui.app import SoulwaveApp


def test_1_firefox_playing_with_valid_position_and_duration():
    """1. Firefox playing with valid position and duration reports correct state and advances."""
    player = MPRISPlayer(player_name="firefox.instance_1_131", use_dbus=False)
    player._apply_dbus_properties({
        "PlaybackStatus": "Playing",
        "Position": 45_000_000,
        "Metadata": {
            "mpris:trackid": "/firefox/track/1",
            "xesam:title": "Firefox Song",
            "xesam:artist": ["Firefox Artist"],
            "mpris:length": 180_000_000,
        },
    })
    state = player.get_state()
    assert state.status == PlaybackStatus.PLAYING
    assert state.metadata.title == "Firefox Song"
    assert state.metadata.duration_seconds == 180.0
    assert 45.0 <= player.get_interpolated_position() < 46.0


def test_2_chromium_playing_with_valid_position_and_duration():
    """2. Chromium playing with valid position and duration."""
    player = MPRISPlayer(player_name="chromium.instance_2_45", use_dbus=False)
    player._apply_dbus_properties({
        "PlaybackStatus": "Playing",
        "Position": 30_000_000,
        "Metadata": {
            "mpris:trackid": "/chromium/track/99",
            "xesam:title": "Chromium Track",
            "xesam:artist": "Chromium Artist",
            "xesam:length": 210_000_000,
        },
    })
    state = player.get_state()
    assert state.status == PlaybackStatus.PLAYING
    assert state.metadata.title == "Chromium Track"
    assert state.metadata.duration_seconds == 210.0
    assert 30.0 <= player.get_interpolated_position() < 31.0


def test_3_spotify_playing_with_valid_position_and_duration():
    """3. Spotify playing with valid position and duration via playerctl formatting."""
    player = MPRISPlayer(player_name="spotify", use_dbus=False)
    delim = MPRISPlayer.FORMAT_DELIMITER
    mock_out = (
        f"Playing{delim}Spotify Artist{delim}Spotify Song{delim}Spotify Album{delim}"
        f"240000000{delim}60000000{delim}1.0{delim}None{delim}false{delim}art_url{delim}spotify:track:123"
    )
    with patch.object(player, "_run_cmd", return_value=mock_out):
        state = player._get_state_playerctl()

    assert state.status == PlaybackStatus.PLAYING
    assert state.metadata.title == "Spotify Song"
    assert state.metadata.duration_seconds == 240.0
    assert 60.0 <= state.position_seconds < 61.0
    assert 60.0 <= player.get_interpolated_position() < 61.0


def test_4_progress_advancing_over_multiple_animation_ticks():
    """4. Progress advancing over multiple animation ticks."""
    player = MPRISPlayer(player_name="firefox.instance_1_131", use_dbus=False)
    player._apply_dbus_properties({
        "PlaybackStatus": "Playing",
        "Position": 10_000_000,
        "Metadata": {
            "mpris:trackid": "/firefox/track/1",
            "xesam:title": "Advancing Track",
            "xesam:artist": ["Artist"],
            "mpris:length": 100_000_000,
        },
    })
    p0 = player.get_interpolated_position()
    time.sleep(0.08)
    p1 = player.get_interpolated_position()
    time.sleep(0.08)
    p2 = player.get_interpolated_position()

    assert p0 < p1 < p2
    assert p2 - p0 >= 0.14


def test_5_pausing_and_resuming():
    """5. Pausing stops advancing, and resuming continues smoothly."""
    player = MPRISPlayer(player_name="test_player", use_dbus=False)
    player._apply_dbus_properties({
        "PlaybackStatus": "Playing",
        "Position": 20_000_000,
        "Metadata": {
            "mpris:trackid": "/track/pause_resume",
            "xesam:title": "Pause Resume Track",
            "xesam:artist": ["Artist"],
            "mpris:length": 200_000_000,
        },
    })
    assert player.get_state().status == PlaybackStatus.PLAYING

    # Player pauses (only PlaybackStatus emitted via D-Bus)
    player._apply_dbus_properties({"PlaybackStatus": "Paused"})
    assert player.get_state().status == PlaybackStatus.PAUSED
    paused_pos = player.get_interpolated_position()
    time.sleep(0.05)
    assert player.get_interpolated_position() == paused_pos

    # Player resumes (only PlaybackStatus emitted via D-Bus)
    player._apply_dbus_properties({"PlaybackStatus": "Playing"})
    assert player.get_state().status == PlaybackStatus.PLAYING
    time.sleep(0.08)
    resumed_pos = player.get_interpolated_position()
    assert resumed_pos > paused_pos


def test_6_seeking_forward_and_backward():
    """6. Seeking forward and backward updates position immediately and reliably."""
    player = MPRISPlayer(player_name="test_player", use_dbus=False)
    player._apply_dbus_properties({
        "PlaybackStatus": "Playing",
        "Position": 50_000_000,
        "Metadata": {
            "mpris:trackid": "/track/seek",
            "xesam:title": "Seek Track",
            "xesam:artist": ["Artist"],
            "mpris:length": 300_000_000,
        },
    })

    # Seek forward to 90s
    player._on_seeked(90_000_000)
    assert 90.0 <= player.get_interpolated_position() < 91.0
    assert player.get_state().position_seconds >= 90.0

    # Seek backward to 25s
    player._on_seeked(25_000_000)
    assert 25.0 <= player.get_interpolated_position() < 26.0
    assert player.get_state().position_seconds >= 25.0


def test_7_switching_between_tracks():
    """7. Switching between tracks resets interpolator epoch and position."""
    player = MPRISPlayer(player_name="test_player", use_dbus=False)
    player._apply_dbus_properties({
        "PlaybackStatus": "Playing",
        "Position": 120_000_000,
        "Metadata": {
            "mpris:trackid": "/track/A",
            "xesam:title": "Song A",
            "xesam:artist": ["Artist A"],
            "mpris:length": 180_000_000,
        },
    })
    assert player.get_state().metadata.title == "Song A"
    assert player.get_interpolated_position() >= 120.0

    # Switch to Track B starting at 0.0s
    player._apply_dbus_properties({
        "PlaybackStatus": "Playing",
        "Position": 0,
        "Metadata": {
            "mpris:trackid": "/track/B",
            "xesam:title": "Song B",
            "xesam:artist": ["Artist B"],
            "mpris:length": 240_000_000,
        },
    })
    state = player.get_state()
    assert state.metadata.title == "Song B"
    assert state.metadata.duration_seconds == 240.0
    assert 0.0 <= player.get_interpolated_position() < 1.0


def test_8_metadata_refresh_without_position_updates():
    """8. Metadata refresh without position update preserves current playback progress."""
    player = MPRISPlayer(player_name="test_player", use_dbus=False)
    player._apply_dbus_properties({
        "PlaybackStatus": "Playing",
        "Position": 75_000_000,
        "Metadata": {
            "mpris:trackid": "/track/same",
            "xesam:title": "Same Song",
            "xesam:artist": ["Artist"],
            "mpris:length": 200_000_000,
        },
    })
    time.sleep(0.05)
    pos_before = player.get_interpolated_position()

    # Metadata update without Position (e.g. artUrl arrived)
    player._apply_dbus_properties({
        "Metadata": {
            "mpris:trackid": "/track/same",
            "xesam:title": "Same Song",
            "xesam:artist": ["Artist"],
            "mpris:length": 200_000_000,
            "mpris:artUrl": "file:///tmp/new_cover.jpg",
        },
    })
    pos_after = player.get_interpolated_position()
    assert pos_after >= pos_before
    assert abs(pos_after - pos_before) < 0.2


def test_9_temporary_playerctl_timeout():
    """9. Temporary playerctl timeout retains last known state without resetting progress."""
    player = MPRISPlayer(player_name="test_player", use_dbus=False)
    player._last_state = PlayerState(
        player_name="test_player",
        status=PlaybackStatus.PLAYING,
        metadata=TrackMetadata(title="Timeout Song", artist="Artist", duration_seconds=180.0),
        position_seconds=42.0,
    )
    player._interpolator.sync(42.0, PlaybackStatus.PLAYING, 180.0)

    def mock_timeout(args, timeout=1.0):
        player._last_cmd_timed_out = True
        return None

    with patch.object(player, "_run_cmd", side_effect=mock_timeout):
        state = player._get_state_playerctl()

    assert state.status == PlaybackStatus.PLAYING
    assert state.metadata.title == "Timeout Song"
    assert 42.0 <= player.get_interpolated_position() < 43.0


def test_10_genuine_player_disconnection():
    """10. Genuine player disconnection resets progress bar and returns DISCONNECTED."""
    player = MPRISPlayer(player_name="test_player", use_dbus=False)
    player._last_state = PlayerState(
        player_name="test_player",
        status=PlaybackStatus.PLAYING,
        metadata=TrackMetadata(title="Closing Song", artist="Artist", duration_seconds=180.0),
        position_seconds=50.0,
    )
    player._interpolator.sync(50.0, PlaybackStatus.PLAYING, 180.0)

    # Disconnect signal
    player._on_name_owner_changed("org.mpris.MediaPlayer2.test_player", ":1.99", "")
    state = player.get_state()
    assert state.status == PlaybackStatus.DISCONNECTED
    assert player.get_interpolated_position() == 0.0
    assert state.metadata.title == ""


def test_11_reconnecting_after_disconnection():
    """11. Reconnecting after disconnection discovers player and restores playback progress."""
    pm = PlayerManager()
    pm._active_player_name = ""
    pm.current_player._last_state = PlayerState(status=PlaybackStatus.DISCONNECTED)

    # Player appears
    with patch.object(MPRISPlayer, "list_players", return_value=["firefox.instance_1_131"]):
        with patch.object(MPRISPlayer, "probe_player_status", return_value=PlaybackStatus.PLAYING):
            switched = pm.check_player_sync()
            assert switched is True
            assert pm._active_player_name == "firefox.instance_1_131"


def test_12_switching_from_firefox_to_spotify():
    """12. Switching from Firefox to Spotify updates active player cleanly."""
    pm = PlayerManager()
    pm.select_player("firefox.instance_1_131")
    assert pm._active_player_name == "firefox.instance_1_131"

    pm.select_player("spotify")
    assert pm._active_player_name == "spotify"
    assert pm.current_player.player_name == "spotify"


@pytest.mark.asyncio
async def test_13_starting_soulwave_while_music_is_already_playing():
    """13. Starting SoulWave while music is already playing initializes progress bar correctly."""
    app = SoulwaveApp()
    mock_player = MagicMock()
    mock_player.player_name = "spotify"
    mock_player.get_state.return_value = PlayerState(
        player_name="spotify",
        status=PlaybackStatus.PLAYING,
        metadata=TrackMetadata(
            title="Pre-existing Song",
            artist="Pre-existing Artist",
            duration_seconds=210.0,
        ),
        position_seconds=85.0,
    )
    mock_player.get_interpolated_position.return_value = 85.0

    with patch.object(app.player_manager, "_current_player", mock_player):
        with patch.object(app.player_manager, "get_state", return_value=mock_player.get_state()):
            async with app.run_test() as pilot:
                await pilot.pause(0.1)
                assert app.progress_bar_view.duration == 210.0
                assert app.progress_bar_view.position == 85.0
                assert app._last_state.status == PlaybackStatus.PLAYING
