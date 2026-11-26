"""Unit and integration tests for progress bar and playerctl MPRIS fallback."""

import threading
import time
import unittest
from unittest.mock import MagicMock, patch

from soulwave.player.base import PlaybackStatus, PlayerState, TrackMetadata
from soulwave.player.mpris import MPRISPlayer
from soulwave.player.interpolator import PositionInterpolator


class TestProgressBarPlayerctl(unittest.TestCase):
    def setUp(self):
        self.player = MPRISPlayer(player_name="org.mpris.MediaPlayer2.spotify", use_dbus=False)
        self.player._playerctl_bin = "/usr/bin/playerctl"

    def tearDown(self):
        if hasattr(self, "player") and self.player:
            self.player.close()

    def test_run_cmd_strips_dbus_prefix(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="test_output\n")
            self.player._run_cmd(["status"])
            mock_run.assert_called_once()
            cmd = mock_run.call_args[0][0]
            # Must be ['...playerctl', '-p', 'spotify', 'status'] NOT 'org.mpris.MediaPlayer2.spotify'
            self.assertIn("-p", cmd)
            idx = cmd.index("-p")
            self.assertEqual(cmd[idx + 1], "spotify")

    def test_probe_player_status_strips_prefix(self):
        with patch("shutil.which", return_value="/usr/bin/playerctl"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="Playing\n")
                status = MPRISPlayer.probe_player_status("org.mpris.MediaPlayer2.firefox")
                self.assertEqual(status, PlaybackStatus.PLAYING)
                cmd = mock_run.call_args[0][0]
                idx = cmd.index("-p")
                self.assertEqual(cmd[idx + 1], "firefox")

    def test_get_state_playerctl_fallback_when_position_empty(self):
        # Metadata string returns empty position (6th field)
        delim = MPRISPlayer.FORMAT_DELIMITER
        mock_output = (
            f"Playing{delim}Artist Name{delim}Track Title{delim}Album Name{delim}"
            f"240000000{delim}{delim}0.8{delim}None{delim}false{delim}art_url{delim}track_1"
        )
        with patch.object(self.player, "_run_cmd") as mock_cmd:
            def cmd_side_effect(args, **kwargs):
                if args[0] == "metadata":
                    return mock_output
                elif args[0] == "position":
                    return "45.5"
                return None
            mock_cmd.side_effect = cmd_side_effect

            state = self.player._get_state_playerctl()
            self.assertEqual(state.status, PlaybackStatus.PLAYING)
            self.assertEqual(state.metadata.duration_seconds, 240.0)
            self.assertEqual(state.position_seconds, 45.5)

    def test_get_state_playerctl_handles_microseconds(self):
        delim = MPRISPlayer.FORMAT_DELIMITER
        out_us = (
            f"Playing{delim}Artist{delim}Title{delim}Album{delim}"
            f"100000000{delim}50000000{delim}1.0{delim}None{delim}false{delim}{delim}"
        )
        with patch.object(self.player, "_run_cmd", return_value=out_us):
            state = self.player._get_state_playerctl()
            self.assertAlmostEqual(state.position_seconds, 50.0)
            self.assertAlmostEqual(state.metadata.duration_seconds, 100.0)

    def test_seek_command_sign_syntax(self):
        # Forward seek (+5s)
        with patch.object(self.player, "_run_cmd") as mock_cmd:
            self.player._last_state.status = PlaybackStatus.PLAYING
            self.player._last_state.metadata.duration_seconds = 100.0
            self.player._last_state.can_seek = True

            self.player.seek(5.0)
            self.player.drain_commands()
            mock_cmd.assert_any_call(["position", "5.0+"])

        # Backward seek (-5s) must pass "5.0-" NOT "-5.0"
        with patch.object(self.player, "_run_cmd") as mock_cmd:
            self.player._last_state.status = PlaybackStatus.PLAYING
            self.player._last_state.metadata.duration_seconds = 100.0
            self.player._last_state.can_seek = True

            self.player.seek(-5.0)
            self.player.drain_commands()
            mock_cmd.assert_any_call(["position", "5.0-"])

    def test_set_position_works_without_track_id_in_cli_mode(self):
        with patch.object(self.player, "_run_cmd") as mock_cmd:
            self.player._last_state.status = PlaybackStatus.PLAYING
            self.player._last_state.metadata.duration_seconds = 180.0
            self.player._last_state.metadata.track_id = ""  # No track ID
            self.player._last_state.can_seek = True

            self.player.set_position(90.0)
            self.player.drain_commands()
            mock_cmd.assert_any_call(["position", "90.0"])

    def test_get_state_playerctl_non_blocking_cached(self):
        with patch.object(self.player, "_run_cmd") as mock_cmd:
            self.player._initialized = True
            self.player._last_state = PlayerState(
                player_name="spotify",
                status=PlaybackStatus.PLAYING,
                metadata=TrackMetadata(title="Song", artist="Artist", duration_seconds=200.0),
                position_seconds=10.0,
            )
            self.player._interpolator.sync(10.0, PlaybackStatus.PLAYING, 200.0)

            st = self.player.get_state()
            mock_cmd.assert_not_called()
            self.assertEqual(st.status, PlaybackStatus.PLAYING)
            self.assertEqual(st.metadata.title, "Song")
            self.assertGreaterEqual(st.position_seconds, 10.0)

    def test_background_poll_status_hold_safeguard(self):
        import time
        delim = MPRISPlayer.FORMAT_DELIMITER
        mock_output = (
            f"Playing{delim}Artist Name{delim}Track Title{delim}Album Name{delim}"
            f"200{delim}50{delim}1.0{delim}None{delim}false{delim}art{delim}id1"
        )
        with patch.object(self.player, "_run_cmd", return_value=mock_output):
            with self.player._lock:
                self.player._last_state.status = PlaybackStatus.PAUSED
                self.player._status_hold_until = time.monotonic() + 1.0
                self.player._status_hold_target = PlaybackStatus.PAUSED

            new_state = self.player._get_state_playerctl()
            self.assertEqual(new_state.status, PlaybackStatus.PAUSED)

    def test_list_players_ttl_caching(self):
        with patch("soulwave.player.mpris._DBUS_AVAILABLE", False):
            with patch("shutil.which", return_value="/usr/bin/playerctl"):
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=0, stdout="spotify\nfirefox\n")
                    p1 = MPRISPlayer.list_players(force=True)
                    self.assertEqual(p1, ["spotify", "firefox"])
                    self.assertEqual(mock_run.call_count, 1)

                    p2 = MPRISPlayer.list_players(force=False)
                    self.assertEqual(p2, ["spotify", "firefox"])
                    self.assertEqual(mock_run.call_count, 1)

    def test_sync_player_state_does_not_override_progress_bar_position(self):
        from soulwave.config import Config
        from soulwave.ui.app import SoulwaveApp
        app = SoulwaveApp(config=Config(theme="night"), force_demo=True)
        app.top_bar = MagicMock()
        app.progress_bar_view = MagicMock()
        app.now_playing_view = MagicMock()
        app.controls_view = MagicMock()
        app.lyrics_view = MagicMock()
        app.player_manager = MagicMock()
        app.companion_view = MagicMock()
        app.palette = MagicMock()
        app.accent_color = (100, 100, 100)
        app.active_theme = MagicMock()
        app.active_theme.name = "Night"
        app.active_theme.mascot_idle_color = (255, 255, 255)

        test_state = PlayerState(
            player_name="spotify",
            status=PlaybackStatus.PLAYING,
            metadata=TrackMetadata(title="Test", artist="Artist", duration_seconds=180.0),
            position_seconds=42.0,
        )
        app.player_manager.get_state.return_value = test_state

        app._sync_player_state()

        # progress_bar_view.update_progress MUST NOT be called from _sync_player_state
        app.progress_bar_view.update_progress.assert_not_called()
        app.now_playing_view.update_state.assert_called_once_with(test_state, app.accent_color)
        app.controls_view.update_state.assert_called_once_with(test_state, app.accent_color)

        # But when _animation_tick runs, it DOES update progress_bar_view
        app.player_manager.current_player.get_interpolated_position.return_value = 42.5
        app.visualizer_view = MagicMock()
        app.visualizer_view.current_energy = 0.5
        app.mascot_view = MagicMock()
        app._animation_tick()
        app.progress_bar_view.update_progress.assert_called_once_with(42.5, 180.0, app.accent_color)

    def test_close_player_while_poll_in_flight_prevents_callback_and_state_update(self):
        import threading
        import time
        in_poll_event = threading.Event()
        release_poll_event = threading.Event()
        callback_called = []

        delim = MPRISPlayer.FORMAT_DELIMITER
        mock_output = (
            f"Playing{delim}Slow Artist{delim}Slow Track{delim}Slow Album{delim}"
            f"200{delim}50{delim}1.0{delim}None{delim}false{delim}art{delim}id_slow"
        )

        def slow_run_cmd(args, **kwargs):
            if args[0] == "metadata":
                in_poll_event.set()
                release_poll_event.wait(timeout=1.0)
                return mock_output
            return None

        # Create player with callback
        p = MPRISPlayer(
            player_name="spotify",
            use_dbus=False,
            on_state_change=lambda: callback_called.append(True),
        )
        p._playerctl_bin = "/usr/bin/playerctl"
        original_state = p._last_state

        with patch.object(p, "_run_cmd", side_effect=slow_run_cmd):
            # Wake background poll
            p._poll_wake_event.set()
            # Wait for poll thread to enter _run_cmd
            self.assertTrue(in_poll_event.wait(timeout=1.0))

            # Now close player while poll is in flight
            p.close()
            # Allow slow poll to return
            release_poll_event.set()
            time.sleep(0.05)

        # Verification:
        # 1. Callback must NOT have fired after closure
        self.assertEqual(len(callback_called), 0)
        # 2. Cached state must not have updated to the slow track
        self.assertNotEqual(p._last_state.metadata.title, "Slow Track")
        self.assertFalse(p._running)

    def test_rapid_consecutive_seek_commands_bounded_queue_coalescing(self):
        # Initial state setup
        self.player._last_state.status = PlaybackStatus.PLAYING
        self.player._last_state.metadata.duration_seconds = 200.0
        self.player._last_state.can_seek = True
        self.player._interpolator.sync(10.0, PlaybackStatus.PLAYING, 200.0)

        executed_cmds = []

        def capture_cmd(args, **kwargs):
            executed_cmds.append(args)
            return "OK"

        with patch.object(self.player, "_run_cmd", side_effect=capture_cmd):
            # 1. Verify queue bounding with 40 rapid seeks (maxsize is 32)
            for _ in range(40):
                self.player.seek(1.0)

            # Queue capacity check: must not exceed bounded limit (32)
            self.assertLessEqual(self.player._cmd_queue.qsize(), 32)

            self.player.drain_commands()
            self.assertGreater(len(executed_cmds), 0)

            # 2. Verify absolute scrubbing coalescing (set_position)
            executed_cmds.clear()
            gate = threading.Event()

            def gated_capture(args, **kwargs):
                executed_cmds.append(args)
                if args == ["position", "50.0"]:
                    gate.wait(timeout=1.0)
                return "OK"

            with patch.object(self.player, "_run_cmd", side_effect=gated_capture):
                self.player.set_position(50.0)
                time.sleep(0.02)
                self.player.set_position(55.0)
                self.player.set_position(60.0)
                gate.set()
                self.player.drain_commands()
                # Intermediates should coalesce; 55.0 skipped in favor of 60.0
                pos_cmds = [cmd for cmd in executed_cmds if cmd and cmd[0] == "position"]
                self.assertLessEqual(len(pos_cmds), 2)
                self.assertEqual(pos_cmds[-1], ["position", "60.0"])

    def test_status_hold_expiration_allows_player_status_updates(self):
        import time
        delim = MPRISPlayer.FORMAT_DELIMITER
        mock_output = (
            f"Playing{delim}Artist{delim}Title{delim}Album{delim}"
            f"200{delim}50{delim}1.0{delim}None{delim}false{delim}art{delim}id1"
        )
        with patch.object(self.player, "_run_cmd", return_value=mock_output):
            with self.player._lock:
                # Hold window has expired (in the past)
                self.player._last_state.status = PlaybackStatus.PAUSED
                self.player._status_hold_until = time.monotonic() - 0.5
                self.player._status_hold_target = PlaybackStatus.PAUSED

            # Poll returns Playing; since hold is expired, Playing should be accepted
            new_state = self.player._get_state_playerctl()
            self.assertEqual(new_state.status, PlaybackStatus.PLAYING)

    def test_playerctl_position_conversion_sub_ten_seconds(self):
        """Regression test: values from 0.1s to 9.9s must not be multiplied by 1000."""
        delim = MPRISPlayer.FORMAT_DELIMITER
        sub_ten_samples = [0.1, 0.5, 1.0, 2.5, 5.0, 7.5, 9.9]
        for sec in sub_ten_samples:
            pos_us = int(round(sec * 1_000_000))
            mock_output = (
                f"Playing{delim}Artist{delim}Title{delim}Album{delim}"
                f"200000000{delim}{pos_us}{delim}1.0{delim}None{delim}false{delim}art{delim}id1"
            )
            with patch.object(self.player, "_run_cmd", return_value=mock_output):
                state = self.player._get_state_playerctl()
                self.assertAlmostEqual(
                    state.position_seconds,
                    sec,
                    places=4,
                    msg=f"Expected {sec}s but got {state.position_seconds}s for {pos_us} us",
                )

    def test_playerctl_position_conversion_boundary_at_ten_seconds(self):
        """Regression test: boundary around 10s (9.99s, 10.0s, 10.01s) must convert smoothly without discontinuity."""
        delim = MPRISPlayer.FORMAT_DELIMITER
        boundary_samples = [9.99, 10.0, 10.01]
        for sec in boundary_samples:
            pos_us = int(round(sec * 1_000_000))
            mock_output = (
                f"Playing{delim}Artist{delim}Title{delim}Album{delim}"
                f"200000000{delim}{pos_us}{delim}1.0{delim}None{delim}false{delim}art{delim}id1"
            )
            with patch.object(self.player, "_run_cmd", return_value=mock_output):
                state = self.player._get_state_playerctl()
                self.assertAlmostEqual(state.position_seconds, sec, places=4)

    def test_playerctl_position_conversion_higher_positions(self):
        """Regression test: values at 30s, 60s, 120s must convert accurately."""
        delim = MPRISPlayer.FORMAT_DELIMITER
        higher_samples = [30.0, 60.0, 120.0]
        for sec in higher_samples:
            pos_us = int(round(sec * 1_000_000))
            mock_output = (
                f"Playing{delim}Artist{delim}Title{delim}Album{delim}"
                f"300000000{delim}{pos_us}{delim}1.0{delim}None{delim}false{delim}art{delim}id1"
            )
            with patch.object(self.player, "_run_cmd", return_value=mock_output):
                state = self.player._get_state_playerctl()
                self.assertAlmostEqual(state.position_seconds, sec, places=4)

    def test_duration_conversion_short_and_standard_tracks(self):
        """Regression test: duration conversion for short (<10s) and standard tracks in playerctl and D-Bus."""
        delim = MPRISPlayer.FORMAT_DELIMITER
        durations = [3.0, 5.0, 8.0, 9.9, 180.0, 240.0]
        for dur in durations:
            dur_us = int(round(dur * 1_000_000))
            # Test playerctl path
            mock_output = (
                f"Playing{delim}Artist{delim}Title_{dur}{delim}Album{delim}"
                f"{dur_us}{delim}1000000{delim}1.0{delim}None{delim}false{delim}art{delim}id_{dur}"
            )
            with patch.object(self.player, "_run_cmd", return_value=mock_output):
                state = self.player._get_state_playerctl()
                self.assertAlmostEqual(state.metadata.duration_seconds, dur, places=4)

            # Test native D-Bus properties path
            dbus_props = {
                "Metadata": {
                    "mpris:trackid": f"/org/mpris/track_{dur}",
                    "xesam:title": f"Song {dur}",
                    "xesam:artist": "Artist",
                    "mpris:length": dur_us,
                },
                "Position": 1_000_000,
            }
            self.player._apply_dbus_properties(dbus_props)
            self.assertAlmostEqual(self.player._last_state.metadata.duration_seconds, dur, places=4)

    def test_native_dbus_metadata_only_update_does_not_reset_position(self):
        """Regression test: metadata-only signals without Position must not reset interpolator position."""
        # 1. Initialize track
        self.player._apply_dbus_properties({
            "PlaybackStatus": "Playing",
            "Metadata": {
                "mpris:trackid": "/org/mpris/song1",
                "xesam:title": "Song 1",
                "xesam:artist": "Artist",
                "mpris:length": 180_000_000,
            },
            "Position": 0,
        })
        self.assertEqual(self.player._last_state.position_seconds, 0.0)

        # 2. Advance playback smoothly via interpolator to 15.0s
        self.player._interpolator.sync(
            position_seconds=15.0,
            status=PlaybackStatus.PLAYING,
            duration_seconds=180.0,
            is_authoritative=True,
            epoch=self.player._track_epoch,
        )
        self.assertAlmostEqual(self.player._interpolator.get_position(), 15.0, places=1)

        # 3. Metadata-only update arrives (artUrl or late metadata) with NO Position key
        self.player._apply_dbus_properties({
            "Metadata": {
                "mpris:trackid": "/org/mpris/song1",
                "xesam:title": "Song 1",
                "xesam:artist": "Artist",
                "mpris:length": 180_000_000,
                "mpris:artUrl": "https://example.com/cover.jpg",
            }
        })

        # Position must NOT have snapped back to 0.0!
        current_pos = self.player._interpolator.get_position()
        self.assertGreaterEqual(current_pos, 14.9)
        self.assertEqual(self.player._last_state.metadata.art_url, "https://example.com/cover.jpg")

    def test_track_transition_from_high_position_to_zero(self):
        """Regression test: track transition from 180s to new track at 0s clears stale position cleanly."""
        # Track 1 at 180s
        self.player._apply_dbus_properties({
            "PlaybackStatus": "Playing",
            "Metadata": {
                "mpris:trackid": "/org/mpris/song1",
                "xesam:title": "Song 1",
                "xesam:artist": "Artist",
                "mpris:length": 200_000_000,
            },
            "Position": 180_000_000,
        })
        initial_epoch = self.player._track_epoch
        self.assertEqual(self.player._last_state.position_seconds, 180.0)

        # Track 2 starts at 0s
        self.player._apply_dbus_properties({
            "Metadata": {
                "mpris:trackid": "/org/mpris/song2",
                "xesam:title": "Song 2",
                "xesam:artist": "Artist",
                "mpris:length": 210_000_000,
            },
            "Position": 0,
        })
        self.assertGreater(self.player._track_epoch, initial_epoch)
        self.assertEqual(self.player._last_state.position_seconds, 0.0)
        self.assertAlmostEqual(self.player._interpolator.get_position(), 0.0, places=1)

    def test_no_oscillation_during_first_ten_seconds_playback(self):
        """Regression test: playerctl successive poll snapshots during the first 10s must not oscillate."""
        delim = MPRISPlayer.FORMAT_DELIMITER
        # Track starts
        positions = [0.1, 0.5, 1.0, 2.0, 3.5, 5.0, 7.0, 9.0, 9.9, 10.5]
        last_pos = -1.0

        for sec in positions:
            pos_us = int(round(sec * 1_000_000))
            mock_output = (
                f"Playing{delim}Artist{delim}OscillationTestTrack{delim}Album{delim}"
                f"240000000{delim}{pos_us}{delim}1.0{delim}None{delim}false{delim}art{delim}track_osc"
            )
            with patch.object(self.player, "_run_cmd", return_value=mock_output):
                state = self.player._get_state_playerctl()
                interp_pos = self.player.get_interpolated_position()

                # Position must be close to actual seconds, never thousands or 100% full bar
                self.assertLess(state.position_seconds, 15.0)
                self.assertGreaterEqual(state.position_seconds, last_pos)
                self.assertLess(interp_pos, 15.0)
                last_pos = state.position_seconds

    def test_startup_playerctl_status_only_then_valid_metadata(self):
        """Test playerctl startup: initially status only (no metadata/duration), then valid metadata."""
        delim = MPRISPlayer.FORMAT_DELIMITER

        # 1. Startup: metadata fails, status command returns "Playing"
        with patch.object(self.player, "_run_cmd") as mock_cmd:
            def side_effect(cmd, **kwargs):
                if cmd and cmd[0] == "metadata":
                    return ""
                if cmd and cmd[0] == "status":
                    return "Playing"
                return ""
            mock_cmd.side_effect = side_effect

            state = self.player._get_state_playerctl()
            self.assertEqual(state.status, PlaybackStatus.PLAYING)
            self.assertEqual(state.metadata.duration_seconds, 0.0)
            # Interpolator must NOT advance phantom progress!
            self.assertEqual(self.player.get_interpolated_position(), 0.0)

        # 2. Next poll tick: valid metadata becomes available
        mock_output = (
            f"Playing{delim}Artist{delim}StartupSong{delim}Album{delim}"
            f"180000000{delim}15000000{delim}1.0{delim}None{delim}false{delim}art{delim}id_startup"
        )
        with patch.object(self.player, "_run_cmd", return_value=mock_output):
            state2 = self.player._get_state_playerctl()
            self.assertEqual(state2.metadata.title, "StartupSong")
            self.assertAlmostEqual(state2.metadata.duration_seconds, 180.0, places=1)
            self.assertAlmostEqual(state2.position_seconds, 15.0, places=1)
            self.assertAlmostEqual(self.player.get_interpolated_position(), 15.0, places=1)

    def test_native_dbus_metadata_without_position_triggers_async_fetch(self):
        """Test native D-Bus: metadata arriving without Position triggers async position fetch."""
        mock_props = MagicMock()
        mock_props.Get.return_value = 45_000_000  # 45.0s in microseconds
        self.player._props_iface = mock_props
        self.player.use_dbus = True

        # Metadata arrives without Position
        self.player._apply_dbus_properties({
            "PlaybackStatus": "Playing",
            "Metadata": {
                "mpris:trackid": "/org/mpris/track_async",
                "xesam:title": "AsyncSong",
                "xesam:artist": "Artist",
                "mpris:length": 240_000_000,
            }
        })

        # Wait for worker thread to process fetch_position
        self.player._cmd_queue.join()

        # Position should have been synchronized to 45.0s!
        self.assertAlmostEqual(self.player._last_state.position_seconds, 45.0, places=1)
        self.assertAlmostEqual(self.player._interpolator.get_position(), 45.0, places=1)
        self.assertAlmostEqual(self.player._last_state.metadata.duration_seconds, 240.0, places=1)

    def test_track_changes_while_async_position_request_pending(self):
        """Test track changes while an async position fetch is in-flight: stale position discarded."""
        mock_props = MagicMock()
        # Simulate slow D-Bus Get("Position") that returns track 1's position (100.0s)
        def delayed_get(iface, prop):
            time.sleep(0.05)
            return 100_000_000
        mock_props.Get.side_effect = delayed_get
        self.player._props_iface = mock_props
        self.player.use_dbus = True

        # Track 1 arrives without position
        self.player._apply_dbus_properties({
            "PlaybackStatus": "Playing",
            "Metadata": {
                "mpris:trackid": "/org/mpris/track1",
                "xesam:title": "Track 1",
                "xesam:artist": "Artist",
                "mpris:length": 200_000_000,
            }
        })
        epoch_track1 = self.player._track_epoch

        # Track 2 arrives immediately with known position 5.0s before worker finishes
        self.player._apply_dbus_properties({
            "PlaybackStatus": "Playing",
            "Metadata": {
                "mpris:trackid": "/org/mpris/track2",
                "xesam:title": "Track 2",
                "xesam:artist": "Artist",
                "mpris:length": 150_000_000,
            },
            "Position": 5_000_000,
        })
        epoch_track2 = self.player._track_epoch
        self.assertGreater(epoch_track2, epoch_track1)

        # Wait for worker queue to complete
        self.player._cmd_queue.join()

        # Position must be Track 2's position (5.0s), NOT overwritten by Track 1's delayed 100.0s!
        self.assertAlmostEqual(self.player._last_state.position_seconds, 5.0, places=1)
        self.assertAlmostEqual(self.player._interpolator.get_position(), 5.0, places=1)
        self.assertEqual(self.player._last_state.metadata.title, "Track 2")


class TestProgressBarWidget(unittest.TestCase):
    def test_format_time(self):
        try:
            from soulwave.ui.widgets.progress_bar import ProgressBarView
        except ImportError:
            return
        self.assertEqual(ProgressBarView._format_time(0), "00:00")
        self.assertEqual(ProgressBarView._format_time(65), "01:05")
        self.assertEqual(ProgressBarView._format_time(3665), "01:01:05")

    def test_calc_target_from_x(self):
        try:
            from soulwave.ui.widgets.progress_bar import ProgressBarView
        except ImportError:
            return
        pb = ProgressBarView()
        pb.position = 0.0
        pb.duration = 200.0
        t0 = pb._calc_target_from_x(6)
        self.assertAlmostEqual(t0, 0.0)

        t_mid = pb._calc_target_from_x(25)
        self.assertGreater(t_mid, 50.0)
        self.assertLess(t_mid, 150.0)

        t_end = pb._calc_target_from_x(50)
        self.assertAlmostEqual(t_end, 200.0)

    def test_render_with_duration(self):
        try:
            from soulwave.ui.widgets.progress_bar import ProgressBarView
        except ImportError:
            return
        pb = ProgressBarView()
        pb.update_progress(position=50.0, duration=100.0, accent=(56, 189, 248))
        rendered = pb.render()
        text = str(rendered)
        self.assertIn("00:50", text)
        self.assertIn("01:40", text)
        self.assertIn("●", text)
        self.assertIn("━", text)

    def test_render_with_zero_duration_stream_pulse(self):
        try:
            from soulwave.ui.widgets.progress_bar import ProgressBarView
        except ImportError:
            return
        pb = ProgressBarView()
        pb.update_progress(position=10.0, duration=0.0, accent=(56, 189, 248))
        rendered = pb.render()
        text = str(rendered)
        self.assertIn("00:10", text)
        self.assertIn("--:--", text)
        self.assertIn("●", text)


if __name__ == "__main__":
    unittest.main()
