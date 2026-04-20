from __future__ import annotations

import typer
from rich.panel import Panel

from fil.application.services.runtime import dictate_service, temp_storage_root
from fil.shared.console import console


def run_dictation() -> None:
    console.print("[bold green]Recording from microphone[/bold green]")
    console.print("Press [bold]Ctrl+C[/bold] to finish and transcribe.")

    service = dictate_service()
    try:
        result = service.run(temp_storage_root())
    except RuntimeError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    if result.copied_to_clipboard:
        console.print("[bold green]Transcription copied to clipboard[/bold green]")

    title = "Dictation Result"
    body = result.transcript or "empty transcript"
    console.print(Panel(body, title=title, border_style="cyan"))


def register(app: typer.Typer) -> None:
    @app.command("d", hidden=True)
    def dictate_short() -> None:
        """Short alias for quick dictation."""
        run_dictation()

    @app.command("dictate")
    def dictate() -> None:
        """Records the microphone, transcribes locally, and copies text to the clipboard."""
        run_dictation()
