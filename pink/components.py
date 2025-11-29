from __future__ import annotations

import shutil
import unicodedata
from dataclasses import dataclass
from typing import Iterable, List, NamedTuple, Optional, Tuple, Union


class RenderResult(NamedTuple):
    lines: List[str]
    caret: Optional[Tuple[int, int]] = None  # (row, col), 0-based


class Component:
    """Base class for all pink components."""

    def render(self) -> RenderResult:
        raise NotImplementedError


Renderable = Union[Component, str, Iterable["Renderable"]]


def _text_to_lines(text: str) -> List[str]:
    lines = text.splitlines()
    return lines if lines else [""]


def _render_node(node: Renderable) -> RenderResult:
    if isinstance(node, Component):
        result = node.render()
        if isinstance(result, RenderResult):
            return result
        return RenderResult(result)
    if isinstance(node, str):
        return RenderResult(_text_to_lines(str(node)))
    if isinstance(node, Iterable):
        lines: List[str] = []
        caret: Optional[Tuple[int, int]] = None
        for child in node:
            result = _render_node(child)
            base_row = len(lines)
            lines.extend(result.lines)
            if result.caret is not None:
                caret = (base_row + result.caret[0], result.caret[1])
        return RenderResult(lines, caret)
    raise TypeError(f"Cannot render node: {node!r}")


def render_to_lines(node: Renderable) -> RenderResult:
    """Convert any renderable node into a flat list of text lines plus caret location."""
    return _render_node(node)


@dataclass
class Text(Component):
    value: str

    def render(self) -> RenderResult:
        text = "" if self.value is None else str(self.value)
        return RenderResult(_text_to_lines(text))


@dataclass
class Panel(Component):
    child: Renderable
    title: str | None = None
    padding: int = 0

    def render(self) -> RenderResult:
        child_result = render_to_lines(self.child)
        body = child_result.lines
        inner_width = max((_measure_width(line) for line in body), default=0)
        pad = max(0, int(self.padding))
        content_width = inner_width + pad * 2

        label = f" {self.title} " if self.title else ""
        content_width = max(content_width, _measure_width(label))

        top_bar = label.ljust(content_width, "-") if label else "-" * content_width

        lines: List[str] = [f"+{top_bar}+"]
        empty_row = " " * content_width
        for _ in range(pad):
            lines.append(f"|{empty_row}|")
        for line in body:
            padded_line = _pad_to_width(line, inner_width)
            padded = " " * pad + padded_line + " " * pad
            padded = padded.ljust(content_width)
            lines.append(f"|{padded}|")
        for _ in range(pad):
            lines.append(f"|{empty_row}|")
        lines.append(f"+{'-' * content_width}+")
        caret = None
        if child_result.caret is not None:
            row, col = child_result.caret
            caret = (1 + pad + row, 1 + pad + col)
        return RenderResult(lines, caret)


def _char_width(ch: str) -> int:
    if unicodedata.combining(ch):
        return 0
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 2
    return 1


def _measure_width(text: str) -> int:
    return sum(_char_width(ch) for ch in text)


def _pad_to_width(text: str, width: int) -> str:
    extra = max(0, width - _measure_width(text))
    return text + " " * extra


@dataclass
class Input(Component):
    value: str = ""
    cursor: int = 0
    width: Optional[int] = None
    bordered: bool = True
    inner_padding: int = 1

    def insert(self, text: str) -> None:
        self.value = self.value[: self.cursor] + text + self.value[self.cursor :]
        self.cursor += len(text)

    def backspace(self) -> None:
        if self.cursor > 0:
            self.value = self.value[: self.cursor - 1] + self.value[self.cursor :]
            self.cursor -= 1

    def move_left(self) -> None:
        if self.cursor > 0:
            self.cursor -= 1

    def move_right(self) -> None:
        if self.cursor < len(self.value):
            self.cursor += 1

    def _trim_to_width(self, target_width: int) -> tuple[str, int]:
        chars = list(self.value)
        widths = [_char_width(ch) for ch in chars]
        total_width = sum(widths)
        cursor_width = sum(widths[: self.cursor])
        start = 0

        while total_width > target_width:
            total_width -= widths[start]
            cursor_width -= widths[start]
            start += 1
            if cursor_width < 0:
                cursor_width = 0

        visible_chars = "".join(chars[start:])
        visible_width = _measure_width(visible_chars)
        pad_width = max(0, target_width - visible_width)
        padded = visible_chars + " " * pad_width
        return padded, cursor_width

    def render(self) -> RenderResult:
        term_cols = shutil.get_terminal_size(fallback=(80, 24)).columns
        total_inner_pad = max(0, int(self.inner_padding)) * 2
        target_width = (
            self.width
            if self.width is not None
            else max(1, term_cols - (2 if self.bordered else 0))
        )
        inner_width = max(1, target_width - total_inner_pad)
        content, cursor_col = self._trim_to_width(inner_width)
        # Apply left padding for caret placement
        padded_content = " " * max(0, int(self.inner_padding)) + content + " " * max(
            0, int(self.inner_padding)
        )
        cursor_col += max(0, int(self.inner_padding))
        if self.bordered:
            line = f"|{padded_content}|"
            bar = "+" + "-" * (target_width) + "+"
            top = bar
            bottom = top
            lines = [top, line, bottom]
            caret = (1, 1 + cursor_col)
        else:
            lines = [content]
            caret = (0, cursor_col)
        return RenderResult(lines, caret)
