"""Smooth interactive progress bar widget with mouse scrub-and-release seeking support."""

from __future__ import annotations

from typing import Optional
from textual.widget import Widget
from textual.events import Click, MouseDown, MouseMove, MouseUp
from textual.message import Message
from rich.text import Text
from rich.style import Style

from ...theme.dynamic import RGB


class ProgressBarView(Widget):
    """Renders a smooth timeline bar with timestamp labels and click/drag-to-seek."""

    DEFAULT_CSS = """
    ProgressBarView {
        height: 1;
        width: 100%;
        padding: 0 1;
    }
    """

    class SeekRequested(Message):
        """Dispatched when the user clicks or releases a drag on the progress bar to seek."""
        def __init__(self, target_seconds: float) -> None:
            super().__init__()
            self.target_seconds = target_seconds

    def __init__(
        self,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self.position: float = 0.0
        self.duration: float = 0.0
        self.accent_color: RGB = (56, 189, 248)

        # Mouse scrubbing / coalescing state
        self._is_dragging: bool = False
        self._drag_target: Optional[float] = None
        self._just_released: bool = False

    def update_progress(self, position: float, duration: float, accent: RGB) -> None:
        self.position = max(0.0, position)
        self.duration = max(0.0, duration)
        self.accent_color = accent
        self.refresh()

    @staticmethod
    def _format_time(seconds: float) -> str:
        mins = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{mins:02d}:{secs:02d}"

    def _calc_target_from_x(self, x: int) -> Optional[float]:
        if self.duration <= 0.0:
            return None

        pos_str_len = 6  # "00:00 "
        width = self.size.width if self.size.width > 0 else 50
        bar_len = max(10, width - 12 - 2)
        click_x = x - pos_str_len

        ratio = max(0.0, min(1.0, click_x / float(bar_len)))
        return ratio * self.duration

    def render(self) -> Text:
        t = Text()
        width = self.size.width if self.size.width > 0 else 50

        # Display drag position during mouse scrubbing for immediate 0ms feedback
        display_pos = (
            self._drag_target
            if (self._is_dragging and self._drag_target is not None)
            else self.position
        )

        pos_str = self._format_time(display_pos)
        dur_str = self._format_time(self.duration) if self.duration > 0.0 else "--:--"

        prefix = f"{pos_str} "
        suffix = f" {dur_str}"
        bar_len = max(10, width - len(prefix) - len(suffix) - 2)

        t.append(prefix, style=Style(color="rgb(148, 163, 184)"))

        ratio = 0.0 if self.duration <= 0.0 else min(1.0, display_pos / self.duration)
        filled_len = int(round(ratio * bar_len))
        empty_len = max(0, bar_len - filled_len)

        fill_col = f"rgb({self.accent_color[0]},{self.accent_color[1]},{self.accent_color[2]})"
        empty_col = "rgb(51, 65, 85)"
        thumb_col = "rgb(255, 255, 255)"

        if filled_len > 0:
            t.append("━" * (filled_len - 1), style=Style(color=fill_col))
            t.append("●", style=Style(color=thumb_col, bold=True))
        else:
            t.append("○", style=Style(color=fill_col))

        if empty_len > 0:
            t.append("─" * empty_len, style=Style(color=empty_col))

        t.append(suffix, style=Style(color="rgb(148, 163, 184)"))
        return t

    def on_mouse_down(self, event: MouseDown) -> None:
        """Begin mouse scrubbing without dispatching D-Bus seek calls."""
        if self.duration <= 0:
            return
        target = self._calc_target_from_x(event.x)
        if target is not None:
            self._is_dragging = True
            self._drag_target = target
            self.capture_mouse()
            self.refresh()

    def on_mouse_move(self, event: MouseMove) -> None:
        """Update visual thumb continuously during drag without calling D-Bus."""
        if self._is_dragging:
            target = self._calc_target_from_x(event.x)
            if target is not None:
                self._drag_target = target
                self.refresh()

    def on_mouse_up(self, event: MouseUp) -> None:
        """Coalesce mouse movement into a single absolute seek on release."""
        if self._is_dragging:
            self._is_dragging = False
            self.release_mouse()
            target = self._calc_target_from_x(event.x)
            if target is None:
                target = self._drag_target
            if target is not None:
                self.position = target
                self._just_released = True
                self.post_message(self.SeekRequested(target))
            self._drag_target = None
            self.refresh()

    def on_click(self, event: Click) -> None:
        """Fallback for mouse click if not handled by mouse_up."""
        if self._just_released:
            self._just_released = False
            return
        if self.duration <= 0:
            return
        target = self._calc_target_from_x(event.x)
        if target is not None:
            self.position = target
            self.post_message(self.SeekRequested(target))
            self.refresh()
