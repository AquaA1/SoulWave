from __future__ import annotations

import time
from typing import Callable, List, Optional
from textual.widget import Widget
from rich.text import Text
from rich.style import Style

from ...lyrics.parser import LRCParser, LyricLine
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
        self.offset_seconds: float = 0.0
        self.current_position: float = 0.0
        self.duration_seconds: float = 0.0
        self.accent_color: RGB = (56, 189, 248)

        # No-lyrics countdown and fallback dance state
        self.is_countdown_active: bool = False
        self.countdown_seconds: int = 5
        self._countdown_start_time: Optional[float] = None
        self._on_countdown_complete: Optional[Callable[[], None]] = None
        self._dance_fallback_active: bool = False
        self._companion_view: Optional[CompanionDanceView] = None

        # Replay prevention state
        self._has_reached_end: bool = False

    def start_no_lyrics_countdown(
        self,
        on_complete: Optional[Callable[[], None]] = None,
        countdown_seconds: int = 5,
    ) -> None:
        """Starts a visible smooth countdown before switching to the mascot dance."""
        self.cancel_countdown()
        self.is_loading = False
        self.lines = []
        self.plain_text = None
        self.is_countdown_active = True
        self.countdown_seconds = countdown_seconds
        self._countdown_start_time = time.monotonic()
        self._on_countdown_complete = on_complete
        self._dance_fallback_active = False
        self._has_reached_end = False
        self.refresh()

    def cancel_countdown(self) -> None:
        """Cancels any pending no-lyrics countdown."""
        self.is_countdown_active = False
        self._countdown_start_time = None
        self._on_countdown_complete = None
        self.countdown_seconds = 5
        self.refresh()

    def set_lyrics(
        self,
        synced_lrc: str | None,
        plain_lyrics: str | None,
        offset: float = 0.0,
        duration: float = 0.0,
    ) -> None:
        self.cancel_countdown()
        self._dance_fallback_active = False
        self._has_reached_end = False
        self.offset_seconds = offset
        self.is_loading = False
        if duration > 0.0:
            self.duration_seconds = duration
        if synced_lrc:
            self.lines = LRCParser.parse(synced_lrc)
            self.plain_text = None
        elif plain_lyrics:
            self.lines = []
            self.plain_text = plain_lyrics
        else:
            self.lines = []
            self.plain_text = None
        self.refresh()

    def set_loading(self) -> None:
        self.cancel_countdown()
        self._dance_fallback_active = False
        self._has_reached_end = False
        self.is_loading = True
        self.lines = []
        self.plain_text = None
        self.refresh()

    def update_position(self, pos: float, accent: RGB, duration: float = 0.0) -> None:
        self.current_position = max(0.0, pos)
        self.accent_color = accent
        if duration > 0.0:
            self.duration_seconds = duration

        # Progress countdown if active
        if self.is_countdown_active and self._countdown_start_time is not None:
            elapsed = time.monotonic() - self._countdown_start_time
            rem = max(1, 5 - int(elapsed))
            if elapsed >= 5.0:
                self.is_countdown_active = False
                self._dance_fallback_active = True
                cb = self._on_countdown_complete
                self._on_countdown_complete = None
                if cb:
                    cb()
            elif rem != self.countdown_seconds:
                self.countdown_seconds = rem

        # Animate fallback mascot if active
        if self._dance_fallback_active:
            if not self._companion_view:
                self._companion_view = CompanionDanceView()
            self._companion_view.update_state(
                is_playing=True,
                is_paused=False,
                accent=self.accent_color,
                energy=0.5,
            )

        self.refresh()

    def adjust_offset(self, delta: float) -> float:
        self.offset_seconds = round(self.offset_seconds + delta, 2)
        self.refresh()
        return self.offset_seconds

    def render(self) -> Text:
        t = Text()
        height = max(5, getattr(self, "_test_height", self.size.height if self.size.height > 0 else 12))
        max_visible_lines = height

        # 1. Dance fallback state
        if self._dance_fallback_active:
            if not self._companion_view:
                self._companion_view = CompanionDanceView()
            if hasattr(self, "_test_height"):
                self._companion_view._test_height = self._test_height
            if hasattr(self, "_test_width"):
                self._companion_view._test_width = getattr(self, "_test_width", 40)
            return self._companion_view.render()

        # 2. Loading state
        if self.is_loading:
            t.append("── LYRICS ──\n", style=Style(color="rgb(100, 116, 139)"))
            t.append("\n  ✨ Looking up lyrics via syncedlyrics...", style=Style(color="rgb(148, 163, 184)"))
            return t

        # 3. No-lyrics countdown state
        if self.is_countdown_active:
            t.append("── NO LYRICS ──\n\n", style=Style(color="rgb(244, 114, 182)", bold=True))
            t.append("  No lyrics found for this track ♡\n", style=Style(color="rgb(251, 207, 232)", bold=True))
            t.append("  Take a little break and enjoy a dance with our Soul Souls!\n\n", style=Style(color="rgb(203, 213, 225)"))
            acc_str = f"rgb({self.accent_color[0]},{self.accent_color[1]},{self.accent_color[2]})"
            t.append("  The Soul Souls are getting ready to dance... ", style=Style(color="rgb(148, 163, 184)"))
            t.append(f"{self.countdown_seconds}\n", style=Style(color=acc_str, bold=True))
            return t

        # 4. Empty lyrics with no active countdown
        if not self.lines and not self.plain_text:
            t.append("── LYRICS ──\n", style=Style(color="rgb(100, 116, 139)"))
            t.append("\n  ♪ (No lyrics found for this track)", style=Style(color="rgb(100, 116, 139)"))
            return t

        # 5. Synchronized LRC lyrics
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

        return t
