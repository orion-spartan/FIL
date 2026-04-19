from __future__ import annotations

from datetime import datetime

from rich.panel import Panel
from rich.table import Table

from fil.domain.models.session import Session, SessionStatus


def _format_elapsed(started_at: datetime, now: datetime) -> str:
    elapsed = max(int((now - started_at).total_seconds()), 0)
    hours, remainder = divmod(elapsed, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def _state_style(status: SessionStatus | str) -> str:
    if status == SessionStatus.RUNNING:
        return "bold red"
    if status == SessionStatus.FAILED:
        return "bold yellow"
    return "bold green"


def render_session_status(session: Session | None, now: datetime | None = None) -> Panel:
    now = now or datetime.utcnow()
    table = Table.grid(padding=(0, 1))
    table.add_column(style="bold")
    table.add_column()

    if session is None:
        table.add_row("State", "inactive")
        table.add_row("Session", "none")
        return Panel(table, title="FIL Watch", border_style="cyan")

    table.add_row("State", f"[{_state_style(session.status)}]{session.status.value}[/{_state_style(session.status)}]")
    table.add_row("Session", f"[cyan]{session.id}[/cyan]")
    table.add_row("Type", session.type.value)
    table.add_row("Started", session.created_at.isoformat(timespec="seconds"))
    table.add_row("Elapsed", _format_elapsed(session.created_at, now))

    if session.recorder_pid is not None:
        table.add_row("PID", str(session.recorder_pid))
    if session.audio_path:
        table.add_row("Audio", session.audio_path)
    if session.error_message:
        table.add_row("Error", session.error_message)

    return Panel(table, title="FIL Watch", border_style="cyan")
