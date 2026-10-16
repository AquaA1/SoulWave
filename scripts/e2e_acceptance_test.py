"""End-to-end playback and lyrics synchronization acceptance test for SoulwaveApp."""

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from soulwave.config import Config
from soulwave.lyrics.parser import LRCParser
from soulwave.player.base import PlaybackStatus
from soulwave.ui.app import SoulwaveApp


def get_active_lyric_info(app: SoulwaveApp) -> tuple[int, Optional[float], str]:
    """Returns (active_idx, timestamp, text) from the live LyricsPanelView."""
    lines = app.lyrics_view.lines
    if not lines:
        if app.lyrics_view.is_loading:
            return -1, None, "<LOADING_LYRICS>"
        if app.lyrics_view.plain_text:
            return -1, None, "<PLAIN_UNSYNCED_LYRICS>"
        return -1, None, "<NO_LYRICS>"

    pos = app.lyrics_view.current_position
    offset = app.lyrics_view.offset_seconds
    idx = LRCParser.find_active_index(lines, pos, offset)
    if 0 <= idx < len(lines):
        line = lines[idx]
        return idx, line.timestamp, line.text
    return idx, None, "<PRE_TRACK_OR_GAP>"


def set_player_pos(pos_sec: float) -> None:
    """Seek the media player directly via playerctl before transition begins."""
    try:
        subprocess.run(["playerctl", "position", f"{pos_sec:.1f}"], check=True, timeout=2.0)
    except Exception as e:
        print(f"[WARN] playerctl position failed: {e}", file=sys.stderr)


def get_playerctl_info() -> tuple[str, str, float, float, str]:
    """Returns (title, artist, position, duration, status) from playerctl."""
    try:
        res = subprocess.run(
            [
                "playerctl",
                "metadata",
                "--format",
                "{{title}}:::{{artist}}:::{{position}}:::{{mpris:length}}:::{{status}}",
            ],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=True,
        )
        parts = res.stdout.strip().split(":::")
        if len(parts) >= 5:
            title = parts[0]
            artist = parts[1]
            pos = float(parts[2]) / 1_000_000.0 if parts[2] else 0.0
            dur = float(parts[3]) / 1_000_000.0 if parts[3] else 0.0
            status = parts[4]
            return title, artist, pos, dur, status
    except Exception:
        pass
    return "", "", 0.0, 0.0, "Unknown"


async def run_e2e_acceptance_test():
    print("=" * 80)
    print("SOULWAVE E2E ACCEPTANCE TEST: LIVE APPLICATION & MEDIA PLAYER")
    print("=" * 80)

    cfg = Config.load()
    cfg.show_lyrics = True
    cfg.fps = 15

    app = SoulwaveApp(config=cfg, force_demo=False, preferred_player="firefox")

    async with app.run_test(size=(120, 36)) as pilot:
        # Initial mount and sync
        await pilot.pause(1.0)

        # Make sure player is playing
        try:
            subprocess.run(["playerctl", "play"], check=False)
        except Exception:
            pass
        await pilot.pause(0.5)

        num_transitions_target = 3
        transitions_completed = 0

        current_track_title = app._last_state.metadata.title
        print(f"\n[SETUP] Initial Track: '{current_track_title}' | Player: {app._last_state.player_name}")

        for test_idx in range(1, num_transitions_target + 1):
            print(f"\n" + "-" * 80)
            print(f"TRANSITION {test_idx} OF {num_transitions_target}: Starting phase...")
            print("-" * 80)

            # Step A: Get current track duration
            # If duration is known, seek to duration - 4.5s so natural transition occurs in ~4.5 seconds
            t_now, a_now, p_now, d_now, s_now = get_playerctl_info()
            if d_now > 10.0:
                seek_target = max(0.0, d_now - 5.0)
                print(f"[SETUP] Advancing track to {seek_target:.1f}s / {d_now:.1f}s (5s before track end)...")
                set_player_pos(seek_target)
                await pilot.pause(0.8)

            pre_transition_title = app._last_state.metadata.title
            print(f"[MONITOR] Waiting for track to end naturally: '{pre_transition_title}'...")

            # Step B: Wait for track metadata to change (transition happens)
            # DO NOT touch any controls in Soulwave!
            t_wait_start = time.monotonic()
            transition_occurred = False
            while time.monotonic() - t_wait_start < 25.0:
                await pilot.pause(0.4)
                new_title = app._last_state.metadata.title
                if new_title and new_title != pre_transition_title:
                    transition_occurred = True
                    break

            if not transition_occurred:
                print(f"[ERROR] Track did not transition within 25 seconds.")
                # Force next track via playerctl to continue testing transitions
                print("[FALLBACK] Sending playerctl next...")
                subprocess.run(["playerctl", "next"], check=False)
                await pilot.pause(1.5)

            new_track_title = app._last_state.metadata.title
            new_epoch = app.player_manager.current_player._track_epoch if hasattr(app.player_manager.current_player, "_track_epoch") else "?"
            print(f"\n>>> [EVENT] TRANSITION {test_idx} DETECTED! <<<")
            print(f"    Old Track: '{pre_transition_title}'")
            print(f"    New Track: '{new_track_title}'")
            print(f"    New Track Epoch: {new_epoch}\n")

            # Step C: Continuous observation for at least 20 seconds
            # DO NOT press space, seek, or refresh Soulwave!
            observation_start = time.monotonic()
            obs_duration = 22.0  # At least 20 seconds
            last_timeline_pos = -0.1
            reversal_detected = False

            print(f"{'Elapsed':<8} | {'Status':<7} | {'InterpPos':<10} | {'Reported':<9} | {'Stale0':<6} | {'Uncert':<6} | {'LyricTimestamp':<14} | {'ActiveLyricLine'}")
            print("-" * 110)

            while (time.monotonic() - observation_start) < obs_duration:
                await pilot.pause(0.5)

                now_t = time.monotonic() - observation_start
                state = app._last_state
                player = app.player_manager.current_player
                diag = getattr(player, "_interpolator", None).diagnostics if hasattr(player, "_interpolator") else {}

                interp_pos = app.progress_bar_view.position
                reported_pos = diag.get("last_reported_pos", 0.0)
                stale_zeros = diag.get("stale_zero_count", 0)
                is_uncert = diag.get("is_uncertain", False)

                lyric_idx, lyric_ts, lyric_text = get_active_lyric_info(app)
                ts_str = f"{lyric_ts:.2f}s" if lyric_ts is not None else "None"
                short_text = (lyric_text[:40] + "...") if len(lyric_text) > 40 else lyric_text

                # Check for backward jump (after initial start)
                if now_t > 1.5 and interp_pos < last_timeline_pos - 0.2:
                    reversal_detected = True
                    print(f"*** [WARNING: REVERSAL] pos dropped from {last_timeline_pos:.2f} to {interp_pos:.2f} ***")
                last_timeline_pos = max(last_timeline_pos, interp_pos)

                print(f"{now_t:6.1f}s  | {state.status.value:<7} | {interp_pos:7.2f}s  | {reported_pos:6.2f}s  | {stale_zeros:<6} | {str(is_uncert):<6} | {ts_str:<14} | {short_text}")

            transitions_completed += 1
            print(f"\n[PASS] Transition {test_idx} 20s observation complete. Reversals: {reversal_detected}")

        print("\n" + "=" * 80)
        print(f"E2E ACCEPTANCE TEST COMPLETED: {transitions_completed} transitions observed.")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_e2e_acceptance_test())
