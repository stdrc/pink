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

        text = "\r\n".join(lines)
        # Always clear screen + scrollback, then redraw full content.
        sys.stdout.write(CLEAR_TERMINAL)
        sys.stdout.write(text)

        rows = shutil.get_terminal_size(fallback=(80, 24)).lines
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

        sys.stdout.flush()

    def close(self) -> None:
        if self._cursor_hidden:
            sys.stdout.write(SHOW_CURSOR)
            sys.stdout.flush()
            self._cursor_hidden = False
