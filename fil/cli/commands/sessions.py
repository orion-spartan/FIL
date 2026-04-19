import typer
from rich.panel import Panel
from rich.table import Table

from fil.application.services.runtime import session_store
from fil.shared.console import console


def register(app: typer.Typer) -> None:
    sessions_app = typer.Typer(help="Inspect and manage FIL sessions.")

    @sessions_app.command("list")
    def list_sessions() -> None:
        """Lists known sessions."""
        sessions = session_store().list_sessions()
        table = Table(title="Sessions")
        table.add_column("ID")
        table.add_column("Type")
        table.add_column("Status")
        table.add_column("Updated")
        for session in sessions:
            table.add_row(
                session.id,
                session.type.value,
                session.status.value,
                session.updated_at.isoformat(timespec="seconds"),
            )
        console.print(table)
        if not sessions:
            console.print("[dim]No sessions stored yet.[/dim]")

    @sessions_app.command("show")
    def show_session(session_id: str = typer.Argument(..., help="Session identifier")) -> None:
        """Shows a single session."""
        session = session_store().get_session(session_id)
        if session is None:
            console.print(f"[red]Error:[/red] session not found: {session_id}")
            raise typer.Exit(code=1)

        body = [
            f"Type: {session.type.value}",
            f"Status: {session.status.value}",
            f"Created: {session.created_at.isoformat(timespec='seconds')}",
            f"Updated: {session.updated_at.isoformat(timespec='seconds')}",
        ]
        if session.audio_path:
            body.append(f"Audio: {session.audio_path}")
        if session.error_message:
            body.append(f"Error: {session.error_message}")
        console.print(Panel("\n".join(body), title=session.id))

    app.add_typer(sessions_app, name="sessions")
