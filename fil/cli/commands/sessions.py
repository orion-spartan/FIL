import typer
from rich.table import Table

from fil.shared.console import console


def register(app: typer.Typer) -> None:
    sessions_app = typer.Typer(help="Inspect and manage FIL sessions.")

    @sessions_app.command("list")
    def list_sessions() -> None:
        """Lists known sessions."""
        table = Table(title="Sessions")
        table.add_column("ID")
        table.add_column("Type")
        table.add_column("Status")
        table.add_column("Updated")
        console.print(table)
        console.print("[dim]No sessions stored yet.[/dim]")

    @sessions_app.command("show")
    def show_session(session_id: str = typer.Argument(..., help="Session identifier")) -> None:
        """Shows a single session."""
        console.print(f"[bold]Session:[/bold] {session_id}")
        console.print("[yellow]Session storage is not connected yet.[/yellow]")

    app.add_typer(sessions_app, name="sessions")
