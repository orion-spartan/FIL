import typer

from fil.shared.console import console


def register(app: typer.Typer) -> None:
    @app.command("status")
    def status() -> None:
        """Shows current FIL status."""
        console.print("[bold]Status:[/bold] no active session")
        console.print("[dim]Storage and session management will land next.[/dim]")
