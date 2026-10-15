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
