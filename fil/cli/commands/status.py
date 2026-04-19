import typer

from fil.application.services.runtime import listen_service
from fil.shared.console import console
from fil.shared.session_view import render_session_status


def register(app: typer.Typer) -> None:
    @app.command("status")
    def status() -> None:
        """Shows current FIL status."""
        active_session = listen_service().get_active_session()
        console.print(render_session_status(active_session))
