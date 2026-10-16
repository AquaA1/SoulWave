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
    assert "COMPANIONS (GROOVE ROOM)" in render_play
    assert "Pip" in render_play
    assert "Nova" in render_play
    assert "Mochi" in render_play
    assert "Grooving with the beat" in render_play

    # Paused state
    comp.update_state(is_playing=False, is_paused=True, accent=(255, 100, 150), energy=0.0)
    assert comp.is_paused is True
    render_paused = comp.render().plain
    assert "Resting calmly" in render_paused

    # Idle / sleeping state
    comp.update_state(is_playing=False, is_paused=False, accent=(255, 100, 150), energy=0.0)
    render_idle = comp.render().plain
    assert "Fast asleep" in render_idle


def test_companion_view_compact_size():
    comp = CompanionDanceView()
    # When widget size is small (e.g. height=5, width=28)
    comp._test_height = 5
    comp._test_width = 28
    comp.update_state(is_playing=True, is_paused=False, accent=(56, 189, 248))
    rendered = comp.render().plain
    # Should render without throwing exception and contain companions
    assert "Pip" in rendered
    assert "Nova" in rendered
    assert "Mochi" in rendered
