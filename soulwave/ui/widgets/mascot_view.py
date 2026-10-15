"""Mascot and room atmosphere widget."""

from __future__ import annotations

from textual.widget import Widget
from rich.text import Text

from ...mascot.animator import MascotAnimator
from ...mascot.scene import RoomScene
from ...theme.dynamic import RGB


class MascotView(Widget):
    """Textual widget rendering the animated Soul mascot and room scene."""

    DEFAULT_CSS = """
    MascotView {
        width: 38;
        height: 15;
        content-align: center middle;
        padding: 0 1;
    }
    """

    def __init__(
        self,
        animator: MascotAnimator,
        scene: RoomScene,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self.animator = animator
        self.scene = scene
        self.accent_color: RGB | None = None

    def render(self) -> Text:
        sprite = self.animator.tick()
        # Compose frame inside room scene
        return self.scene.compose_frame(sprite, self.accent_color)
