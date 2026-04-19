import typer

from fil.application.services.runtime import audio_storage_root, listen_service
from fil.shared.console import console


def register(app: typer.Typer) -> None:
    listen_app = typer.Typer(help="Record meeting audio from Linux audio devices.")

    @listen_app.command("start")
    def start() -> None:
        """Starts a listening session."""
        service = listen_service()
        try:
            result = service.start(audio_storage_root())
        except RuntimeError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(code=1) from exc

        console.print(f"[bold green]Listening started[/bold green] ({result.session.id})")
        console.print(f"Audio file: [cyan]{result.audio_path}[/cyan]")
        console.print("Source: default PipeWire input via [bold]pw-record[/bold]")

    @listen_app.command("stop")
    def stop() -> None:
        """Stops the active listening session."""
        service = listen_service()
        try:
            session = service.stop()
        except RuntimeError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(code=1) from exc

        console.print(f"[bold green]Listening stopped[/bold green] ({session.id})")
        if session.audio_path:
            console.print(f"Audio file: [cyan]{session.audio_path}[/cyan]")

    app.add_typer(listen_app, name="listen")
