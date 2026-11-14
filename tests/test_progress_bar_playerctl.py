"""Unit and integration tests for progress bar and playerctl MPRIS fallback."""

import unittest
from unittest.mock import MagicMock, patch

from soulwave.player.base import PlaybackStatus, PlayerState, TrackMetadata
from soulwave.player.mpris import MPRISPlayer
from soulwave.player.interpolator import PositionInterpolator


class TestProgressBarPlayerctl(unittest.TestCase):
    def setUp(self):
        self.player = MPRISPlayer(player_name="org.mpris.MediaPlayer2.spotify", use_dbus=False)
        self.player._playerctl_bin = "/usr/bin/playerctl"

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

    def test_get_state_playerctl_handles_microseconds_and_seconds(self):
        delim = MPRISPlayer.FORMAT_DELIMITER
        # Case 1: position in microseconds
        out_us = (
            f"Playing{delim}Artist{delim}Title{delim}Album{delim}"
            f"100000000{delim}50000000{delim}1.0{delim}None{delim}false{delim}{delim}"
        )
        with patch.object(self.player, "_run_cmd", return_value=out_us):
            state = self.player._get_state_playerctl()
            self.assertAlmostEqual(state.position_seconds, 50.0)
            self.assertAlmostEqual(state.metadata.duration_seconds, 100.0)

        # Case 2: position in seconds
        out_sec = (
            f"Playing{delim}Artist{delim}Title{delim}Album{delim}"
            f"100.0{delim}50.0{delim}1.0{delim}None{delim}false{delim}{delim}"
        )
        with patch.object(self.player, "_run_cmd", return_value=out_sec):
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
            mock_cmd.assert_called_with(["position", "5.0+"])

        # Backward seek (-5s) must pass "5.0-" NOT "-5.0"
        with patch.object(self.player, "_run_cmd") as mock_cmd:
            self.player._last_state.status = PlaybackStatus.PLAYING
            self.player._last_state.metadata.duration_seconds = 100.0
            self.player._last_state.can_seek = True

            self.player.seek(-5.0)
            mock_cmd.assert_called_with(["position", "5.0-"])

    def test_set_position_works_without_track_id_in_cli_mode(self):
        with patch.object(self.player, "_run_cmd") as mock_cmd:
            self.player._last_state.status = PlaybackStatus.PLAYING
            self.player._last_state.metadata.duration_seconds = 180.0
            self.player._last_state.metadata.track_id = ""  # No track ID
            self.player._last_state.can_seek = True

            self.player.set_position(90.0)
            mock_cmd.assert_called_with(["position", "90.0"])


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
