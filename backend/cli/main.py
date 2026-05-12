"""OpenHack CLI entry point.

Usage:
    openhack --help
    openhack config get
    openhack config set hackathon_name "My Hackathon"
    openhack db migrate
    openhack hackathon list
    openhack server start
"""

import typer
from rich import box
from rich.console import Console
from rich.table import Table

from cli import __version__
from cli.config import app as config_app
from cli.db import app as db_app
from cli.hackathon import app as hackathon_app
from cli.server import app as server_app
from cli.user import app as user_app
from cli.tui.app import TuiApp

console = Console()

app = typer.Typer(
    name="openhack",
    help="OpenHack - Command-line interface for hackathon management",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

app.add_typer(config_app, name="config", help="Manage site configuration")
app.add_typer(db_app, name="db", help="Database operations")
app.add_typer(hackathon_app, name="hackathon", help="Hackathon management")
app.add_typer(server_app, name="server", help="Server operations")
app.add_typer(user_app, name="user", help="User management")


@app.command()
def version():
    """Show the OpenHack CLI version."""
    console.print(f"[bold blue]OpenHack CLI[/bold blue] v{__version__}")


@app.command()
def status():
    """Show platform status overview."""
    from app.config import settings

    table = Table(title="OpenHack Platform Status", box=box.ROUNDED)
    table.add_column("Setting", style="cyan", no_wrap=True)
    table.add_column("Value", style="green")

    table.add_row("Hackathon Name", settings.hackathon_name)
    table.add_row("Database URL", settings.database_url)
    table.add_row("Redis URL", settings.redis_url)
    table.add_row("Frontend URL", settings.frontend_url)
    table.add_row("Base URL", settings.base_url)
    table.add_row("Email Provider", settings.email_provider)
    table.add_row("Log Level", settings.log_level)
    table.add_row("JSON Logs", str(settings.json_logs))

    console.print(table)


@app.command("tui")
def tui():
    """Launch the interactive TUI dashboard."""
    tui_app = TuiApp(mode="dashboard")
    tui_app.run()


@app.command("setup")
def setup():
    """Run the interactive setup wizard."""
    tui_app = TuiApp(mode="setup")
    tui_app.run()


def main():
    app()


if __name__ == "__main__":
    main()
