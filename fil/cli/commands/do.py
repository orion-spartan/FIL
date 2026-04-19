import typer

from fil.shared.console import console


def register(app: typer.Typer) -> None:
    @app.command("do")
    def do_command(instruction: str = typer.Argument(..., help="Instruction for FIL/OpenCode")) -> None:
        """Runs an instruction against the agent layer."""
        console.print("[bold]Instruction received:[/bold]")
        console.print(instruction)
        console.print("[dim]OpenCode integration will be connected in the next phase.[/dim]")
