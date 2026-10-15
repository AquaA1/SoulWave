"""Theme definitions and color palettes for Soulwave."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

RGB = Tuple[int, int, int]


@dataclass
class Theme:
    name: str
    background: RGB
    surface: RGB
    border: RGB
    text: RGB
    text_dim: RGB
    primary_accent: RGB
    secondary_accent: RGB
    progress_bar_fill: RGB
    progress_bar_empty: RGB

    def to_css(self, dynamic_accent: RGB | None = None) -> str:
        """Generate CSS variable definitions for Textual."""
        accent = dynamic_accent or self.primary_accent
        return f"""
        Screen {{
            background: rgb({self.background[0]}, {self.background[1]}, {self.background[2]});
            color: rgb({self.text[0]}, {self.text[1]}, {self.text[2]});
        }}
        """


# Pre-defined curated themes
THEMES: Dict[str, Theme] = {
    "night": Theme(
        name="Night",
        background=(15, 23, 42),          # slate-900
        surface=(30, 41, 59),            # slate-800
        border=(51, 65, 85),             # slate-700
        text=(248, 250, 252),            # slate-50
        text_dim=(148, 163, 184),        # slate-400
        primary_accent=(56, 189, 248),   # sky-400
        secondary_accent=(168, 85, 247), # purple-500
        progress_bar_fill=(56, 189, 248),
        progress_bar_empty=(51, 65, 85),
    ),
    "sunset": Theme(
        name="Sunset",
        background=(36, 18, 48),         # deep dusk plum
        surface=(66, 32, 75),            # warm violet
        border=(112, 53, 102),           # magenta border
        text=(255, 241, 242),            # soft peach
        text_dim=(216, 180, 210),        # dusty rose
        primary_accent=(251, 113, 133),  # rose-400
        secondary_accent=(251, 191, 36), # amber-400
        progress_bar_fill=(251, 113, 133),
        progress_bar_empty=(88, 42, 90),
    ),
    "mint": Theme(
        name="Mint",
        background=(18, 38, 32),         # deep evergreen
        surface=(30, 60, 52),            # dark forest
        border=(52, 98, 85),             # moss border
        text=(240, 253, 244),            # fresh cream
        text_dim=(167, 243, 208),        # soft sage
        primary_accent=(52, 211, 153),   # emerald-400
        secondary_accent=(110, 231, 183),# mint-300
        progress_bar_fill=(52, 211, 153),
        progress_bar_empty=(40, 75, 65),
    ),
    "sakura": Theme(
        name="Sakura",
        background=(39, 23, 33),         # night sakura
        surface=(64, 38, 54),            # deep plum
        border=(102, 57, 85),            # blossom border
        text=(255, 245, 247),            # pure blossom white
        text_dim=(244, 182, 208),        # soft lilac
        primary_accent=(244, 114, 182),  # pink-400
        secondary_accent=(251, 191, 222),# pink-200
        progress_bar_fill=(244, 114, 182),
        progress_bar_empty=(78, 45, 66),
    ),
    "cyberpunk": Theme(
        name="Cyberpunk",
        background=(13, 14, 27),         # neon dark
        surface=(25, 28, 54),            # deep synth indigo
        border=(67, 56, 120),            # electric border
        text=(240, 249, 255),            # electric white
        text_dim=(147, 197, 253),        # icy blue
        primary_accent=(244, 63, 94),    # hot pink/red
        secondary_accent=(6, 182, 212),  # neon cyan
        progress_bar_fill=(6, 182, 212),
        progress_bar_empty=(42, 38, 77),
    ),
    "mono": Theme(
        name="Mono",
        background=(18, 18, 18),         # true dark
        surface=(38, 38, 38),            # carbon
        border=(64, 64, 64),             # mid gray
        text=(250, 250, 250),            # crisp white
        text_dim=(163, 163, 163),        # light gray
        primary_accent=(245, 245, 245),  # chalk white
        secondary_accent=(115, 115, 115),# neutral
        progress_bar_fill=(255, 255, 255),
        progress_bar_empty=(55, 55, 55),
    ),
}


def get_theme(name: str) -> Theme:
    """Retrieve theme by name, default to 'night'."""
    return THEMES.get(name.lower(), THEMES["night"])


def cycle_theme_name(current: str) -> str:
    """Return the next theme key in circular order."""
    keys = list(THEMES.keys())
    try:
        idx = keys.index(current.lower())
        return keys[(idx + 1) % len(keys)]
    except ValueError:
        return keys[0]
