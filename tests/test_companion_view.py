"""Unit tests for CompanionDanceView dancing mini-mascots."""

from soulwave.ui.widgets.companion_view import CompanionDanceView


def test_companion_view_init():
    comp = CompanionDanceView()
    assert comp.is_playing is False
    assert comp.is_paused is False
    assert comp.energy == 0.0


def test_companion_view_states():
    comp = CompanionDanceView()

    # Playing state with high energy
    comp.update_state(is_playing=True, is_paused=False, accent=(255, 100, 150), energy=0.8)
    assert comp.is_playing is True
    assert comp.energy == 0.8
    render_play = comp.render().plain
    assert "COMPANIONS" in render_play
    assert "sleepy soul" not in render_play.lower()
    assert "gentle soul" not in render_play.lower()
    assert "grooving with the beat" not in render_play.lower()

    # Paused state
    comp.update_state(is_playing=False, is_paused=True, accent=(255, 100, 150), energy=0.0)
    assert comp.is_paused is True
    render_paused = comp.render().plain
    assert "resting calmly" not in render_paused.lower()

    # Idle / sleeping state
    comp.update_state(is_playing=False, is_paused=False, accent=(255, 100, 150), energy=0.0)
    render_idle = comp.render().plain
    assert "fast asleep" not in render_idle.lower()


def test_companion_view_compact_size():
    comp = CompanionDanceView()
    # When widget size is small (e.g. height=5, width=28)
    comp._test_height = 5
    comp._test_width = 28
    comp.update_state(is_playing=True, is_paused=False, accent=(56, 189, 248))
    rendered = comp.render().plain
    assert "COMPANIONS" in rendered
    assert "▀" in rendered or "▄" in rendered


def test_companion_view_minimal_and_pixel_art():
    """Verify that companion view is minimal, text subtitles are removed, and pixel-art renders cleanly."""
    comp = CompanionDanceView()
    comp._test_height = 12
    comp._test_width = 56
    comp.update_state(is_playing=True, is_paused=False, accent=(56, 189, 248), energy=0.5)

    rendered = comp.render().plain

    # Texts must be removed
    assert "The gentle soul" not in rendered
    assert "The energetic soul" not in rendered
    assert "The sleepy soul" not in rendered
    assert "Grooving with the beat" not in rendered
    assert "Fast asleep" not in rendered

    # Half-block characters from PixelSprite
    assert "▀" in rendered or "▄" in rendered

    # Clean name tags present
    assert "Pip" in rendered
    assert "Nova" in rendered
    assert "Mochi" in rendered
