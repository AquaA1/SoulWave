"""Dancing companion mini-mascots widget for hidden-lyrics mode."""

from __future__ import annotations

from typing import List, Tuple
from rich.text import Text
from rich.style import Style
from textual.widget import Widget

from ...theme.dynamic import RGB


class CompanionDanceView(Widget):
    """Displays unique dancing companion mini-mascots when lyrics are hidden."""

    DEFAULT_CSS = """
    CompanionDanceView {
        height: 100%;
        width: 100%;
        content-align: center middle;
        padding: 0 1;
    }
    """

    # Hand-crafted companion sprites (3 rows x 9 columns)
    # Companion 1: Pip (Mint Sprout Slime) - squish & bounce
    PIP_PLAYING_0 = [
        "   🌱    ",
        " ( •‿• ) ",
        " (_____) ",
    ]
    PIP_PLAYING_1 = [
        "   🌱    ",
        " ᐠ(•‿•)ᐟ ",
        "  (   )  ",
    ]
    PIP_PAUSED = [
        "   🌱    ",
        " ( •-• ) ",
        " (_____) ",
    ]
    PIP_IDLE = [
        "   🌱    ",
        " ( -.- ) ",
        " (_____) ",
    ]

    # Companion 2: Nova (Golden Starlet) - floating & ray pulse
    NOVA_PLAYING_0 = [
        "  ✦   ✦  ",
        " ✧(◕‿◕)✧ ",
        "   ˙⤙˙   ",
    ]
    NOVA_PLAYING_1 = [
        "  ✧   ✧  ",
        " ✦(ᵔᵕᵔ)✦ ",
        "   ˘⤙˘   ",
    ]
    NOVA_PAUSED = [
        "    ✦    ",
        " ·(•‿•)· ",
        "   ˙⤙˙   ",
    ]
    NOVA_IDLE = [
        "    ·    ",
        "  (u_u)｡ ",
        "   ...   ",
    ]

    # Companion 3: Mochi (Lavender Headphone Bun) - swaying head-bob
    MOCHI_PLAYING_0 = [
        "  ₍ᐢ. .ᐢ₎  ",
        "  🎧•ω•)  ",
        "   (__)   ",
    ]
    MOCHI_PLAYING_1 = [
        "  ₍ᐢ. .ᐢ₎  ",
        "  (•ω•🎧  ",
        "   (__)   ",
    ]
    MOCHI_PAUSED = [
        "  ₍ᐢ. .ᐢ₎  ",
        "  🎧•.•🎧  ",
        "   (__)   ",
    ]
    MOCHI_IDLE = [
        "  ₍ᐢ. .ᐢ₎  ",
        "  (-.-)ᶻ  ",
        "   (__)   ",
    ]

    def __init__(
        self,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self.is_playing: bool = False
        self.is_paused: bool = False
        self.energy: float = 0.0
        self.accent_color: RGB = (56, 189, 248)
        self._tick_count: int = 0

    def update_state(
        self,
        is_playing: bool,
        is_paused: bool,
        accent: RGB,
        energy: float = 0.0,
    ) -> None:
        self.is_playing = is_playing
        self.is_paused = is_paused
        self.accent_color = accent
        self.energy = max(0.0, min(1.0, energy))
        self._tick_count += 1
        self.refresh()

    def render(self) -> Text:
        t = Text()
        h = getattr(self, "_test_height", self.size.height if self.size.height > 0 else 12)
        w = getattr(self, "_test_width", self.size.width if self.size.width > 0 else 40)
        height = max(5, h)
        width = max(24, w)

        # Header bar matching lyrics panel style
        t.append("── COMPANIONS (GROOVE ROOM) ──\n", style=Style(color="rgb(100, 116, 139)"))

        # Determine frame index based on playback and audio energy
        if self.is_playing:
            # Beat-reactive frame tempo: high energy switches every 3 ticks, otherwise 6
            period = 3 if self.energy > 0.4 else 6
            frame_idx = (self._tick_count // period) % 2
            pip_lines = self.PIP_PLAYING_0 if frame_idx == 0 else self.PIP_PLAYING_1
            nova_lines = self.NOVA_PLAYING_0 if frame_idx == 0 else self.NOVA_PLAYING_1
            mochi_lines = self.MOCHI_PLAYING_0 if frame_idx == 0 else self.MOCHI_PLAYING_1
        elif self.is_paused:
            pip_lines = self.PIP_PAUSED
            nova_lines = self.NOVA_PAUSED
            mochi_lines = self.MOCHI_PAUSED
        else:
            pip_lines = self.PIP_IDLE
            nova_lines = self.NOVA_IDLE
            mochi_lines = self.MOCHI_IDLE

        # Colors
        pip_style = Style(color="rgb(52, 211, 153)", bold=True)      # Mint green
        nova_style = Style(color="rgb(251, 191, 36)", bold=True)     # Amber gold
        mochi_style = Style(color="rgb(192, 132, 252)", bold=True)   # Lavender violet
        tag_style = Style(color="rgb(148, 163, 184)")
        dim_style = Style(color="rgb(100, 116, 139)")

        # Spacing calculations
        sprite_w = 9
        num_sprites = 3
        gap = max(1, min(4, (width - (sprite_w * num_sprites)) // 2))
        total_w = (sprite_w * num_sprites) + (gap * (num_sprites - 1))

        left_pad = max(1, (width - total_w) // 2)
        spacer = " " * gap
        pad_str = " " * left_pad

        # Optional top breathing space if height allows
        if height >= 8:
            t.append("\n")

        # Render 3 sprite rows side-by-side
        for row in range(3):
            t.append(pad_str)
            t.append(pip_lines[row], style=pip_style)
            t.append(spacer)
            t.append(nova_lines[row], style=nova_style)
            t.append(spacer)
            t.append(mochi_lines[row], style=mochi_style)
            t.append("\n")

        # Name tags below sprites
        t.append(pad_str)
        t.append("   Pip   ", style=tag_style)
        t.append(spacer)
        t.append("  Nova   ", style=tag_style)
        t.append(spacer)
        t.append("  Mochi  ", style=tag_style)
        t.append("\n")

        # Status text below
        if height >= 9:
            t.append("\n")
            if self.is_playing:
                energy_dot = "✨" if self.energy > 0.4 else "♪"
                status_str = f" {energy_dot} Grooving with the beat"
                status_col = Style(color=f"rgb({self.accent_color[0]},{self.accent_color[1]},{self.accent_color[2]})")
            elif self.is_paused:
                status_str = " ⏸  Resting calmly..."
                status_col = dim_style
            else:
                status_str = " 💤 Fast asleep"
                status_col = dim_style

            status_pad = max(1, (width - len(status_str)) // 2)
            t.append(" " * status_pad)
            t.append(f"{status_str}\n", style=status_col)

        return t
