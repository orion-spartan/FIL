import typer

from fil.cli.commands import dictate, do, listen, sessions, status, talk, watch
from fil.shared.console import print_banner


app = typer.Typer(
    help="FIL command line interface.",
    add_completion=False,
    no_args_is_help=False,
    rich_markup_mode="rich",
)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None and not ctx.resilient_parsing:
        print_banner()
        typer.echo(ctx.get_help())


status.register(app)
do.register(app)
dictate.register(app)
talk.register(app)
sessions.register(app)
listen.register(app)
watch.register(app)


def run() -> None:
    app()


if __name__ == "__main__":
    run()
