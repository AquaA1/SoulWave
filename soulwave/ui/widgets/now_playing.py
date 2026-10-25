"""Now playing metadata display widget."""

from __future__ import annotations

from textual.widget import Widget
from rich.text import Text
from rich.style import Style

from ...player.base import PlayerState, PlaybackStatus
from ...theme.dynamic import RGB


class NowPlayingView(Widget):
    """Displays current track title, artist, album, and player badge."""

    DEFAULT_CSS = """
    NowPlayingView {
        height: auto;
        padding: 0 1;
        content-align: left middle;
    }
    """

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
        acc_style = Style(color=f"rgb({self.accent_color[0]},{self.accent_color[1]},{self.accent_color[2]})", bold=True)
        dim_style = Style(color="rgb(148, 163, 184)")
        badge_style = Style(color="rgb(248, 250, 252)", bgcolor="rgb(51, 65, 85)", bold=True)

        # Player badge and status
        is_disconnected = self.state.status == PlaybackStatus.DISCONNECTED
        player_name = self.state.player_name or "None"
        if is_disconnected and (not player_name or player_name == "None"):
            badge_name = "WAITING"
            status_text = " ○ SEARCHING FOR PLAYER "
            status_style = Style(color="rgb(148, 163, 184)", bold=True)
        elif self.state.status == PlaybackStatus.PLAYING:
            badge_name = player_name.upper()
            status_text = " ▶ PLAYING "
            status_style = Style(color="rgb(34, 197, 94)", bold=True)
        elif self.state.status == PlaybackStatus.PAUSED:
            badge_name = player_name.upper()
            status_text = " ⏸ PAUSED "
            status_style = Style(color="rgb(251, 191, 36)", bold=True)
        else:
            badge_name = player_name.upper()
            status_text = f" ■ {self.state.status.value.upper()} "
            status_style = Style(color="rgb(148, 163, 184)", bold=True)

        t.append(f" {badge_name} ", style=badge_style)
        t.append(" ")
        t.append(status_text, style=status_style)
        t.append("\n\n")

        # Track title and metadata
        if is_disconnected or not self.state.metadata.title or self.state.metadata.title == "No Track Playing":
            title = "Waiting for media playback..."
            artist = "Start playing a track in Spotify, YouTube, or your media player"
            t.append(title, style=Style(color="rgb(255, 255, 255)", bold=True))
            t.append("\n")
            t.append(artist, style=dim_style)
            return t

        title = self.state.metadata.title
        t.append(title, style=Style(color="rgb(255, 255, 255)", bold=True))
        t.append("\n")

        # Artist
        artist = self.state.metadata.artist or "Unknown Artist"
        t.append(artist, style=acc_style)

        # Album
        album = self.state.metadata.album
        if album and album != "Unknown Album":
            t.append("  •  ", style=dim_style)
            t.append(album, style=dim_style)

        return t
