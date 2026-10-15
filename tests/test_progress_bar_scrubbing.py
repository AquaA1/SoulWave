"""Tests for ProgressBarView mouse scrubbing, coalescing on release, and visual feedback."""

import pytest
from textual.app import App, ComposeResult
from textual.events import MouseDown, MouseMove, MouseUp, Click
from soulwave.ui.widgets.progress_bar import ProgressBarView


class ScrubTestApp(App):
    def __init__(self):
        super().__init__()
        self.bar = ProgressBarView(id="progress-bar")
        self.seek_events = []

    def compose(self) -> ComposeResult:
        yield self.bar

    def on_progress_bar_view_seek_requested(self, message: ProgressBarView.SeekRequested) -> None:
        self.seek_events.append(message.target_seconds)


@pytest.mark.asyncio
async def test_mouse_scrubbing_coalesces_on_release():
    app = ScrubTestApp()

    async with app.run_test(size=(80, 5)) as pilot:
        # Duration: 120 seconds, current position 10.0s
        app.bar.update_progress(10.0, 120.0, (56, 189, 248))
        await pilot.pause(0.05)

        assert app.bar.position == 10.0
        assert not app.bar._is_dragging
        assert len(app.seek_events) == 0

        # 1. Mouse down at x=20 (middle of the bar)
        down_evt = MouseDown(
            widget=app.bar,
            x=20,
            y=0,
            delta_x=0,
            delta_y=0,
            button=1,
            shift=False,
            meta=False,
            ctrl=False,
        )
        app.bar.on_mouse_down(down_evt)
        assert app.bar._is_dragging is True
        assert app.bar._drag_target is not None
        # Must NOT dispatch any SeekRequested on mouse down
        assert len(app.seek_events) == 0

        drag_pos1 = app.bar._drag_target

        # 2. Mouse move to x=30, x=40, x=50
        for x in [30, 40, 50]:
            move_evt = MouseMove(
                widget=app.bar,
                x=x,
                y=0,
                delta_x=10,
                delta_y=0,
                button=1,
                shift=False,
                meta=False,
                ctrl=False,
            )
            app.bar.on_mouse_move(move_evt)
            # Must NOT dispatch any SeekRequested during movement
            assert len(app.seek_events) == 0

        # Visual thumb must reflect x=50
        drag_pos_final = app.bar._drag_target
        assert drag_pos_final > drag_pos1

        # 3. Mouse up at x=50 (release)
        up_evt = MouseUp(
            widget=app.bar,
            x=50,
            y=0,
            delta_x=0,
            delta_y=0,
            button=1,
            shift=False,
            meta=False,
            ctrl=False,
        )
        app.bar.on_mouse_up(up_evt)

        # Dragging ended
        assert app.bar._is_dragging is False
        assert app.bar._drag_target is None

        # Give Textual message loop a moment to deliver SeekRequested
        await pilot.pause(0.05)

        # Exactly ONE SeekRequested was dispatched (coalesced!)
        assert len(app.seek_events) == 1
        assert abs(app.seek_events[0] - drag_pos_final) < 0.1
