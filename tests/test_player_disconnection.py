"""Regression tests for MPRIS player-disconnection lifecycle, discovery caching,
distinguishing stopped vs disconnected playback, and PlayerManager recovery.
"""

from unittest.mock import MagicMock, patch
import subprocess
import time
import pytest

from soulwave.player.base import (
    PlaybackStatus,
    PlayerState,
    TrackMetadata,
)
from soulwave.player.mpris import MPRISPlayer
from soulwave.player.manager import PlayerManager
from soulwave.ui.widgets.now_playing import NowPlayingView


def test_1_firefox_completely_closes_while_playing():
    """1. Firefox completely closes while playing."""
    player = MPRISPlayer(player_name="firefox.instance_1_131", use_dbus=False)
    player._bus_name = "org.mpris.MediaPlayer2.firefox.instance_1_131"
    player._last_state = PlayerState(
        player_name="firefox.instance_1_131",
        status=PlaybackStatus.PLAYING,
        metadata=TrackMetadata(title="Song A", artist="Artist A", duration_seconds=180.0),
        position_seconds=15.0,
    )
    player._interpolator.sync(15.0, PlaybackStatus.PLAYING, 180.0)

    # Disconnection signal arrives
    player._on_name_owner_changed("org.mpris.MediaPlayer2.firefox.instance_1_131", ":1.131", "")

    state = player.get_state()
    assert state.status == PlaybackStatus.DISCONNECTED
    assert state.metadata.title == ""
    assert state.position_seconds == 0.0


def test_2_firefox_completely_closes_while_paused():
    """2. Firefox completely closes while paused."""
    player = MPRISPlayer(player_name="firefox.instance_1_131", use_dbus=False)
    player._bus_name = "org.mpris.MediaPlayer2.firefox.instance_1_131"
    player._last_state = PlayerState(
        player_name="firefox.instance_1_131",
        status=PlaybackStatus.PAUSED,
        metadata=TrackMetadata(title="Song A", artist="Artist A", duration_seconds=180.0),
        position_seconds=45.0,
    )
    player._interpolator.sync(45.0, PlaybackStatus.PAUSED, 180.0)

    player._on_name_owner_changed("org.mpris.MediaPlayer2.firefox.instance_1_131", ":1.131", "")

    state = player.get_state()
    assert state.status == PlaybackStatus.DISCONNECTED
    assert state.metadata.title == ""
    assert state.position_seconds == 0.0


def test_3_music_tab_closes_while_firefox_remains_open():
    """3. Music tab closes while Firefox remains open.
    Reports STOPPED with empty metadata -> clears previous track & progress,
    but does NOT classify browser itself as disconnected.
    """
    player = MPRISPlayer(player_name="firefox.instance_1_131", use_dbus=False)
    player._last_state = PlayerState(
        player_name="firefox.instance_1_131",
        status=PlaybackStatus.PLAYING,
        metadata=TrackMetadata(title="Song A", artist="Artist A", duration_seconds=180.0),
        position_seconds=50.0,
    )

    # Browser tab closed: Firefox emits PlaybackStatus: Stopped with empty metadata
    player._apply_dbus_properties({
        "PlaybackStatus": "Stopped",
        "Metadata": {},
    })

    state = player.get_state()
    # Browser is still running: NOT disconnected!
    assert state.status == PlaybackStatus.STOPPED
    assert state.player_name == "firefox.instance_1_131"
    # But previous track and progress are cleared!
    assert state.metadata.title == ""
    assert state.position_seconds == 0.0

    # In NowPlayingView: badge shows FIREFOX.INSTANCE_1_131 ■ STOPPED, but track says Waiting...
    view = NowPlayingView()
    view.update_state(state, (56, 189, 248))
    plain = view.render().plain
    assert "FIREFOX.INSTANCE_1_131" in plain
    assert "STOPPED" in plain
    assert "Waiting for media playback..." in plain


def test_4_firefox_closes_while_spotify_is_available():
    """4. Firefox closes while Spotify is available -> switches to Spotify."""
    pm = PlayerManager()
    pm._active_player_name = "firefox.instance_1_131"
    pm.current_player._bus_name = "org.mpris.MediaPlayer2.firefox.instance_1_131"
    pm.current_player.player_name = "firefox.instance_1_131"
    pm.current_player._last_state = PlayerState(
        player_name="firefox.instance_1_131",
        status=PlaybackStatus.PLAYING,
        metadata=TrackMetadata(title="Firefox Song", artist="Artist"),
    )

    # When discovering players after Firefox closes, only Spotify is present
    with patch.object(MPRISPlayer, "list_players", return_value=["spotify"]):
        with patch.object(MPRISPlayer, "probe_player_status", return_value=PlaybackStatus.PLAYING):
            # Firefox disconnects
            pm.current_player._on_name_owner_changed("org.mpris.MediaPlayer2.firefox.instance_1_131", ":1.131", "")

    assert pm._active_player_name == "spotify"


def test_5_firefox_closes_while_no_other_players_exist():
    """5. Firefox closes while no other players exist -> enters clean waiting state."""
    pm = PlayerManager()
    pm._active_player_name = "firefox.instance_1_131"
    pm.current_player._bus_name = "org.mpris.MediaPlayer2.firefox.instance_1_131"
    pm.current_player._last_state = PlayerState(
        player_name="firefox.instance_1_131",
        status=PlaybackStatus.PLAYING,
        metadata=TrackMetadata(title="Firefox Song", artist="Artist"),
    )

    with patch.object(MPRISPlayer, "list_players", return_value=[]):
        pm.current_player._on_name_owner_changed("org.mpris.MediaPlayer2.firefox.instance_1_131", ":1.131", "")
        pm.check_player_sync()

    assert pm._active_player_name == ""
    assert pm.get_state().status == PlaybackStatus.DISCONNECTED

    # UI renders WAITING badge
    view = NowPlayingView()
    view.update_state(pm.get_state(), (56, 189, 248))
    plain = view.render().plain
    assert "WAITING" in plain
    assert "SEARCHING FOR PLAYER" in plain


def test_6_firefox_reopens_and_starts_playback():
    """6. Firefox reopens and starts playback -> manager auto-connects."""
    pm = PlayerManager()
    pm._active_player_name = ""

    # Firefox launches and is detected
    with patch.object(MPRISPlayer, "list_players", return_value=["firefox.instance_1_131"]):
        with patch.object(MPRISPlayer, "probe_player_status", return_value=PlaybackStatus.PLAYING):
            pm.check_player_sync()

    assert pm._active_player_name == "firefox.instance_1_131"


def test_7_playerctl_returns_definitive_disconnected_result():
    """7. Playerctl returns a definitive disconnected result -> updates _last_state immediately."""
    player = MPRISPlayer(player_name="firefox.instance_1_131", use_dbus=False)
    player._playerctl_bin = "/usr/bin/playerctl"
    player._last_state = PlayerState(
        player_name="firefox.instance_1_131",
        status=PlaybackStatus.PLAYING,
        metadata=TrackMetadata(title="Old Song", artist="Old Artist", duration_seconds=120.0),
    )

    # Mock playerctl commands failing definitively (rc=1, not timeout)
    player._last_cmd_timed_out = False
    with patch.object(player, "_run_cmd", return_value=None):
        with patch.object(MPRISPlayer, "list_players", return_value=[]):
            state = player._get_state_playerctl()

    assert state.status == PlaybackStatus.DISCONNECTED
    assert player.get_state().status == PlaybackStatus.DISCONNECTED
    assert player.get_state().metadata.title == ""
    assert player.get_state().position_seconds == 0.0


def test_8_temporary_playerctl_timeout_does_not_disconnect():
    """8. A temporary playerctl timeout does not incorrectly disconnect the player."""
    player = MPRISPlayer(player_name="firefox.instance_1_131", use_dbus=False)
    player._playerctl_bin = "/usr/bin/playerctl"
    player._last_state = PlayerState(
        player_name="firefox.instance_1_131",
        status=PlaybackStatus.PLAYING,
        metadata=TrackMetadata(title="Active Song", artist="Artist", duration_seconds=200.0),
        position_seconds=50.0,
    )

    # Command times out (is_timeout=True)
    def mock_timeout(args, timeout=1.0):
        player._last_cmd_timed_out = True
        return None

    with patch.object(player, "_run_cmd", side_effect=mock_timeout):
        state = player._get_state_playerctl()

    # Must preserve current state rather than disconnecting!
    assert state.status == PlaybackStatus.PLAYING
    assert state.metadata.title == "Active Song"


def test_9_disconnected_player_never_recreated_from_stale_discovery_cache():
    """9. A disconnected player is never recreated from stale discovery cache."""
    pm = PlayerManager()
    pm._active_player_name = "firefox.instance_1_131"
    pm.current_player._last_state = PlayerState(
        player_name="firefox.instance_1_131",
        status=PlaybackStatus.DISCONNECTED,
    )

    # Even if stale discovery returns the dead player, find_best_player and check_player_sync MUST NOT recreate it
    with patch.object(MPRISPlayer, "list_players", return_value=["firefox.instance_1_131"]):
        best = pm.find_best_player(["firefox.instance_1_131"])
        assert best is None

        switched = pm.check_player_sync()
        assert pm._active_player_name == ""


def test_10_disconnect_handling_does_not_cause_recursive_manager_callbacks():
    """10. Disconnect handling does not cause recursive manager callbacks."""
    call_count = 0

    def on_change():
        nonlocal call_count
        call_count += 1
        pm.check_player_sync()

    pm = PlayerManager(on_state_change=on_change)
    pm._active_player_name = "firefox.instance_1_131"
    pm.current_player._bus_name = "org.mpris.MediaPlayer2.firefox.instance_1_131"

    with patch.object(MPRISPlayer, "list_players", return_value=[]):
        # Fire disconnect
        pm.current_player._on_name_owner_changed("org.mpris.MediaPlayer2.firefox.instance_1_131", ":1.131", "")

    # Recursion guard should ensure it finishes without RecursionError and only minimal calls
    assert call_count <= 2
    assert pm._active_player_name == ""


def test_11_existing_pause_resume_and_track_transitions_work():
    """11. Existing pause/resume and track transitions still work."""
    player = MPRISPlayer(player_name="test_player", use_dbus=False)

    # Track A Playing
    player._apply_dbus_properties({
        "PlaybackStatus": "Playing",
        "Position": 10_000_000,
        "Metadata": {
            "mpris:trackid": "/track/A",
            "xesam:title": "Song A",
            "xesam:artist": ["Artist A"],
            "mpris:length": 180_000_000,
        },
    })
    state = player.get_state()
    assert state.status == PlaybackStatus.PLAYING
    assert state.metadata.title == "Song A"
    assert state.metadata.duration_seconds == 180.0
    assert state.position_seconds >= 10.0 and state.position_seconds < 10.5

    # Pause: metadata and progress preserved
    player._apply_dbus_properties({
        "PlaybackStatus": "Paused",
        "Position": 15_000_000,
    })
    state = player.get_state()
    assert state.status == PlaybackStatus.PAUSED
    assert state.metadata.title == "Song A"
    assert state.metadata.duration_seconds == 180.0
    assert state.position_seconds == 15.0

    # Resume: still Song A
    player._apply_dbus_properties({
        "PlaybackStatus": "Playing",
    })
    state = player.get_state()
    assert state.status == PlaybackStatus.PLAYING
    assert state.metadata.title == "Song A"

    # Track Transition: Song B starts
    player._apply_dbus_properties({
        "PlaybackStatus": "Playing",
        "Position": 0,
        "Metadata": {
            "mpris:trackid": "/track/B",
            "xesam:title": "Song B",
            "xesam:artist": ["Artist B"],
            "mpris:length": 210_000_000,
        },
    })
    state = player.get_state()
    assert state.status == PlaybackStatus.PLAYING
    assert state.metadata.title == "Song B"
    assert state.metadata.duration_seconds == 210.0
    assert state.position_seconds >= 0.0 and state.position_seconds < 0.5
