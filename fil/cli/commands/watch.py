from __future__ import annotations

from datetime import datetime

import typer
from rich.live import Live

from fil.application.services.runtime import listen_service
from fil.shared.console import console
from fil.shared.session_view import render_session_status
from fil.shared.terminal import is_quit_key, read_key, terminal_keys


def register(app: typer.Typer) -> None:
    @app.command("watch")
    def watch(interval: float = typer.Option(1.0, min=0.2, help="Refresh interval in seconds.")) -> None:
        """Watches FIL session state in real time."""
        service = listen_service()

        try:
            with terminal_keys(), Live(render_session_status(service.get_active_session(), datetime.utcnow()), console=console, refresh_per_second=4) as live:
                while True:
                    live.update(render_session_status(service.get_active_session(), datetime.utcnow()))
                    if is_quit_key(read_key(interval)):
                        break
        except KeyboardInterrupt:
            console.print("\n[dim]watch stopped[/dim]")
            return

        console.print("\n[dim]watch stopped[/dim]")
