"""Tests for player controllers and management."""

from soulwave.player.base import PlaybackStatus, LoopStatus, ShuffleStatus
from soulwave.player.mock_player import MockPlayer
from soulwave.player.manager import PlayerManager
from soulwave.player.mpris import MPRISPlayer


def test_mock_player_controls():
    player = MockPlayer()
    state = player.get_state()

    assert state.status == PlaybackStatus.PLAYING
    assert state.metadata.title != ""
    assert state.can_control is True

    # Play / Pause toggle
    player.play_pause()
    assert player.get_state().status == PlaybackStatus.PAUSED

    player.play_pause()
    assert player.get_state().status == PlaybackStatus.PLAYING

    # Skip next track
    initial_title = state.metadata.title
    player.next_track()
    new_title = player.get_state().metadata.title
    assert new_title != initial_title

    # Seeking
    player.set_position(30.0)
    assert abs(player.get_interpolated_position() - 30.0) < 0.2

    # Volume
    player.set_volume(0.5)
    assert abs(player.get_state().volume - 0.5) < 0.05

    # Shuffle & Loop
    player.toggle_shuffle()
    assert player.get_state().shuffle == ShuffleStatus.ON

    player.cycle_loop()
    assert player.get_state().loop != LoopStatus.PLAYLIST


def test_player_manager_demo():
    mgr = PlayerManager(force_demo=True)
    assert mgr.is_demo is True
    state = mgr.get_state()
    assert state.player_name == "Soulwave Demo"


def test_mpris_status_parser():
    assert MPRISPlayer._parse_status("Playing") == PlaybackStatus.PLAYING
    assert MPRISPlayer._parse_status("PAUSED") == PlaybackStatus.PAUSED
    assert MPRISPlayer._parse_status("stopped") == PlaybackStatus.STOPPED
    assert MPRISPlayer._parse_loop("track") == LoopStatus.TRACK
    assert MPRISPlayer._parse_loop("playlist") == LoopStatus.PLAYLIST
    assert MPRISPlayer._parse_shuffle("true") == ShuffleStatus.ON
    assert MPRISPlayer._parse_shuffle("off") == ShuffleStatus.OFF
