from __future__ import annotations

from typing import Iterable

from .components import Component, RenderResult, Renderable, render_to_lines
from .runtime import Renderer


class App:
    """Simple pink application base."""

    def __init__(self) -> None:
        self._renderer = Renderer()

    def compose(self) -> Renderable | Iterable[Renderable]:
        """Override to return your view tree."""
        return []

    def render(
        self,
        caret: tuple[int, int] | None = None,
        place_cursor_after: bool = False,
    ) -> None:
        tree = self.compose()
        result: RenderResult = render_to_lines(tree)
        caret_to_use = caret if caret is not None else result.caret
        self._renderer.present(result.lines, caret_to_use, place_cursor_after)

    def refresh(
        self,
        caret: tuple[int, int] | None = None,
        place_cursor_after: bool = False,
    ) -> None:
        """Alias for render, mirrors ink's update wording."""
        self.render(caret, place_cursor_after)

    def stop(self) -> None:
        self._renderer.close()
