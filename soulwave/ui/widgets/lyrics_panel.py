"""Synchronized scrolling lyrics panel widget."""

from __future__ import annotations

from typing import List, Optional
from textual.widget import Widget
from rich.text import Text
from rich.style import Style

from ...lyrics.parser import LRCParser, LyricLine
from ...theme.dynamic import RGB


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
        self.accent_color: RGB = (56, 189, 248)

    def set_lyrics(
        self,
        synced_lrc: str | None,
        plain_lyrics: str | None,
        offset: float = 0.0,
    ) -> None:
        self.offset_seconds = offset
        self.is_loading = False
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
        self.is_loading = True
        self.lines = []
        self.plain_text = None
        self.refresh()

    def update_position(self, pos: float, accent: RGB) -> None:
        self.current_position = pos
        self.accent_color = accent
        self.refresh()

    def adjust_offset(self, delta: float) -> float:
        self.offset_seconds = round(self.offset_seconds + delta, 2)
        self.refresh()
        return self.offset_seconds

    def render(self) -> Text:
        t = Text()
        height = max(5, self.size.height)
        max_visible_lines = height

        if self.lines:
            # Header bar showing synced lyrics & offset
            offset_ms = int(round(self.offset_seconds * 1000))
            offset_badge = f" [Offset: {offset_ms:+d}ms]" if offset_ms != 0 else ""
            t.append(f"── SYNCED LYRICS{offset_badge} ──\n", style=Style(color="rgb(100, 116, 139)"))
        elif self.plain_text:
            # Header explicitly marking unsynchronized lyrics
            t.append("── PLAIN LYRICS (UNSYNCHRONIZED) ──\n", style=Style(color="rgb(245, 158, 11)", bold=True))
        else:
            t.append("── LYRICS ──\n", style=Style(color="rgb(100, 116, 139)"))

        if self.is_loading:
            t.append("\n  ✨ Looking up lyrics via syncedlyrics...", style=Style(color="rgb(148, 163, 184)"))
            return t

        if not self.lines and not self.plain_text:
            t.append("\n  ♪ (No lyrics found for this track)", style=Style(color="rgb(100, 116, 139)"))
            return t

        if self.lines:
            active_idx = LRCParser.find_active_index(self.lines, self.current_position, self.offset_seconds)

            # Center active line in available space
            half = (max_visible_lines - 2) // 2
            start_idx = max(0, active_idx - half)
            end_idx = min(len(self.lines), start_idx + max_visible_lines - 2)

            # Re-adjust start_idx if near bottom
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

                if idx == active_idx:
                    t.append(f" ▸ {line_str}\n", style=acc_style)
                elif idx < active_idx:
                    t.append(f"   {line_str}\n", style=past_style)
                else:
                    t.append(f"   {line_str}\n", style=future_style)

        elif self.plain_text:
            plain_lines = [l.strip() for l in self.plain_text.splitlines() if l.strip()]
            for l in plain_lines[:max_visible_lines - 2]:
                t.append(f"   {l}\n", style=Style(color="rgb(203, 213, 225)"))

        return t
