"""Audio visualizer widget — CAVA-backed beat-reactive spectrum bars.

When CAVA is available the widget reads real PCM amplitude data from the
system audio monitor.  When CAVA is unavailable (not installed, or no audio
device) it falls back to the synthetic harmonic-wave pattern so the UI still
looks alive.
"""

from __future__ import annotations

from textual.widget import Widget
from rich.text import Text

from ...audio.visualizer import AudioVisualizer
from ...audio.cava_reader import CavaReader
from ...theme.dynamic import RGB


class VisualizerView(Widget):
    """Renders rhythmic audio spectrum bars, driven by CAVA when possible."""

    DEFAULT_CSS = """
    VisualizerView {
        height: 1;
        width: 100%;
        content-align: center middle;
    }
    """

    def __init__(
        self,
        num_bars: int = 36,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._num_bars = num_bars
        self.visualizer = AudioVisualizer(num_bars=num_bars)
        self._cava = CavaReader(num_bars=num_bars)
        self._cava_ok = self._cava.start()   # non-blocking; daemon thread

        self.is_playing: bool = False
        self.volume: float = 0.8
        self.bpm: float = 100.0
        self.accent_color: RGB = (56, 189, 248)

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def update_params(
        self,
        is_playing: bool,
        volume: float,
        bpm: float,
        accent: RGB,
    ) -> None:
        self.is_playing = is_playing
        self.volume = volume
        self.bpm = bpm
        self.accent_color = accent
        self.refresh()

    # ------------------------------------------------------------------ #
    #  Rendering                                                           #
    # ------------------------------------------------------------------ #

    def render(self) -> Text:
        # Prefer live CAVA data; fall back to synthetic animation
        if self._cava_ok and self._cava.is_running:
            return self._render_cava()
        return self.visualizer.tick(
            is_playing=self.is_playing,
            volume=self.volume,
            bpm=self.bpm,
            accent_color=self.accent_color,
        )

    def _render_cava(self) -> Text:
        """Render CAVA bar heights as block characters with accent gradient."""
        BAR_CHARS = AudioVisualizer.BAR_CHARS
        bars = self._cava.bars

        # When paused / stopped decay bars toward zero gracefully
        if not self.is_playing:
            bars = [max(0.0, b - 0.08) for b in bars]

        text = Text()
        col = self.accent_color

        for val in bars:
            val = max(0.0, min(1.0, val))
            char_idx = int(round(val * (len(BAR_CHARS) - 1)))
            ch = BAR_CHARS[char_idx]

            # Intensity-scaled colour: dim at low amplitude, bright at peaks
            r = int(min(255, col[0] * (0.4 + val * 0.6)))
            g = int(min(255, col[1] * (0.4 + val * 0.6)))
            b = int(min(255, col[2] * (0.4 + val * 0.6)))

            text.append(ch, style=f"rgb({r},{g},{b})")
            text.append(" ")

        return text

    # ------------------------------------------------------------------ #
    #  Lifecycle                                                           #
    # ------------------------------------------------------------------ #

    def on_unmount(self) -> None:
        self._cava.stop()
