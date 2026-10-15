"""Visualizer spectrum bar generator with subtle rhythm reactivity."""

from __future__ import annotations

import math
import random
import time
from typing import List, Tuple
from rich.text import Text
from rich.style import Style

RGB = Tuple[int, int, int]


class AudioVisualizer:
    """Generates animated audio spectrum bars for the bottom panel."""

    BAR_CHARS = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]

    def __init__(self, num_bars: int = 32, max_height: int = 2) -> None:
        self.num_bars = num_bars
        self.max_height = max_height
        self.levels: List[float] = [0.0] * num_bars
        self.peaks: List[float] = [0.0] * num_bars
        self._phase = 0.0

    def tick(
        self,
        is_playing: bool,
        volume: float = 0.8,
        bpm: float = 100.0,
        accent_color: RGB | None = None,
    ) -> Text:
        """Advance spectrum frame and return styled Rich Text."""
        dt = 0.08
        self._phase += dt * (bpm / 60.0) * math.pi

        for i in range(self.num_bars):
            if is_playing:
                # Harmonic wave pattern influenced by tempo and index
                freq = (i + 1) * 0.4
                wave1 = math.sin(self._phase * 1.5 + freq) * 0.5 + 0.5
                wave2 = math.cos(self._phase * 0.7 - freq * 0.5) * 0.5 + 0.5
                noise = random.uniform(-0.1, 0.1)

                target = ((wave1 * 0.6) + (wave2 * 0.4) + noise) * volume
                target = max(0.05, min(1.0, target))

                # Smooth lerp
                self.levels[i] += (target - self.levels[i]) * 0.35
            else:
                # Decay to zero
                self.levels[i] = max(0.0, self.levels[i] - 0.1)

            # Update peaks with slow falloff
            if self.levels[i] > self.peaks[i]:
                self.peaks[i] = self.levels[i]
            else:
                self.peaks[i] = max(0.0, self.peaks[i] - 0.05)

        # Render bars into Rich Text
        text = Text()
        col = accent_color or (56, 189, 248)

        for i, val in enumerate(self.levels):
            char_idx = int(round(val * (len(self.BAR_CHARS) - 1)))
            char_idx = max(0, min(len(self.BAR_CHARS) - 1, char_idx))
            ch = self.BAR_CHARS[char_idx]

            # Gradient color from base to peak
            r = int(min(255, col[0] * (0.6 + val * 0.4)))
            g = int(min(255, col[1] * (0.6 + val * 0.4)))
            b = int(min(255, col[2] * (0.6 + val * 0.4)))

            text.append(ch, style=Style(color=f"rgb({r},{g},{b})"))
            text.append(" ")

        return text
