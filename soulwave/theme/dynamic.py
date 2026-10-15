"""Per-song dynamic accent color generator based on track metadata hash."""

from __future__ import annotations

import colorsys
import hashlib
from typing import Tuple

RGB = Tuple[int, int, int]


def get_song_accent_color(title: str, artist: str) -> RGB:
    """Generate a consistent, vibrant truecolor accent from the song's title and artist."""
    if not title or title == "No Track Playing":
        return (56, 189, 248)  # Default sky blue

    key = f"{title.strip().lower()}--{artist.strip().lower()}"
    h_bytes = hashlib.md5(key.encode("utf-8")).digest()

    # Hue: 0.0 to 1.0 (full color wheel)
    hue = (h_bytes[0] + (h_bytes[1] << 8)) / 65536.0

    # Saturation: 0.65 to 0.85 (pleasing pastel-vibrant aesthetic)
    saturation = 0.65 + ((h_bytes[2] % 100) / 500.0)

    # Value/Brightness: 0.82 to 0.96 (never too dark)
    value = 0.82 + ((h_bytes[3] % 100) / 700.0)

    r_f, g_f, b_f = colorsys.hsv_to_rgb(hue, saturation, value)
    return (int(r_f * 255), int(g_f * 255), int(b_f * 255))
