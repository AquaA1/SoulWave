"""Handcrafted pixel-art frames and sprite animations for the Soul mascot."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from .sprite import PixelSprite, RGBColor, Pixel

# Base palette constants
W = (248, 250, 252)   # Ghost white body
G = (226, 232, 240)   # Body shading / soft crease
D = (30, 41, 59)      # Eye pupils / dark details
S = (255, 255, 255)   # Eye sparkle / shine
P = (251, 113, 133)   # Pink cheek blush
H = (71, 85, 105)     # Headphone band / dark chassis
A = (56, 189, 248)    # Headphone glowing earcups (Accent color default)
B = (14, 165, 233)    # Headphone inner rim
_ = None              # Transparent

# 18 width x 16 height ASCII matrix for frame templates
# Legend:
# ' ' = transparent
# 'W' = white body
# 'G' = body shading
# 'D' = dark eye
# 'S' = eye shine
# 'P' = pink blush
# 'H' = headphone band
# 'A' = headphone glow (replaced by dynamic accent)
# 'B' = headphone rim
# 'M' = mouth

# --- IDLE FRAMES ---
IDLE_F0 = [
    "        HHHHHHHHH        ",
    "      HH         HH      ",
    "     H   WWWWWWW   H     ",
    "    H  WWWWWWWWWWW  H    ",
    "   A  WWWWWWWWWWWWW  A   ",
    "   AA WWWWWWWWWWWWW AA   ",
    "   AA WWWWWWWWWWWWW AA   ",
    "   BB W DDDD   DDDD W BB ",
    "   BB W DDDD   DDDD W BB ",
    "   HA W DDPP   DDPP W AH ",
    "    H W DDPP   DDPP W H  ",
    "      WWWWWWWWWWWWW      ",
    "   WW WWWWWWWWWWWWW      ",
    "  WWW WWWWWWWWWWWWW      ",
    "   WW WWWWWWWWWWWWW      ",
    "      WWWWWWWWWWWWW      ",
    "      WWWWWWWWWWWWW      ",
    "      GWWWWWWWWWWWG      ",
    "       WWW  WWW  WWW     ",
    "       WW   WW    WW     ",
    "       W          W      ",
    "                         ",
]

IDLE_F1 = [
    "        HHHHHHHHH        ",
    "      HH         HH      ",
    "     H   WWWWWWW   H     ",
    "    H  WWWWWWWWWWW  H    ",
    "   A  WWWWWWWWWWWWW  A   ",
    "   AA WWWWWWWWWWWWW AA   ",
    "   AA WWWWWWWWWWWWW AA   ",
    "   BB W DDDD   DDDD W BB ",
    "   BB W DDDD   DDDD W BB ",
    "   HA W DDPP   DDPP W AH ",
    "    H W DDPP   DDPP W H  ",
    "      WWWWWWWWWWWWW      ",
    "   WW WWWWWWWWWWWWW      ",
    "  WWW WWWWWWWWWWWWW      ",
    "   WW WWWWWWWWWWWWW      ",
    "      WWWWWWWWWWWWW      ",
    "      WWWWWWWWWWWWW      ",
    "      GWWWWWWWWWWWG      ",
    "       WWW  WWW  WWW     ",
    "        WW   WW   WW     ",
    "         W    W    W     ",
    "                         ",
]

IDLE_BLINK = [
    "        HHHHHHHHH        ",
    "      HH         HH      ",
    "     H   WWWWWWW   H     ",
    "    H  WWWWWWWWWWW  H    ",
    "   A  WWWWWWWWWWWWW  A   ",
    "   AA WWWWWWWWWWWWW AA   ",
    "   AA WWWWWWWWWWWWW AA   ",
    "   BB W             W BB ",
    "   BB W ----   ---- W BB ",
    "   HA W DDPP   DDPP W AH ",
    "    H W             W H  ",
    "      WWWWWWWWWWWWW      ",
    "   WW WWWWWWWWWWWWW      ",
    "  WWW WWWWWWWWWWWWW      ",
    "   WW WWWWWWWWWWWWW      ",
    "      WWWWWWWWWWWWW      ",
    "      WWWWWWWWWWWWW      ",
    "      GWWWWWWWWWWWG      ",
    "       WWW  WWW  WWW     ",
    "       WW   WW    WW     ",
    "       W          W      ",
    "                         ",
]

# --- PLAYING / GROOVING FRAMES ---
PLAY_BOB_DOWN = [
    "                         ",
    "        HHHHHHHHH        ",
    "      HH         HH      ",
    "     H   WWWWWWW   H     ",
    "    H  WWWWWWWWWWW  H    ",
    "   A  WWWWWWWWWWWWW  A   ",
    "   AA WWWWWWWWWWWWW AA   ",
    "   AA W             W AA ",
    "   BB W ^^^^   ^^^^ W BB ",
    "   BB W PPPP   PPPP W BB ",
    "   HA W             W AH ",
    "    H WWWWWWWWWWWWW   H  ",
    "  WW  WWWWWWWWWWWWW   WW ",
    "  WW  WWWWWWWWWWWWW   WW ",
    "      WWWWWWWWWWWWW      ",
    "     WWWWWWWWWWWWWWW     ",
    "     WWWWWWWWWWWWWWW     ",
    "     GWWWWWWWWWWWWWG     ",
    "      WWW   WWW   WWW    ",
    "      WW    WW     WW    ",
    "      W      W      W    ",
    "                         ",
]

PLAY_SWAY_LEFT = [
    "       HHHHHHHHH         ",
    "     HH         HH       ",
    "    H   WWWWWWW   H      ",
    "   H  WWWWWWWWWWW  H     ",
    "  A  WWWWWWWWWWWWW  A    ",
    "  AA WWWWWWWWWWWWW AA    ",
    "  AA WWWWWWWWWWWWW AA    ",
    "  BB W DDDD   DDDD W BB  ",
    "  BB W DDDD   DDDD W BB  ",
    "  HA W DDPP   DDPP W AH  ",
    "   H W DDPP   DDPP W H   ",
    "     WWWWWWWWWWWWW       ",
    "  WW WWWWWWWWWWWWW       ",
    " WWW WWWWWWWWWWWWW       ",
    "  WW WWWWWWWWWWWWW       ",
    "     WWWWWWWWWWWWW       ",
    "     WWWWWWWWWWWWW       ",
    "     GWWWWWWWWWWWG       ",
    "      WWW  WWW  WWW      ",
    "     WW    WW    WW      ",
    "    W      W      W      ",
    "                         ",
]

PLAY_SWAY_RIGHT = [
    "         HHHHHHHHH       ",
    "       HH         HH     ",
    "      H   WWWWWWW   H    ",
    "     H  WWWWWWWWWWW  H   ",
    "    A  WWWWWWWWWWWWW  A  ",
    "    AA WWWWWWWWWWWWW AA  ",
    "    AA WWWWWWWWWWWWW AA  ",
    "    BB W DDDD   DDDD W BB",
    "    BB W DDDD   DDDD W BB",
    "    HA W DDPP   DDPP W AH",
    "     H W DDPP   DDPP W H ",
    "       WWWWWWWWWWWWW     ",
    "       WWWWWWWWWWWWW WW  ",
    "       WWWWWWWWWWWWW WWW ",
    "       WWWWWWWWWWWWW WW  ",
    "       WWWWWWWWWWWWW     ",
    "       WWWWWWWWWWWWW     ",
    "       GWWWWWWWWWWWG     ",
    "        WWW  WWW  WWW    ",
    "         WW   WW   WW    ",
    "          W    W    W    ",
    "                         ",
]

PLAY_HOP = [
    "        HHHHHHHHH        ",
    "      HH         HH      ",
    "     H   WWWWWWW   H     ",
    "    H  WWWWWWWWWWW  H    ",
    "   A  WWWWWWWWWWWWW  A   ",
    "   AA WWWWWWWWWWWWW AA   ",
    "   AA WWWWWWWWWWWWW AA   ",
    "   BB W ^^^^   ^^^^ W BB ",
    "   BB W SSSS   SSSS W BB ",
    "   HA W PPPP   PPPP W AH ",
    "    H W             W H  ",
    "      WWWWWWWWWWWWW      ",
    "  WWW WWWWWWWWWWWWW WWW  ",
    "   WW WWWWWWWWWWWWW WW   ",
    "      WWWWWWWWWWWWW      ",
    "      WWWWWWWWWWWWW      ",
    "      WWWWWWWWWWWWW      ",
    "      GWWWWWWWWWWWG      ",
    "       WWW  WWW  WWW     ",
    "        WW   WW   WW     ",
    "                         ",
    "                         ",
]

# --- PAUSED / NAP FRAMES ---
PAUSED_F0 = [
    "        HHHHHHHHH        ",
    "      HH         HH      ",
    "     H   WWWWWWW   H     ",
    "    H  WWWWWWWWWWW  H    ",
    "   B  WWWWWWWWWWWWW  B   ",
    "   BB WWWWWWWWWWWWW BB   ",
    "   BB WWWWWWWWWWWWW BB   ",
    "   H  W             W  H ",
    "   H  W ----   ---- W  H ",
    "      W DDPP   DDPP W    ",
    "      W             W    ",
    "      WWWWWWWWWWWWW      ",
    "   WW WWWWWWWWWWWWW      ",
    "  WWW WWWWWWWWWWWWW      ",
    "   WW WWWWWWWWWWWWW      ",
    "      WWWWWWWWWWWWW      ",
    "      WWWWWWWWWWWWW      ",
    "      GWWWWWWWWWWWG      ",
    "       WWW  WWW  WWW     ",
    "       WW   WW    WW     ",
    "       W          W      ",
    "                         ",
]

PAUSED_F1 = [
    "                         ",
    "        HHHHHHHHH        ",
    "      HH         HH      ",
    "     H   WWWWWWW   H     ",
    "    H  WWWWWWWWWWW  H    ",
    "   B  WWWWWWWWWWWWW  B   ",
    "   BB WWWWWWWWWWWWW BB   ",
    "   BB WWWWWWWWWWWWW BB   ",
    "   H  W ~~~~   ~~~~ W  H ",
    "   H  W DDPP   DDPP W  H ",
    "      W             W    ",
    "      WWWWWWWWWWWWW      ",
    "   WW WWWWWWWWWWWWW      ",
    "  WWW WWWWWWWWWWWWW      ",
    "   WW WWWWWWWWWWWWW      ",
    "      WWWWWWWWWWWWW      ",
    "      WWWWWWWWWWWWW      ",
    "      GWWWWWWWWWWWG      ",
    "       WWW  WWW  WWW     ",
    "       WW   WW    WW     ",
    "       W          W      ",
    "                         ",
]

# --- TRACK CHANGE / PERK UP ---
TRACK_CHANGE_SURPRISE = [
    "        HHHHHHHHH        ",
    "      HH  AAAAA  HH      ",
    "     H   WWWWWWW   H     ",
    "    H  WWWWWWWWWWW  H    ",
    "   A  WWWWWWWWWWWWW  A   ",
    "   AA WWWWWWWWWWWWW AA   ",
    "   AA W ****   **** W AA ",
    "   BB W ****   **** W BB ",
    "   BB W DDPP   DDPP W BB ",
    "   HA W             W AH ",
    "    H WWWWWWWWWWWWW   H  ",
    "  WWW WWWWWWWWWWWWW WWW  ",
    "  WWW WWWWWWWWWWWWW WWW  ",
    "      WWWWWWWWWWWWW      ",
    "      WWWWWWWWWWWWW      ",
    "      WWWWWWWWWWWWW      ",
    "      GWWWWWWWWWWWG      ",
    "       WWW  WWW  WWW     ",
    "      WW    WW     WW    ",
    "     W      W       W    ",
    "                         ",
    "                         ",
]

# --- SEEKING / DASH ---
SEEK_DASH = [
    "         HHHHHHHHH       ",
    "       HH         HH     ",
    "      H   WWWWWWW   H    ",
    "     H  WWWWWWWWWWW  H   ",
    "  - A  WWWWWWWWWWWWW  A  ",
    " -- AA WWWWWWWWWWWWW AA  ",
    " -  AA W >>>>   <<<< W AA",
    " -- BB W >>>>   <<<< W BB",
    " -  BB W DDPP   DDPP W BB",
    "    HA W             W AH",
    "     H WWWWWWWWWWWWW   H ",
    "       WWWWWWWWWWWWW     ",
    "       WWWWWWWWWWWWW     ",
    "       WWWWWWWWWWWWW     ",
    "       GWWWWWWWWWWWG     ",
    "        WWW  WWW  WWW    ",
    "       WW    WW    WW    ",
    "      W      W      W    ",
    "                         ",
    "                         ",
    "                         ",
    "                         ",
]

# --- VOLUME UP (EXCITED) ---
VOL_UP_F0 = [
    "   AA   HHHHHHHHH   AA   ",
    "      HH  AAAAA  HH      ",
    "     H   WWWWWWW   H     ",
    "    H  WWWWWWWWWWW  H    ",
    "   A  WWWWWWWWWWWWW  A   ",
    "   AA WWWWWWWWWWWWW AA   ",
    "   AA W ^^^^   ^^^^ W AA ",
    "   BB W SSSS   SSSS W BB ",
    "   BB W PPPP   PPPP W BB ",
    "   HA W             W AH ",
    "    H WWWWWWWWWWWWW   H  ",
    "  WWW WWWWWWWWWWWWW WWW  ",
    "  WWW WWWWWWWWWWWWW WWW  ",
    "   WW WWWWWWWWWWWWW WW   ",
    "      WWWWWWWWWWWWW      ",
    "      WWWWWWWWWWWWW      ",
    "      GWWWWWWWWWWWG      ",
    "       WWW  WWW  WWW     ",
    "      WW    WW     WW    ",
    "     W      W       W    ",
    "                         ",
    "                         ",
]

# --- SLEEPING / IDLE (no song detected) ---
SLEEP_F0 = [
    "        HHHHHHHHH        ",
    "      HH         HH      ",
    "     H   WWWWWWW   H     ",
    "    H  WWWWWWWWWWW  H    ",
    "   B  WWWWWWWWWWWWW  B   ",
    "   BB WWWWWWWWWWWWW BB   ",
    "   BB WWWWWWWWWWWWW BB   ",
    "   H  W ----   ---- W  H ",
    "   H  W DDPP   DDPP W  H ",
    "      W             W    ",
    "      WWWWWWWWWWWWW      ",
    "   WW WWWWWWWWWWWWW      ",
    "  WWW WWWWWWWWWWWWW      ",
    "   WW WWWWWWWWWWWWW      ",
    "   z  WWWWWWWWWWWWW      ",
    "      WWWWWWWWWWWWW      ",
    "      GWWWWWWWWWWWG      ",
    "       WWW  WWW  WWW     ",
    "       WW   WW    WW     ",
    "       W          W      ",
    "                         ",
    "                         ",
]

SLEEP_F1 = [
    "        HHHHHHHHH        ",
    "      HH         HH      ",
    "     H   WWWWWWW   H     ",
    "    H  WWWWWWWWWWW  H    ",
    "   B  WWWWWWWWWWWWW  B   ",
    "   BB WWWWWWWWWWWWW BB   ",
    "   BB WWWWWWWWWWWWW BB   ",
    "   H  W ~~~~   ~~~~ W  H ",
    "   H  W DDPP   DDPP W  H ",
    "      W             W    ",
    "      WWWWWWWWWWWWW      ",
    "   WW WWWWWWWWWWWWW      ",
    "  zWW WWWWWWWWWWWWW      ",
    "   WW WWWWWWWWWWWWW      ",
    "      WWWWWWWWWWWWW      ",
    "      WWWWWWWWWWWWW      ",
    "      GWWWWWWWWWWWG      ",
    "       WWW  WWW  WWW     ",
    "       WW   WW    WW     ",
    "       W          W      ",
    "                         ",
    "                         ",
]

SLEEP_F2 = [
    "        HHHHHHHHH        ",
    "      HH         HH      ",
    "     H   WWWWWWW   H     ",
    "    H  WWWWWWWWWWW  H    ",
    "   B  WWWWWWWWWWWWW  B   ",
    "   BB WWWWWWWWWWWWW BB   ",
    "   BB WWWWWWWWWWWWW BB   ",
    "   H  W ~~~~   ~~~~ W  H ",
    "   H  W DDPP   DDPP W  H ",
    "      W             W    ",
    "   z  WWWWWWWWWWWWW      ",
    "   WW WWWWWWWWWWWWW      ",
    "  WWW WWWWWWWWWWWWW      ",
    "   WW WWWWWWWWWWWWW      ",
    "      WWWWWWWWWWWWW      ",
    "      WWWWWWWWWWWWW      ",
    "      GWWWWWWWWWWWG      ",
    "       WWW  WWW  WWW     ",
    "       WW   WW    WW     ",
    "       W          W      ",
    "                         ",
    "                         ",
]

# --- VOLUME DOWN (COVERS EARS) ---
VOL_DOWN_F0 = [
    "        HHHHHHHHH        ",
    "      HH         HH      ",
    "     H   WWWWWWW   H     ",
    "    H  WWWWWWWWWWW  H    ",
    "   B  WWWWWWWWWWWWW  B   ",
    "  WW  WWWWWWWWWWWWW  WW  ",
    "  WW  W >>>>   <<<< W  WW",
    "  WW  W >>>>   <<<< W  WW",
    "   W  W DDPP   DDPP W  W ",
    "      W             W    ",
    "      WWWWWWWWWWWWW      ",
    "      WWWWWWWWWWWWW      ",
    "      WWWWWWWWWWWWW      ",
    "      WWWWWWWWWWWWW      ",
    "      WWWWWWWWWWWWW      ",
    "      GWWWWWWWWWWWG      ",
    "       WWW  WWW  WWW     ",
    "       WW   WW    WW     ",
    "       W          W      ",
    "                         ",
    "                         ",
    "                         ",
]


class FrameLibrary:
    """Manages raw ASCII frames and renders PixelSprites with dynamic colors."""

    @classmethod
    def get_color_map(cls, accent_color: RGBColor | None = None) -> Dict[str, Pixel]:
        acc = accent_color or A
        # Slightly darker shade for inner rim
        rim = (max(0, acc[0] - 40), max(0, acc[1] - 40), max(0, acc[2] - 40))
        return {
            " ": _,
            "W": W,
            "G": G,
            "D": D,
            "S": S,
            "P": P,
            "H": H,
            "A": acc,
            "B": rim,
            "^": D,
            "-": D,
            "~": D,
            "*": acc,
            "O": D,
            ">": D,
            "<": D,
            "z": acc,   # zzz sleep bubbles use accent color
        }

    @classmethod
    def create_sprite(
        cls,
        ascii_lines: List[str],
        accent_color: RGBColor | None = None,
    ) -> PixelSprite:
        cmap = cls.get_color_map(accent_color)
        return PixelSprite.from_ascii(ascii_lines, cmap)


# Animation sequences as list of frame templates
ANIMATIONS: Dict[str, List[List[str]]] = {
    "idle": [IDLE_F0, IDLE_F1, IDLE_BLINK, IDLE_F1],
    "sleeping": [SLEEP_F0, SLEEP_F1, SLEEP_F2, SLEEP_F1, SLEEP_F0],
    "playing": [PLAY_BOB_DOWN, PLAY_SWAY_LEFT, PLAY_BOB_DOWN, PLAY_SWAY_RIGHT, PLAY_HOP, IDLE_F0],
    "paused": [PAUSED_F0, PAUSED_F1, PAUSED_F0, PAUSED_F1],
    "track_change": [TRACK_CHANGE_SURPRISE, PLAY_HOP, TRACK_CHANGE_SURPRISE, IDLE_F0],
    "seeking": [SEEK_DASH, PLAY_BOB_DOWN, SEEK_DASH],
    "vol_up": [VOL_UP_F0, PLAY_HOP, VOL_UP_F0, IDLE_F0],
    "vol_down": [VOL_DOWN_F0, PAUSED_F0, VOL_DOWN_F0],
}
