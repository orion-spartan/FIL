from __future__ import annotations

from contextlib import contextmanager
import select
import sys
import termios
import time
import tty

from fil.shared.console import console


@contextmanager
def terminal_keys(*, require_tty: bool = False, hide_cursor: bool = True):
    if not sys.stdin.isatty():
        if require_tty:
            raise RuntimeError("interactive mode requires an interactive terminal")
        yield
        return

    file_descriptor = sys.stdin.fileno()
    original_settings = termios.tcgetattr(file_descriptor)
    try:
        tty.setcbreak(file_descriptor)
        if hide_cursor:
            console.show_cursor(False)
        yield
    finally:
        termios.tcsetattr(file_descriptor, termios.TCSADRAIN, original_settings)
        if hide_cursor:
            console.show_cursor(True)


def read_key(timeout: float = 0.1) -> str | None:
    if not sys.stdin.isatty():
        time.sleep(timeout)
        return None

    readable, _writable, _errors = select.select([sys.stdin], [], [], timeout)
    if not readable:
        return None
    return sys.stdin.read(1)


def is_quit_key(key: str | None) -> bool:
    return key in {"q", "Q", "\x03"}
