"""Pixel sprite representation and terminal half-block truecolor renderer."""

from __future__ import annotations

from typing import List, Optional, Tuple, Union
from rich.text import Text
from rich.style import Style

# Color type: (R, G, B) or None for transparent
RGBColor = Tuple[int, int, int]
Pixel = Optional[RGBColor]


class PixelSprite:
    """A 2D pixel grid renderable to terminal characters using half-blocks."""

    def __init__(self, width: int, height: int, default_pixel: Pixel = None) -> None:
        self.width = width
        self.height = height
        # Ensure even height for half-block pair rendering
        if self.height % 2 != 0:
            self.height += 1
        self.pixels: List[List[Pixel]] = [
            [default_pixel for _ in range(self.width)] for _ in range(self.height)
        ]

    def set_pixel(self, x: int, y: int, color: Pixel) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.pixels[y][x] = color

    def get_pixel(self, x: int, y: int) -> Pixel:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.pixels[y][x]
        return None

    @classmethod
    def from_ascii(
        cls,
        ascii_lines: List[str],
        color_map: dict[str, Pixel],
    ) -> "PixelSprite":
        """Build a sprite from ASCII art lines and a color palette mapping."""
        h = len(ascii_lines)
        w = max(len(line) for line in ascii_lines) if ascii_lines else 0
        sprite = cls(w, h)
        for y, line in enumerate(ascii_lines):
            for x, char in enumerate(line):
                color = color_map.get(char, None)
                sprite.set_pixel(x, y, color)
        return sprite

    def render_to_rich_text(
        self,
        bg_color: Optional[RGBColor] = None,
        offset_x: int = 0,
        offset_y: int = 0,
    ) -> Text:
        """Render the pixel grid to Rich Text using half-block characters (▀ and ▄)."""
        text = Text()

        # Render 2 vertical pixels per terminal line
        for row in range(0, self.height, 2):
            if offset_x > 0:
                text.append(" " * offset_x)

            for col in range(self.width):
                top_px = self.get_pixel(col, row)
                bot_px = self.get_pixel(col, row + 1)

                top = top_px if top_px is not None else bg_color
                bot = bot_px if bot_px is not None else bg_color

                if top is None and bot is None:
                    text.append(" ")
                elif top is not None and bot is None:
                    # Only top is colored -> ▀ with fg=top
                    style = Style(color=f"rgb({top[0]},{top[1]},{top[2]})")
                    text.append("▀", style=style)
                elif top is None and bot is not None:
                    # Only bottom is colored -> ▄ with fg=bot
                    style = Style(color=f"rgb({bot[0]},{bot[1]},{bot[2]})")
                    text.append("▄", style=style)
                else:
                    # Both are colored -> ▀ with fg=top, bg=bot
                    style = Style(
                        color=f"rgb({top[0]},{top[1]},{top[2]})",
                        bgcolor=f"rgb({bot[0]},{bot[1]},{bot[2]})",
                    )
                    text.append("▀", style=style)

            if row + 2 < self.height:
                text.append("\n")

        return text
