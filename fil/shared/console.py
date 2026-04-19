from rich.console import Console


console = Console()

ASCII_BANNER = r"""
███████╗██╗██╗
██╔════╝██║██║
█████╗  ██║██║
██╔══╝  ██║██║
██║     ██║███████╗
╚═╝     ╚═╝╚══════╝
""".strip("\n")


def print_banner() -> None:
    console.print(f"[bold cyan]{ASCII_BANNER}[/bold cyan]")
    console.print("[dim]Local-first meetings, dictation, and agent CLI[/dim]")
