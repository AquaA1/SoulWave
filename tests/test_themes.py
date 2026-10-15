"""Tests for themes and dynamic song accent colors."""

from soulwave.theme.palettes import THEMES, get_theme, cycle_theme_name
from soulwave.theme.dynamic import get_song_accent_color


def test_theme_retrieval():
    assert len(THEMES) >= 6
    for key in ["night", "sunset", "mint", "sakura", "cyberpunk", "mono"]:
        assert key in THEMES

    t = get_theme("sunset")
    assert t.name == "Sunset"

    fallback = get_theme("non_existent_theme")
    assert fallback.name == "Night"


def test_cycle_theme_name():
    curr = "night"
    next_theme = cycle_theme_name(curr)
    assert next_theme != curr
    assert next_theme in THEMES


def test_dynamic_song_accent():
    col1 = get_song_accent_color("Yellow", "Coldplay")
    assert len(col1) == 3
    # Check RGB range
    assert all(0 <= c <= 255 for c in col1)

    # Determinism
    col2 = get_song_accent_color("Yellow", "Coldplay")
    assert col1 == col2

    # Different song -> different color
    col3 = get_song_accent_color("Bohemian Rhapsody", "Queen")
    assert col1 != col3
