from __future__ import annotations

import time
from typing import Callable, List, Optional
from textual.widget import Widget
from rich.text import Text
from rich.style import Style

from ...lyrics.parser import LRCParser, LyricLine
from ...player.mpris import is_mpris_available, get_playerctl_install_hint
from ...theme.dynamic import RGB
from .companion_view import CompanionDanceView


class LyricsPanelView(Widget):
    """Displays smoothly scrolling synced lyrics centered on current playback time."""

    DEFAULT_CSS = """
    LyricsPanelView {
        height: 100%;
        width: 100%;
        padding: 0 1;
        content-align: center middle;
    }
    """

    def __init__(
        self,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self.lines: List[LyricLine] = []
        self.plain_text: Optional[str] = None
        self.is_loading: bool = False
        self.is_searching: bool = False
        self.is_waiting: bool = False
        self.status_message: Optional[str] = None
        self._not_found_timestamp: Optional[float] = None
        self._not_found_duration: float = 2.5
        self.offset_seconds: float = 0.0
        self.current_position: float = 0.0
        self.duration_seconds: float = 0.0
        self.accent_color: RGB = (56, 189, 248)

        # Persistent fallback companion dance view
        self._companion_view: CompanionDanceView = CompanionDanceView()
        self._dance_fallback_active: bool = True

        # Countdown compatibility state
        self.is_countdown_active: bool = False
        self.countdown_seconds: int = 5
        self._countdown_start_time: Optional[float] = None
        self._on_countdown_complete: Optional[Callable[[], None]] = None

        # Replay prevention state
        self._has_reached_end: bool = False

    def start_no_lyrics_countdown(
        self,
        on_complete: Optional[Callable[[], None]] = None,
        countdown_seconds: int = 5,
    ) -> None:
        """Starts fallback dance (compatibility helper)."""
        self.set_not_found(duration=float(countdown_seconds))
        if on_complete:
            on_complete()

    def cancel_countdown(self) -> None:
        """Cancels any pending countdown or status message timer."""
        self.is_countdown_active = False
        self._countdown_start_time = None
        self._on_countdown_complete = None
        self.countdown_seconds = 5

    def set_searching(self) -> None:
        """Immediately displays the group dance animation while searching for lyrics."""
        self.cancel_countdown()
        self._has_reached_end = False
        self.is_loading = True
        self.is_searching = True
        self.is_waiting = False
        self.status_message = "SEARCHING FOR LYRICS..."
        self._not_found_timestamp = None
        self.lines = []
        self.plain_text = None
        self._companion_view.status_message = self.status_message
        self._companion_view.status_subtitle = None
        self.refresh()

    def set_loading(self) -> None:
        """Immediately displays group dance with searching indicator."""
        self.set_searching()

    def set_not_found(self, duration: float = 2.5, status_text: str = "LYRICS NOT FOUND") -> None:
        """Briefly displays 'LYRICS NOT FOUND' at the top, then continues the group dance."""
        self.cancel_countdown()
        self._has_reached_end = False
        self.is_loading = False
        self.is_searching = False
        self.is_waiting = False
        self.lines = []
        self.plain_text = None
        self.status_message = status_text
        self._not_found_timestamp = time.monotonic() + duration
        self._companion_view.status_message = self.status_message
        self._companion_view.status_subtitle = "(No lyrics found for this track)"
        self.refresh()

    def set_lyrics(
        self,
        synced_lrc: str | None,
        plain_lyrics: str | None,
        offset: float = 0.0,
        duration: float = 0.0,
    ) -> None:
        self.cancel_countdown()
        self._has_reached_end = False
        self.offset_seconds = offset
        self.is_loading = False
        self.is_searching = False
        self._not_found_timestamp = None
        if duration > 0.0:
            self.duration_seconds = duration

        if synced_lrc:
            self.lines = LRCParser.parse(synced_lrc)
            self.plain_text = None
            self.status_message = None
            self._companion_view.status_message = None
            self._companion_view.status_subtitle = None
        elif plain_lyrics:
            self.lines = []
            self.plain_text = plain_lyrics
            self.status_message = None
            self._companion_view.status_message = None
            self._companion_view.status_subtitle = None
        else:
            self.lines = []
            self.plain_text = None
            if not self.is_waiting:
                self.set_not_found()
            else:
                self.status_message = None
                self._companion_view.status_message = None
                self._companion_view.status_subtitle = None
        self.refresh()

    def update_position(
        self,
        pos: float,
        accent: RGB,
        duration: float = 0.0,
        is_playing: bool = True,
        is_paused: bool = False,
        energy: float = 0.0,
    ) -> None:
        self.current_position = max(0.0, pos)
        self.accent_color = accent
        if duration > 0.0:
            self.duration_seconds = duration

        # Auto-hide LYRICS NOT FOUND after specified duration (around 2-3 seconds)
        if self._not_found_timestamp is not None:
            if time.monotonic() >= self._not_found_timestamp:
                self._not_found_timestamp = None
                if self.status_message and "NOT FOUND" in self.status_message.upper():
                    self.status_message = None
                    self._companion_view.status_message = None
                    self._companion_view.status_subtitle = None

        # When lyrics are not available, update and animate companion dance view
        if not self.lines and not self.plain_text:
            self._companion_view.status_message = self.status_message
            self._companion_view.update_state(
                is_playing=is_playing,
                is_paused=is_paused,
                accent=self.accent_color,
                energy=energy,
            )

        self.refresh()

    def adjust_offset(self, delta: float) -> float:
        self.offset_seconds = round(self.offset_seconds + delta, 2)
        self.refresh()
        return self.offset_seconds

    def render(self) -> Text:
        t = Text()
        height = max(5, getattr(self, "_test_height", self.size.height if self.size.height > 0 else 12))
        width = max(24, getattr(self, "_test_width", self.size.width if self.size.width > 0 else 40))
        max_visible_lines = height

        # 1. Cold-start waiting state (no track playing on system)
        if self.is_waiting and not self.lines and not self.plain_text and not self.is_searching:
            t.append("── LYRICS ──\n", style=Style(color="rgb(100, 116, 139)"))
            if not is_mpris_available():
                hint = get_playerctl_install_hint()
                t.append("\n  ⚠️ 'playerctl' utility not found\n\n", style=Style(color="rgb(245, 158, 11)", bold=True))
                t.append("  Soulwave needs 'playerctl' to track songs and fetch lyrics.\n", style=Style(color="rgb(203, 213, 225)"))
                t.append(f"  To install: {hint}\n\n", style=Style(color="rgb(56, 189, 248)", bold=True))
                t.append("  (Or press 'd' to switch to built-in demo tracks with synced lyrics!)", style=Style(color="rgb(148, 163, 184)"))
            else:
                t.append("\n  🎧 Waiting for media playback...\n\n", style=Style(color="rgb(148, 163, 184)", bold=True))
                t.append("  Start playing a song in Spotify, YouTube, or your media player", style=Style(color="rgb(100, 116, 139)"))
            return t

        # 2. Synchronized LRC lyrics
        if self.lines:
            offset_ms = int(round(self.offset_seconds * 1000))
            offset_badge = f" [Offset: {offset_ms:+d}ms]" if offset_ms != 0 else ""
            t.append(f"── SYNCED LYRICS{offset_badge} ──\n", style=Style(color="rgb(100, 116, 139)"))

            active_idx = LRCParser.find_active_index(self.lines, self.current_position, self.offset_seconds)

            # Prevent replaying: when playback passes the final timestamp, keep final line displayed
            last_timestamp = self.lines[-1].timestamp
            adjusted_pos = self.current_position + self.offset_seconds

            if adjusted_pos >= last_timestamp:
                self._has_reached_end = True
                active_idx = len(self.lines) - 1
            elif self._has_reached_end:
                # If previously ended, only un-freeze if user seeks backward significantly
                if adjusted_pos < last_timestamp - 1.5:
                    self._has_reached_end = False
                else:
                    active_idx = len(self.lines) - 1

            is_intro = (active_idx < 0)
            center_idx = 0 if is_intro else active_idx

            # Center active line in available space
            half = (max_visible_lines - 2) // 2
            start_idx = max(0, center_idx - half)
            end_idx = min(len(self.lines), start_idx + max_visible_lines - 2)

            if end_idx - start_idx < max_visible_lines - 2:
                start_idx = max(0, end_idx - (max_visible_lines - 2))

            acc_style = Style(
                color=f"rgb({self.accent_color[0]},{self.accent_color[1]},{self.accent_color[2]})",
                bold=True,
            )
            past_style = Style(color="rgb(100, 116, 139)")
            future_style = Style(color="rgb(148, 163, 184)")

            for idx in range(start_idx, end_idx):
                line = self.lines[idx]
                line_str = line.text if line.text else " "

                if not is_intro and idx == active_idx:
                    t.append(f" ▸ {line_str}\n", style=acc_style)
                elif not is_intro and idx < active_idx:
                    t.append(f"   {line_str}\n", style=past_style)
                else:
                    t.append(f"   {line_str}\n", style=future_style)

        # 6. Plain-text unsynchronized lyrics
        elif self.plain_text:
            t.append("── PLAIN LYRICS (UNSYNCHRONIZED) ──\n", style=Style(color="rgb(245, 158, 11)", bold=True))
            plain_lines = [l.strip() for l in self.plain_text.splitlines() if l.strip()]
            if not plain_lines:
                t.append("\n  ♪ (No lyrics found for this track)", style=Style(color="rgb(100, 116, 139)"))
                return t

            # Map current position to approximate reading progress fraction
            if self.duration_seconds > 0.0:
                progress_fraction = min(1.0, max(0.0, self.current_position / self.duration_seconds))
            else:
                est_total = max(1.0, len(plain_lines) * 4.0)
                progress_fraction = min(1.0, max(0.0, self.current_position / est_total))

            # Prevent replaying: once end is reached, stop advancing and stay on final line
            if progress_fraction >= 1.0:
                self._has_reached_end = True
                active_idx = len(plain_lines) - 1
            elif self._has_reached_end:
                if progress_fraction < 0.95:
                    self._has_reached_end = False
                    active_idx = int(round(progress_fraction * (len(plain_lines) - 1)))
                else:
                    active_idx = len(plain_lines) - 1
            else:
                active_idx = int(round(progress_fraction * (len(plain_lines) - 1)))

            active_idx = max(0, min(len(plain_lines) - 1, active_idx))

            # Center active reading line in available space
            half = (max_visible_lines - 2) // 2
            start_idx = max(0, active_idx - half)
            end_idx = min(len(plain_lines), start_idx + max_visible_lines - 2)

            if end_idx - start_idx < max_visible_lines - 2:
                start_idx = max(0, end_idx - (max_visible_lines - 2))

            acc_style = Style(
                color=f"rgb({self.accent_color[0]},{self.accent_color[1]},{self.accent_color[2]})",
                bold=True,
            )
            past_style = Style(color="rgb(100, 116, 139)")
            future_style = Style(color="rgb(203, 213, 225)")

            for idx in range(start_idx, end_idx):
                line_str = plain_lines[idx]
                if idx == active_idx:
                    t.append(f" ▸ {line_str}\n", style=acc_style)
                elif idx < active_idx:
                    t.append(f"   {line_str}\n", style=past_style)
                else:
                    t.append(f"   {line_str}\n", style=future_style)

        else:
            # 3. Permanent Fallback: Group Dance Animation (when lyrics are not available, searching, or not found)
            self._companion_view._test_height = height
            self._companion_view._test_width = width
            self._companion_view.status_message = self.status_message
            return self._companion_view.render()

        return t
