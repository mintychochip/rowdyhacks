"""Configuration management commands for the OpenHack CLI."""

import typer
from rich import box
from rich.console import Console
from rich.table import Table

from app.config import settings
from app.services.config_service import ConfigService, DEFAULTS as CONFIG_DEFAULTS
from cli.utils import db_session, run_async

console = Console()
app = typer.Typer(help="Manage site configuration settings")

config_service = ConfigService()

# Map of CLI-friendly names to full config keys
_CONFIG_KEYS = {
    "name": "hackathon_name",
    "tagline": "hackathon_tagline",
    "email": "hackathon_email",
    "primary_color": "hackathon_primary_color",
    "background_color": "hackathon_background_color",
    "text_color": "hackathon_text_color",
    "accent_color": "hackathon_accent_color",
    "font_heading": "hackathon_font_heading",
    "font_body": "hackathon_font_body",
    "logo_url": "hackathon_logo_url",
    "favicon_url": "hackathon_favicon_url",
    "year": "hackathon_year",
    "custom_css": "custom_css",
    "registration_open": "registration_open",
    "judging_enabled": "judging_enabled",
}


@app.command("list")
def list_config():
    """List all configuration settings."""

    async def _list():
        values = {}
        try:
            async with db_session() as db:
                values = await config_service.get_all(db)
        except Exception:
            pass  # DB may not be running; show env defaults only

        table = Table(title="OpenHack Configuration", box=box.ROUNDED)
        table.add_column("Key", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")
        table.add_column("Source", style="dim")

        # Show all known keys
        for cli_name, full_key in _CONFIG_KEYS.items():
            val = values.get(full_key) if values else None
            default_val = CONFIG_DEFAULTS.get(full_key, ("", None, None))[0]
            env_val = getattr(settings, full_key, None)
            source = "default"
            display_val = default_val
            if env_val and str(env_val) != str(default_val):
                source = "env"
                display_val = env_val
            if val and str(val) != str(default_val):
                source = "db"
                display_val = val
            table.add_row(full_key, str(display_val), source)

        console.print(table)

    run_async(_list())


@app.command("get")
def get_config(key: str = typer.Argument(..., help="Config key to read (e.g., hackathon_name)")):
    """Get a single configuration value."""

    async def _get():
        async with db_session() as db:
            val = await config_service.get(key, db)

        if val is None:
            # Fall back to env settings
            val = getattr(settings, key, None)

        if val is None:
            console.print(f"[red]Key '{key}' not found[/red]")
            raise typer.Exit(1)

        console.print(f"[bold]{key}[/bold] = [green]{val}[/green]")

    run_async(_get())


@app.command("set")
def set_config(
    key: str = typer.Argument(..., help="Config key to set (e.g., hackathon_name)"),
    value: str = typer.Argument(..., help="New value"),
):
    """Set a configuration value in the database."""

    async def _set():
        async with db_session() as db:
            await config_service.set(key, value, db)
            await db.commit()

        console.print(f"[bold]{key}[/bold] set to [green]{value}[/green]")

    run_async(_set())


@app.command("reset")
def reset_config(
    key: str = typer.Argument(..., help="Config key to reset"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Reset a configuration value to its default."""

    if not yes:
        typer.confirm(f"Reset '{key}' to default?", abort=True)

    async def _reset():
        async with db_session() as db:
            await config_service.delete(key, db)
            await db.commit()

        console.print(f"[yellow]{key}[/yellow] reset to default")

    run_async(_reset())
