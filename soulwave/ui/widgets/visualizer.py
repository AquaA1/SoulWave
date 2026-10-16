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

    VISUALIZER_HEIGHT: int = AudioVisualizer.DEFAULT_HEIGHT  # Layout constant: 2 text rows (~1.5x)

    DEFAULT_CSS = """
    VisualizerView {
        height: 2;
        width: 100%;
        content-align: center bottom;
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

    @property
    def current_energy(self) -> float:
        """Estimate current audio energy [0.0, 1.0] from CAVA bars or playback state."""
        if not self.is_playing:
            return 0.0
        if self._cava_ok and self._cava.is_running:
            bars = self._cava.bars
            if bars:
                return float(min(1.0, max(0.0, sum(bars) / len(bars))))
        return 0.5

    # ------------------------------------------------------------------ #
    #  Rendering                                                           #
    # ------------------------------------------------------------------ #

    def render(self) -> Text:
        # Determine effective render height (gracefully degrades to 1 if terminal is compact)
        h = max(1, min(self.VISUALIZER_HEIGHT, self.size.height)) if self.size.height > 0 else self.VISUALIZER_HEIGHT

        # Prefer live CAVA data; fall back to synthetic animation
        if self._cava_ok and self._cava.is_running:
            return self._render_cava(height=h)
        return self.visualizer.tick(
            is_playing=self.is_playing,
            volume=self.volume,
            bpm=self.bpm,
            accent_color=self.accent_color,
            height=h,
        )

    def _render_cava(self, height: int = VISUALIZER_HEIGHT) -> Text:
        """Render CAVA bar heights as block characters with accent gradient, anchored at bottom."""
        BAR_CHARS = AudioVisualizer.BAR_CHARS
        bars = self._cava.bars

        # When paused / stopped decay bars toward zero gracefully
        if not self.is_playing:
            bars = [max(0.0, b - 0.08) for b in bars]

        col = self.accent_color
        num_rows = max(1, height)

        if num_rows == 1:
            text = Text()
            for val in bars:
                val = max(0.0, min(1.0, val))
                char_idx = int(round(val * (len(BAR_CHARS) - 1)))
                ch = BAR_CHARS[char_idx]

                r = int(min(255, col[0] * (0.4 + val * 0.6)))
                g = int(min(255, col[1] * (0.4 + val * 0.6)))
                b = int(min(255, col[2] * (0.4 + val * 0.6)))

                text.append(ch, style=f"rgb({r},{g},{b})")
                text.append(" ")
            return text

        # Multi-row rendering: row 0 is top, row num_rows-1 is bottom base
        row_texts = [Text() for _ in range(num_rows)]

        for val in bars:
            val = max(0.0, min(1.0, val))
            total_amp = val * num_rows

            for r_idx in range(num_rows):
                level_from_bottom = (num_rows - 1) - r_idx
                amp_in_row = total_amp - level_from_bottom

                if amp_in_row >= 1.0:
                    ch = BAR_CHARS[-1]
                    intensity = 0.5 + (0.5 * ((level_from_bottom + 1) / num_rows))
                elif amp_in_row > 0.0:
                    char_idx = int(round(amp_in_row * (len(BAR_CHARS) - 1)))
                    char_idx = max(0, min(len(BAR_CHARS) - 1, char_idx))
                    ch = BAR_CHARS[char_idx]
                    intensity = 0.4 + (0.6 * ((level_from_bottom + amp_in_row) / num_rows))
                else:
                    ch = " "
                    intensity = 0.4

                r = int(min(255, col[0] * intensity))
                g = int(min(255, col[1] * intensity))
                b = int(min(255, col[2] * intensity))

                row_texts[r_idx].append(ch, style=f"rgb({r},{g},{b})")
                row_texts[r_idx].append(" ")

        final_text = Text()
        for idx, row in enumerate(row_texts):
            final_text.append_text(row)
            if idx < len(row_texts) - 1:
                final_text.append("\n")

        return final_text

    # ------------------------------------------------------------------ #
    #  Lifecycle                                                           #
    # ------------------------------------------------------------------ #

    def on_unmount(self) -> None:
        self._cava.stop()
