"""Tests for audio visualizer."""

from soulwave.audio.visualizer import AudioVisualizer


def test_visualizer_initialization():
    vis = AudioVisualizer(num_bars=20)
    assert len(vis.levels) == 20
    assert len(vis.peaks) == 20


def test_visualizer_tick_playing():
    vis = AudioVisualizer(num_bars=16)
    rich_text = vis.tick(is_playing=True, volume=0.8, bpm=120.0, accent_color=(255, 100, 150))
    assert rich_text is not None
    # Level should have moved from 0.0
    assert any(lvl > 0.0 for lvl in vis.levels)


def test_visualizer_tick_paused_decay():
    vis = AudioVisualizer(num_bars=10)
    vis.levels = [0.8] * 10
    vis.tick(is_playing=False, volume=0.8, bpm=100.0)
    # Should decay
    assert all(lvl < 0.8 for lvl in vis.levels)


def test_visualizer_height_and_degradation():
    assert AudioVisualizer.DEFAULT_HEIGHT == 2

    vis = AudioVisualizer(num_bars=16)
    # Multi-row render (height=2)
    rendered_2 = vis.tick(is_playing=True, volume=1.0, bpm=120.0, height=2)
    lines_2 = rendered_2.plain.split("\n")
    assert len(lines_2) == 2
    # Width / bar count check: each bar + space = 32 chars
    assert len(lines_2[0].strip().replace(" ", "")) <= 16

    # Graceful degradation to single-row (height=1)
    rendered_1 = vis.tick(is_playing=True, volume=1.0, bpm=120.0, height=1)
    lines_1 = rendered_1.plain.split("\n")
    assert len(lines_1) == 1
