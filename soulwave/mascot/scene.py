"""Room atmosphere and floating particle effects (notes, stars, z-sleepers)."""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass
from typing import List, Tuple
from rich.text import Text
from rich.style import Style

from .sprite import PixelSprite, RGBColor


@dataclass
class Particle:
    char: str
    x: float
    y: float
    vx: float
    vy: float
    lifetime: float
    max_lifetime: float
    color: RGBColor


class RoomScene:
    """Manages the surrounding room ambience, floating musical notes, and twinkling stars."""

    NOTES = ["♪", "♫", "♬", "♩"]
    STARS = ["✦", "✧", "·", "˚"]

    def __init__(self, width: int = 34, height: int = 12) -> None:
        self.width = width
        self.height = height
        self.particles: List[Particle] = []
        self._last_spawn = time.monotonic()
        self._last_star_twinkle = time.monotonic()
        self.stars_grid: List[Tuple[int, int, str, int]] = []  # x, y, char, brightness
        self._init_stars()

    def _init_stars(self) -> None:
        """Place a few subtle background stars."""
        self.stars_grid.clear()
        for _ in range(8):
            x = random.randint(1, self.width - 2)
            y = random.randint(0, self.height - 3)
            char = random.choice(self.STARS)
            self.stars_grid.append((x, y, char, random.randint(60, 160)))

    def spawn_note(self, accent_color: RGBColor | None = None) -> None:
        """Spawn a floating musical note near the bottom center."""
        col = accent_color or (147, 197, 253)
        char = random.choice(self.NOTES)
        # Spawn near mascot sides
        side = -1 if random.random() < 0.5 else 1
        x = (self.width / 2.0) + (side * random.uniform(8.0, 12.0))
        y = float(self.height - 3)
        self.particles.append(
            Particle(
                char=char,
                x=x,
                y=y,
                vx=random.uniform(-0.4, 0.4),
                vy=random.uniform(-0.8, -1.4),
                lifetime=0.0,
                max_lifetime=random.uniform(2.5, 4.0),
                color=col,
            )
        )

    def spawn_sleep_z(self) -> None:
        """Spawn a gentle floating 'z' when paused/sleepy."""
        x = (self.width / 2.0) + random.uniform(4.0, 8.0)
        y = float(self.height - 4)
        self.particles.append(
            Particle(
                char="z",
                x=x,
                y=y,
                vx=random.uniform(0.1, 0.3),
                vy=random.uniform(-0.5, -0.9),
                lifetime=0.0,
                max_lifetime=3.0,
                color=(148, 163, 184),
            )
        )

    def update(self, is_playing: bool, is_paused: bool, accent_color: RGBColor | None = None) -> None:
        """Update particle physics and spawn new notes."""
        now = time.monotonic()
        dt = 0.08  # Approx tick delta

        # Spawn notes while playing
        if is_playing and now - self._last_spawn > random.uniform(0.9, 1.8):
            self._last_spawn = now
            self.spawn_note(accent_color)
        elif is_paused and now - self._last_spawn > 2.2:
            self._last_spawn = now
            self.spawn_sleep_z()

        # Update existing particles
        surviving = []
        for p in self.particles:
            p.lifetime += dt
            if p.lifetime < p.max_lifetime:
                p.x += p.vx + (math.sin(p.lifetime * 3) * 0.15)
                p.y += p.vy * dt * 4.0
                if 0 <= p.x < self.width and 0 <= p.y < self.height:
                    surviving.append(p)
        self.particles = surviving

    def compose_frame(
        self,
        mascot_sprite: PixelSprite,
        accent_color: RGBColor | None = None,
    ) -> Text:
        """Compose the mascot sprite centered inside the room scene with particles."""
        # Convert mascot sprite to rich text lines
        mascot_text = mascot_sprite.render_to_rich_text()
        mascot_lines = mascot_text.split()
        mascot_w = mascot_sprite.width
        mascot_h = len(mascot_lines)

        # Buffer of characters and styles
        canvas_chars = [[" " for _ in range(self.width)] for _ in range(self.height)]
        canvas_styles: List[List[Style | None]] = [
            [None for _ in range(self.width)] for _ in range(self.height)
        ]

        # Draw subtle stars
        for sx, sy, schar, brightness in self.stars_grid:
            if 0 <= sy < self.height and 0 <= sx < self.width:
                canvas_chars[sy][sx] = schar
                canvas_styles[sy][sx] = Style(color=f"rgb({brightness},{brightness},{brightness})")

        # Draw floating particles
        for p in self.particles:
            px, py = int(round(p.x)), int(round(p.y))
            if 0 <= py < self.height and 0 <= px < self.width:
                canvas_chars[py][px] = p.char
                # Fade color towards end of life
                fade = max(0.2, 1.0 - (p.lifetime / p.max_lifetime))
                r = int(p.color[0] * fade)
                g = int(p.color[1] * fade)
                b = int(p.color[2] * fade)
                canvas_styles[py][px] = Style(color=f"rgb({r},{g},{b})", bold=True)

        # Mascot top-left placement (centered)
        start_x = max(0, (self.width - mascot_w) // 2)
        start_y = max(0, (self.height - mascot_h) // 2)

        # Assemble final Rich Text
        final_text = Text()

        for y in range(self.height):
            # If line falls into mascot vertical bounds
            mascot_line_idx = y - start_y
            if 0 <= mascot_line_idx < mascot_h:
                m_line = mascot_lines[mascot_line_idx]
                # Left background
                left_pad = Text()
                for x in range(start_x):
                    ch = canvas_chars[y][x]
                    st = canvas_styles[y][x]
                    left_pad.append(ch, style=st)

                # Right background
                right_pad = Text()
                for x in range(start_x + mascot_w, self.width):
                    ch = canvas_chars[y][x]
                    st = canvas_styles[y][x]
                    right_pad.append(ch, style=st)

                final_text.append_text(left_pad)
                final_text.append_text(m_line)
                final_text.append_text(right_pad)
            else:
                # Room-only line
                line_text = Text()
                for x in range(self.width):
                    ch = canvas_chars[y][x]
                    st = canvas_styles[y][x]
                    line_text.append(ch, style=st)
                final_text.append_text(line_text)

            if y < self.height - 1:
                final_text.append("\n")

        # Bottom floor / cozy rug line
        rug_col = accent_color or (100, 116, 139)
        final_text.append("\n" + " " * (start_x - 1))
        rug_style = Style(color=f"rgb({rug_col[0]//2},{rug_col[1]//2},{rug_col[2]//2})")
        final_text.append("╭" + "─" * (mascot_w) + "╮", style=rug_style)

        return final_text
