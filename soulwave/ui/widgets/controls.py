"""Interactive playback controls and status indicators widget."""

from __future__ import annotations

from textual.widget import Widget
from textual.events import Click
from textual.message import Message
from rich.text import Text
from rich.style import Style

from ...player.base import PlayerState, PlaybackStatus, LoopStatus, ShuffleStatus
from ...theme.dynamic import RGB


class ControlsView(Widget):
    """Renders playback buttons and media status badges with mouse interaction."""

    DEFAULT_CSS = """
    ControlsView {
        height: 1;
        width: 100%;
        padding: 0 1;
        content-align: center middle;
    }
    """

    class ActionTriggered(Message):
        def __init__(self, action: str) -> None:
            super().__init__()
            self.action = action

    def __init__(
        self,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self.state: PlayerState = PlayerState()
        self.accent_color: RGB = (56, 189, 248)

    def update_state(self, state: PlayerState, accent: RGB) -> None:
        self.state = state
        self.accent_color = accent
        self.refresh()

    def render(self) -> Text:
        t = Text()
        btn_style = Style(color="rgb(248, 250, 252)", bgcolor="rgb(51, 65, 85)", bold=True)
        acc_btn = Style(
            color="rgb(15, 23, 42)",
            bgcolor=f"rgb({self.accent_color[0]},{self.accent_color[1]},{self.accent_color[2]})",
            bold=True,
        )
        dim_style = Style(color="rgb(148, 163, 184)")

        # Prev button
        t.append(" ⏮ Prev ", style=btn_style)
        t.append("  ")

        # Play/Pause button
        if self.state.status == PlaybackStatus.PLAYING:
            t.append(" ⏸ Pause ", style=acc_btn)
        else:
            t.append(" ▶ Play ", style=acc_btn)
        t.append("  ")

        # Next button
        t.append(" ⏭ Next ", style=btn_style)
        t.append("    ")

        # Volume
        vol_pct = int(self.state.volume * 100)
        vol_icon = "🔇" if vol_pct == 0 else ("🔉" if vol_pct < 50 else "🔊")
        t.append(f"{vol_icon} {vol_pct}%", style=Style(color="rgb(226, 232, 240)"))
        t.append("   ")

        # Shuffle
        shuffle_active = self.state.shuffle == ShuffleStatus.ON
        shuf_st = Style(color="rgb(56, 189, 248)", bold=True) if shuffle_active else dim_style
        t.append(f"🔀 {'On' if shuffle_active else 'Off'}", style=shuf_st)
        t.append("   ")

        # Loop
        loop_active = self.state.loop != LoopStatus.NONE
        loop_st = Style(color="rgb(56, 189, 248)", bold=True) if loop_active else dim_style
        t.append(f"🔁 {self.state.loop.value}", style=loop_st)

        return t

    def on_click(self, event: Click) -> None:
        """Handle clicks on controls."""
        # Simple coordinate-based button routing
        x = event.x
        if 2 <= x <= 12:
            self.post_message(self.ActionTriggered("previous"))
        elif 14 <= x <= 26:
            self.post_message(self.ActionTriggered("play_pause"))
        elif 28 <= x <= 38:
            self.post_message(self.ActionTriggered("next"))
        elif 50 <= x <= 62:
            self.post_message(self.ActionTriggered("shuffle"))
        elif 64 <= x <= 78:
            self.post_message(self.ActionTriggered("loop"))
