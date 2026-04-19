from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import select
import sys
import termios
import threading
import time
import tty

import typer
from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from fil.application.services.runtime import talk_service
from fil.application.services.talk_service import TalkMode, TalkSnapshot
from fil.shared.console import console


@contextmanager
def terminal_keys():
    if not sys.stdin.isatty():
        raise RuntimeError("talk mode requires an interactive terminal")

    file_descriptor = sys.stdin.fileno()
    original_settings = termios.tcgetattr(file_descriptor)
    try:
        tty.setcbreak(file_descriptor)
        console.show_cursor(False)
        yield
    finally:
        termios.tcsetattr(file_descriptor, termios.TCSADRAIN, original_settings)
        console.show_cursor(True)


def read_key(timeout: float = 0.1) -> str | None:
    readable, _writable, _errors = select.select([sys.stdin], [], [], timeout)
    if not readable:
        return None
    return sys.stdin.read(1)


def _elapsed(started_at: datetime | None) -> str:
    if started_at is None:
        return "00:00"
    seconds = max(int((datetime.utcnow() - started_at).total_seconds()), 0)
    minutes, remainder = divmod(seconds, 60)
    return f"{minutes:02}:{remainder:02}"


def _mode_label(mode: TalkMode) -> str:
    labels = {
        TalkMode.IDLE: "idle",
        TalkMode.LISTENING: "listening",
        TalkMode.FINALIZING: "finalizing audio",
        TalkMode.TRANSCRIBING: "transcribing",
        TalkMode.COPYING: "copying to clipboard",
        TalkMode.DONE: "done",
        TalkMode.ERROR: "error",
    }
    return labels[mode]


def _clipboard_label(snapshot: TalkSnapshot) -> str:
    if snapshot.mode == TalkMode.COPYING:
        return "pending"
    if snapshot.copied_to_clipboard:
        return "copied"
    if snapshot.clipboard_error:
        return f"failed: {snapshot.clipboard_error}"
    return "idle"


def _controls_label(snapshot: TalkSnapshot, exiting: bool) -> str:
    if exiting:
        return "finishing current utterance, then quitting"
    if snapshot.mode == TalkMode.LISTENING:
        return "Space stop, q cancel and quit"
    if snapshot.mode in {TalkMode.FINALIZING, TalkMode.TRANSCRIBING, TalkMode.COPYING}:
        return "processing current utterance... q will quit when done"
    return "Space start/stop, q quit"


def render_talk(snapshot: TalkSnapshot, *, exiting: bool = False):
    status = Table.grid(padding=(0, 1))
    status.add_column(style="bold")
    status.add_column()
    status.add_row("Controls", _controls_label(snapshot, exiting))
    status.add_row("Mode", _mode_label(snapshot.mode))
    status.add_row("Persistence", "ephemeral (not saved)")
    status.add_row("Clipboard", _clipboard_label(snapshot))
    status.add_row("Status", snapshot.status_message)
    if snapshot.mode in {TalkMode.LISTENING, TalkMode.FINALIZING, TalkMode.TRANSCRIBING, TalkMode.COPYING}:
        status.add_row("Elapsed", _elapsed(snapshot.started_at))

    transcript_title = "Live Transcript"
    transcript_body = ""
    if snapshot.mode == TalkMode.LISTENING:
        transcript_body = snapshot.partial_transcript or "listening..."
    elif snapshot.mode in {TalkMode.FINALIZING, TalkMode.TRANSCRIBING, TalkMode.COPYING}:
        transcript_body = snapshot.partial_transcript or "processing current utterance..."
    elif snapshot.mode == TalkMode.ERROR:
        transcript_title = "Error"
        transcript_body = snapshot.error_message or "unknown error"
    else:
        transcript_title = "Final Transcript"
        transcript_body = snapshot.final_transcript or "ready"

    return Group(
        Panel(status, title="FIL Talk", border_style="cyan"),
        Panel(transcript_body, title=transcript_title, border_style="green" if snapshot.mode != TalkMode.ERROR else "red"),
    )


def run_talk() -> None:
    service = talk_service()
    stop_thread: threading.Thread | None = None
    stop_error: RuntimeError | None = None
    exit_after_processing = False

    def stop_worker() -> None:
        nonlocal stop_error
        try:
            service.stop()
        except RuntimeError as exc:
            stop_error = exc

    try:
        with terminal_keys(), Live(render_talk(service.snapshot()), console=console, refresh_per_second=10) as live:
            while True:
                snapshot = service.snapshot()
                live.update(render_talk(snapshot, exiting=exit_after_processing))

                if stop_thread is not None and not stop_thread.is_alive():
                    stop_thread = None
                    if stop_error is not None:
                        error = stop_error
                        stop_error = None
                        raise error
                    if exit_after_processing and snapshot.mode in {TalkMode.IDLE, TalkMode.DONE, TalkMode.ERROR}:
                        break

                key = read_key(0.1)
                if key is None:
                    continue
                if key == " ":
                    if snapshot.mode in {TalkMode.IDLE, TalkMode.DONE, TalkMode.ERROR} and stop_thread is None:
                        exit_after_processing = False
                        service.start()
                    elif snapshot.mode == TalkMode.LISTENING and stop_thread is None:
                        stop_error = None
                        stop_thread = threading.Thread(target=stop_worker, name="fil-talk-stop", daemon=True)
                        stop_thread.start()
                elif key in {"q", "Q", "\x03"}:
                    if snapshot.mode == TalkMode.LISTENING:
                        service.cancel()
                        break
                    if snapshot.mode in {TalkMode.FINALIZING, TalkMode.TRANSCRIBING, TalkMode.COPYING}:
                        exit_after_processing = True
                        continue
                    break
        console.print("[dim]talk stopped[/dim]")
    except RuntimeError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc


def register(app: typer.Typer) -> None:
    @app.command("t")
    def talk_short() -> None:
        """Interactive low-latency talk mode for short commands."""
        run_talk()

    @app.command("talk")
    def talk() -> None:
        """Interactive low-latency talk mode for short commands."""
        run_talk()
