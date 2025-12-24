"""
Soorma CLI - Main entry point.

Commands:
    soorma init <name>  - Scaffold a new agent project
    soorma dev          - Start local development infrastructure
    soorma deploy       - Deploy to Soorma Cloud (coming soon)
"""

import typer
from typing import Optional
from pathlib import Path

from .commands import init, dev

app = typer.Typer(
    name="soorma",
    help="Soorma CLI - Build and deploy AI agents with the DisCo architecture.",
    no_args_is_help=True,
)

# Register commands
app.command(name="init", help="Scaffold a new agent project.")(init.init_project)
app.command(name="dev", help="Start local development infrastructure (Docker).")(dev.dev_stack)


@app.command()
def deploy():
    """
    Deploy your agent to Soorma Cloud.
    """
    typer.echo("🚀 Deploy command coming soon!")
    typer.echo("Visit https://soorma.ai to join the waitlist for Soorma Cloud.")
    raise typer.Exit(0)


@app.command()
def version():
    """
    Show the Soorma CLI version.
    """
    from soorma import __version__
    typer.echo(f"Soorma Core v{__version__}")


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
