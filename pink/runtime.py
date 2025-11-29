from __future__ import annotations

import shutil
import sys
from typing import List

CSI = "\x1b["
# Match Ink's clearTerminal (ansi-escapes): clear screen, clear scrollback, home cursor.
CLEAR_TERMINAL = CSI + "2J" + CSI + "3J" + CSI + "H"
CURSOR_HOME = CSI + "H"
HIDE_CURSOR = CSI + "?25l"
SHOW_CURSOR = CSI + "?25h"


class Renderer:
    """Render text blocks with ink-style redraw semantics."""

    def __init__(self) -> None:
        self._cursor_hidden = False
        self._inline_mode = True
        # Row (0-based) of where we leave the cursor relative to our render block.
        self._inline_anchor_row: int | None = None

    def present(
        self,
        lines: List[str],
        caret: tuple[int, int] | None = None,
        place_cursor_after: bool = False,
    ) -> None:
        if not lines:
            lines = [""]

        hide_cursor = caret is None
        if hide_cursor and not self._cursor_hidden:
            sys.stdout.write(HIDE_CURSOR)
            self._cursor_hidden = True
        if not hide_cursor and self._cursor_hidden:
            sys.stdout.write(SHOW_CURSOR)
            self._cursor_hidden = False

        rows = shutil.get_terminal_size(fallback=(80, 24)).lines
        rows = max(1, rows)
        content_height = len(lines)

        if self._inline_mode and content_height > rows:
            self._inline_mode = False
            self._inline_anchor_row = None

        if self._inline_mode:
            self._render_inline(lines, caret, place_cursor_after)
        else:
            self._render_fullscreen(lines, caret, place_cursor_after, rows)

        sys.stdout.flush()

    def close(self) -> None:
        if self._cursor_hidden:
            sys.stdout.write(SHOW_CURSOR)
            sys.stdout.flush()
            self._cursor_hidden = False

    def _render_fullscreen(
        self,
        lines: List[str],
        caret: tuple[int, int] | None,
        place_cursor_after: bool,
        rows: int,
    ) -> None:
        text = "\r\n".join(lines)
        # Clear screen + scrollback, then redraw full content.
        sys.stdout.write(CLEAR_TERMINAL)
        sys.stdout.write(text)

        if caret is not None and not place_cursor_after:
            row, col = caret
            visible_start = max(0, len(lines) - rows)
            row = max(0, row - visible_start)
            row = min(rows - 1, row)
            sys.stdout.write(CSI + f"{row + 1};{col + 1}H")
        elif place_cursor_after:
            target_row = rows - 1 if len(lines) >= rows else len(lines) - 1
            target_row = max(0, target_row)
            sys.stdout.write(CSI + f"{target_row + 1};1H")

    def _render_inline(
        self,
        lines: List[str],
        caret: tuple[int, int] | None,
        place_cursor_after: bool,
    ) -> None:
        # Move back to the start of our render block based on where we left the cursor.
        if self._inline_anchor_row is not None:
            sys.stdout.write("\r")
            if self._inline_anchor_row:
                sys.stdout.write(CSI + f"{self._inline_anchor_row}A")

        # Clear everything from the cursor down so we don't trample content above.
        sys.stdout.write(CSI + "0J")

        text = "\r\n".join(lines)
        sys.stdout.write(text)

        height = len(lines)
        target_row: int
        target_col: int
        if caret is not None and not place_cursor_after:
            target_row, target_col = caret
        elif place_cursor_after:
            target_row = max(0, height - 1)
            target_col = 0
        else:
            target_row = max(0, height - 1)
            target_col = 0

        # Move cursor to requested position relative to the start of the block.
        sys.stdout.write("\r")
        if height > 1:
            sys.stdout.write(CSI + f"{height - 1}A")
        if target_row > 0:
            sys.stdout.write(CSI + f"{target_row}B")
        sys.stdout.write(CSI + f"{target_col + 1}G")

        self._inline_anchor_row = target_row
