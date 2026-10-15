"""Tests for CavaReader and CAVA-integrated VisualizerView."""

from soulwave.audio.cava_reader import CavaReader
from soulwave.ui.widgets.visualizer import VisualizerView
from rich.text import Text


def test_cava_reader_lifecycle():
    reader = CavaReader(num_bars=16)
    assert len(reader.bars) == 16
    assert all(b == 0.0 for b in reader.bars)

    # Config generation creates valid config file
    cfg_path = reader._write_config()
    try:
        with open(cfg_path, "r") as f:
            content = f.read()
        assert "bars = 16" in content
        assert "method = raw" in content
        assert "data_format = ascii" in content
    finally:
        import os
        if os.path.exists(cfg_path):
            os.unlink(cfg_path)


def test_visualizer_view_rendering():
    vis = VisualizerView(num_bars=24)
    # Even if CAVA is running or not running, render returns Rich Text
    vis.update_params(is_playing=True, volume=0.8, bpm=120.0, accent=(56, 189, 248))
    rendered = vis.render()
    assert isinstance(rendered, Text)
    assert len(rendered.plain) > 0

    # Paused rendering
    vis.update_params(is_playing=False, volume=0.8, bpm=120.0, accent=(56, 189, 248))
    rendered_paused = vis.render()
    assert isinstance(rendered_paused, Text)

    vis.on_unmount()
