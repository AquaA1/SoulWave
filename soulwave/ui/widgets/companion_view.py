"""Dancing companion mini-mascots widget for hidden-lyrics mode."""

from __future__ import annotations

import math
from typing import List, Tuple
from rich.text import Text
from rich.style import Style
from textual.widget import Widget

from ...theme.dynamic import RGB
from ...mascot.sprite import PixelSprite


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

    # Hand-crafted pixel-art soul companion matrices (11 columns x 10 rows)
    # Rendered using terminal half-blocks (5 terminal lines tall).
    # Palette legend:
    # W = White ghost body
    # H = Slate headphone band
    # D = Dark eyes
    # P = Soft blush
    # E = Sprout mint green (Pip)
    # Y = Golden amber star (Nova)
    # V = Lavender violet (Mochi)
    # S = Eye / star shine

    # Colors
    W = (248, 250, 252)
    H = (71, 85, 105)
    D = (30, 41, 59)
    P = (251, 113, 133)
    S = (255, 255, 255)
    E = (74, 222, 128)   # Pip sprout green
    Y = (251, 191, 36)   # Nova golden amber
    V = (192, 132, 252)  # Mochi lavender violet

    PIP_MAP = {" ": None, "W": W, "H": H, "E": E, "D": D, "P": P, "-": D}
    NOVA_MAP = {" ": None, "W": W, "H": H, "Y": Y, "D": D, "P": P, "S": S, "^": D, "-": D}
    MOCHI_MAP = {" ": None, "W": W, "H": H, "V": V, "D": D, "P": P, "-": D, "~": D}

    # --- Companion 1: Pip (The gentle soul) ---
    PIP_PLAY_0 = [
        "    EEE    ",
        "     E     ",
        "   HHHHH   ",
        "  HWWWWWH  ",
        " EEWWWWWEE ",
        " EEWD DWEE ",
        "  HWP PWH  ",
        "   WWWWW   ",
        "   WWWWW   ",
        "   W W W   ",
    ]
    PIP_PLAY_1 = [
        "           ",
        "   EE E    ",
        "    E      ",
        "   HHHHH   ",
        "  HWWWWWH  ",
        " EEWWWWWEE ",
        " EEWD DWEE ",
        "  HWP PWH  ",
        "  WWWWWWW  ",
        "  WW W WW  ",
    ]
    PIP_PLAY_2 = [
        "           ",
        "    E EE   ",
        "     E     ",
        "   HHHHH   ",
        "  HWWWWWH  ",
        " EEWWWWWEE ",
        " EEWD DWEE ",
        "  HWP PWH  ",
        "  WWWWWWW  ",
        "  WW W WW  ",
    ]
    PIP_PAUSED = [
        "    EEE    ",
        "     E     ",
        "   HHHHH   ",
        "  HWWWWWH  ",
        " EEWWWWWEE ",
        " EEWD DWEE ",
        "  HWP PWH  ",
        "   WWWWW   ",
        "   WWWWW   ",
        "   W W W   ",
    ]
    PIP_IDLE = [
        "    EEE    ",
        "     E     ",
        "   HHHHH   ",
        "  HWWWWWH  ",
        " EEWWWWWEE ",
        " EEW- -WEE ",
        "  HWP PWH  ",
        "   WWWWW   ",
        "   WWWWW   ",
        "   W W W   ",
    ]

    # --- Companion 2: Nova (The energetic soul) ---
    NOVA_PLAY_0 = [
        "       Y   ",
        "      YYY  ",
        "   HHHHH   ",
        "  HWWWWWH  ",
        " YYWWWWWYY ",
        " YYWD DWYY ",
        "  HWP PWH  ",
        "   WWWWW   ",
        "   WWWWW   ",
        "   W W W   ",
    ]
    NOVA_HOP_1 = [
        "      YSY  ",
        "       Y   ",
        "   HHHHH   ",
        "  HWWWWWH  ",
        " YYWWWWWYY ",
        " YYW^ ^WYY ",
        "  HWP PWH  ",
        "  WWWWWWW  ",
        "   WWWWW   ",
        "   WW WW   ",
    ]
    NOVA_HOP_2 = [
        "      YYY  ",
        "     YSYSY ",
        "   HHHHH   ",
        "  HWWWWWH  ",
        " YYWWWWWYY ",
        " YYW^ ^WYY ",
        "  HWP PWH  ",
        "  WWWWWWW  ",
        "   WWWWW   ",
        "   W   W   ",
    ]
    NOVA_PAUSED = [
        "       Y   ",
        "      YYY  ",
        "   HHHHH   ",
        "  HWWWWWH  ",
        " YYWWWWWYY ",
        " YYWD DWYY ",
        "  HWP PWH  ",
        "   WWWWW   ",
        "   WWWWW   ",
        "   W W W   ",
    ]
    NOVA_IDLE = [
        "       Y   ",
        "      YYY  ",
        "   HHHHH   ",
        "  HWWWWWH  ",
        " YYWWWWWYY ",
        " YYW- -WYY ",
        "  HWP PWH  ",
        "   WWWWW   ",
        "   WWWWW   ",
        "   W W W   ",
    ]

    # --- Companion 3: Mochi (The sleepy soul) ---
    MOCHI_TILT_LEFT = [
        "        V  ",
        "       V   ",
        "  HHHHH    ",
        " HWWWWWH   ",
        "VVWWWWWVV  ",
        "VVWD DWVV  ",
        " HWP PWH   ",
        "  WWWWW    ",
        "  WWWWW    ",
        "  W W W    ",
    ]
    MOCHI_CENTER = [
        "        V  ",
        "       V   ",
        "   HHHHH   ",
        "  HWWWWWH  ",
        " VVWWWWWVV ",
        " VVW- -WVV ",
        "  HWP PWH  ",
        "   WWWWW   ",
        "   WWWWW   ",
        "   W W W   ",
    ]
    MOCHI_TILT_RIGHT = [
        "         V ",
        "        V  ",
        "    HHHHH  ",
        "   HWWWWWH ",
        "  VVWWWWWVV",
        "  VVWD DWVV",
        "   HWP PWH ",
        "    WWWWW  ",
        "    WWWWW  ",
        "    W W W  ",
    ]
    MOCHI_PAUSED = [
        "        V  ",
        "       V   ",
        "   HHHHH   ",
        "  HWWWWWH  ",
        " VVWWWWWVV ",
        " VVW- -WVV ",
        "  HWP PWH  ",
        "   WWWWW   ",
        "   WWWWW   ",
        "   W W W   ",
    ]
    MOCHI_IDLE = [
        "        V  ",
        "       V   ",
        "   HHHHH   ",
        "  HWWWWWH  ",
        " VVWWWWWVV ",
        " VVW- -WVV ",
        "  HWP PWH  ",
        "   WWWWW   ",
        "   WWWWW   ",
        "   W W W   ",
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
        self.in_track_transition: bool = False
        self.energy: float = 0.0
        self.accent_color: RGB = (56, 189, 248)
        self._tick_count: int = 0

    def set_track_transition(self, active: bool) -> None:
        """Inform companions of an in-progress track transition."""
        self.in_track_transition = active
        self.refresh()

    def update_state(
        self,
        is_playing: bool,
        is_paused: bool,
        accent: RGB,
        energy: float = 0.0,
        in_transition: bool = False,
    ) -> None:
        self.is_playing = is_playing
        self.is_paused = is_paused
        self.in_track_transition = in_transition
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

        # Header bar matching reference design
        title_text = " COMPANIONS (GROOVE ROOM) " if width >= 44 else " COMPANIONS "
        dash_len = max(2, (width - len(title_text)) // 2)
        header_bar = f"{'─' * dash_len}{title_text}{'─' * dash_len}\n"
        t.append(header_bar, style=Style(color="rgb(100, 116, 139)"))

        # Determine frame index based on playback state and transition
        if self.is_playing and not self.in_track_transition:
            # Pip: noticeable vertical bob with gentle green leaf flutter (period 18 ticks)
            pip_idx = self._tick_count % 18
            if pip_idx < 6:
                pip_f = self.PIP_PLAY_0
            elif pip_idx < 12:
                pip_f = self.PIP_PLAY_1
            else:
                pip_f = self.PIP_PLAY_2

            # Nova: stronger bounce with occasional double-bounce and short pause (period 16 ticks)
            nova_idx = self._tick_count % 16
            if nova_idx < 4:
                nova_f = self.NOVA_PLAY_0
            elif nova_idx < 7:
                nova_f = self.NOVA_HOP_1
            elif nova_idx < 9:
                nova_f = self.NOVA_PLAY_0
            elif nova_idx < 12:
                nova_f = self.NOVA_HOP_2
            else:
                nova_f = self.NOVA_PLAY_0

            # Mochi: visible side-to-side rocking with headphone tilt (period 16 ticks, phase offset 4)
            mochi_idx = (self._tick_count + 4) % 16
            if mochi_idx < 4:
                mochi_f = self.MOCHI_TILT_LEFT
            elif mochi_idx < 8:
                mochi_f = self.MOCHI_CENTER
            elif mochi_idx < 12:
                mochi_f = self.MOCHI_TILT_RIGHT
            else:
                mochi_f = self.MOCHI_CENTER
        elif self.in_track_transition or self.is_paused:
            pip_f = self.PIP_PAUSED
            nova_f = self.NOVA_PAUSED
            mochi_f = self.MOCHI_PAUSED
        else:
            pip_f = self.PIP_IDLE
            nova_f = self.NOVA_IDLE
            mochi_f = self.MOCHI_IDLE

        # Render sprites to rich half-blocks
        p_lines = PixelSprite.from_ascii(pip_f, self.PIP_MAP).render_to_rich_text().split()
        n_lines = PixelSprite.from_ascii(nova_f, self.NOVA_MAP).render_to_rich_text().split()
        m_lines = PixelSprite.from_ascii(mochi_f, self.MOCHI_MAP).render_to_rich_text().split()

        # Layout calculation
        sprite_w = 11
        gap = max(1, min(4, (width - (sprite_w * 3)) // 3))
        total_w = (sprite_w * 3) + (gap * 2)
        left_pad = max(1, (width - total_w) // 2)
        pad_str = " " * left_pad
        spacer = " " * gap

        # Optional top breathing space if height allows
        if height >= 10:
            t.append("\n")

        # Render 5 terminal rows (10 pixel rows)
        num_rows = min(len(p_lines), len(n_lines), len(m_lines))
        for row in range(num_rows):
            t.append(pad_str)
            t.append_text(p_lines[row])
            t.append(spacer)
            t.append_text(n_lines[row])
            t.append(spacer)
            t.append_text(m_lines[row])
            t.append("\n")

        # Name tags below sprites
        pip_col = Style(color="rgb(74, 222, 128)", bold=True)
        nova_col = Style(color="rgb(251, 191, 36)", bold=True)
        mochi_col = Style(color="rgb(192, 132, 252)", bold=True)
        tag_style = Style(color="rgb(148, 163, 184)")

        t.append(pad_str)
        t.append("    Pip    ", style=pip_col)
        t.append(spacer)
        t.append("   Nova    ", style=nova_col)
        t.append(spacer)
        t.append("   Mochi   ", style=mochi_col)
        t.append("\n")

        # Subtitles below names
        if height >= 9:
            sub_pip = "The gentle soul" if width >= 54 else "Gentle soul"
            sub_nova = "The energetic soul" if width >= 54 else "Energetic"
            sub_mochi = "The sleepy soul" if width >= 54 else "Sleepy soul"

            # Center subtitles under each column
            p_pad = max(0, (sprite_w - len(sub_pip)) // 2)
            n_pad = max(0, (sprite_w - len(sub_nova)) // 2)
            m_pad = max(0, (sprite_w - len(sub_mochi)) // 2)

            t.append(pad_str)
            t.append(" " * p_pad + sub_pip + " " * max(0, sprite_w - len(sub_pip) - p_pad), style=tag_style)
            t.append(spacer)
            t.append(" " * n_pad + sub_nova + " " * max(0, sprite_w - len(sub_nova) - n_pad), style=tag_style)
            t.append(spacer)
            t.append(" " * m_pad + sub_mochi + " " * max(0, sprite_w - len(sub_mochi) - m_pad), style=tag_style)
            t.append("\n")

        # Status text below
        if height >= 11:
            t.append("\n")
            if self.is_playing:
                energy_dot = "✨" if self.energy > 0.4 else "♪"
                status_str = f" {energy_dot} Grooving with the beat"
                status_col = Style(color=f"rgb({self.accent_color[0]},{self.accent_color[1]},{self.accent_color[2]})")
            elif self.is_paused:
                status_str = " ⏸  Resting calmly..."
                status_col = tag_style
            else:
                status_str = " 💤 Fast asleep"
                status_col = tag_style

            status_pad = max(1, (width - len(status_str)) // 2)
            t.append(" " * status_pad)
            t.append(f"{status_str}\n", style=status_col)

        return t
