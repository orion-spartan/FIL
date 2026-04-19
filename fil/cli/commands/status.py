import typer

from fil.application.services.runtime import listen_service
from fil.shared.console import console


def register(app: typer.Typer) -> None:
    @app.command("status")
    def status() -> None:
        """Shows current FIL status."""
        active_session = listen_service().get_active_session()
        if active_session is None:
            console.print("[bold]Status:[/bold] no active session")
            return

        console.print(f"[bold]Status:[/bold] active {active_session.type.value} session")
        console.print(f"Session ID: [cyan]{active_session.id}[/cyan]")
        console.print(f"State: [yellow]{active_session.status.value}[/yellow]")
        if active_session.audio_path:
            console.print(f"Audio file: [cyan]{active_session.audio_path}[/cyan]")
