import codecs
import sys
import termios
import time
import tty
from contextlib import contextmanager

from pink import App, Input, Panel, Text


@contextmanager
def raw_mode(fd):
    old_settings = termios.tcgetattr(fd)
    tty.setraw(fd)
    try:
        yield
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


class Demo(App):
    def __init__(self) -> None:
        super().__init__()
        self.lines = 10
        self.input = Input(width=None)

    def compose(self):
        return [
            Panel(
                [Text(f"Line {index + 1}") for index in range(self.lines)],
                title="pink demo",
                padding=1,
            ),
            self.input,
        ]


def main():
    app = Demo()
    decoder = codecs.getincrementaldecoder("utf-8")()
    try:
        if not sys.stdin.isatty():
            count = 1
            while True:
                app.lines = count
                app.refresh()
                count += 1
                time.sleep(1)
            return

        count = 1

        with raw_mode(sys.stdin.fileno()):
            while True:
                app.lines = count
                app.refresh()
                count += 1
                b = sys.stdin.buffer.read(1)
                if not b:
                    break

                if b == b"\x1b":
                    seq = b + sys.stdin.buffer.read(2)
                    if seq == b"\x1b[D":
                        app.input.move_left()
                        continue
                    if seq == b"\x1b[C":
                        app.input.move_right()
                        continue
                    # Unknown escape sequence, ignore.
                    continue

                ch = decoder.decode(b, final=False)
                if ch == "":
                    continue
                if ch in ("\r", "\n"):
                    break
                if ch == "\x03":  # Ctrl+C
                    break
                if ch in ("\x7f", "\b"):
                    app.input.backspace()
                else:
                    app.input.insert(ch)
    finally:
        app.refresh(place_cursor_after=True)
        app.stop()
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()
