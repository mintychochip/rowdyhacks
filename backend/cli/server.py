"""Server management commands for the OpenHack CLI."""

import subprocess
import sys

import typer
from rich.console import Console

console = Console()
app = typer.Typer(help="Server operations")


@app.command("start")
def start_server(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Bind host"),
    port: int = typer.Option(8000, "--port", "-p", help="Bind port"),
    reload: bool = typer.Option(True, "--reload/--no-reload", help="Enable auto-reload"),
    workers: int = typer.Option(1, "--workers", "-w", help="Number of worker processes"),
):
    """Start the OpenHack development server."""
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]
    if reload:
        cmd.append("--reload")
    if workers > 1:
        cmd.extend(["--workers", str(workers)])

    console.print(f"[green]Starting server on {host}:{port}...[/green]")
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped[/yellow]")


@app.command("shell")
def server_shell():
    """Open an interactive Python shell with the app loaded."""
    console.print("[blue]Starting interactive shell with app context...[/blue]")
    console.print("[dim]Available: app, db, settings, models[/dim]")
    script = (
        "import asyncio;"
        "from app.main import app;"
        "from app.config import settings;"
        "from app.models import *;"
        "from app.database import async_session;"
        "import IPython;"
        "IPython.embed()"
    )
    subprocess.run([sys.executable, "-c", script])


@app.command("logs")
def server_logs(
    tail: int = typer.Option(50, "--tail", "-n", help="Number of lines to show"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output"),
):
    """View server logs (Docker Compose only)."""
    cmd = ["docker", "logs", "openhack-backend-1", "--tail", str(tail)]
    if follow:
        cmd.append("--follow")

    try:
        subprocess.run(cmd)
    except FileNotFoundError:
        console.print("[red]Docker not found. This command requires Docker Compose.[/red]")
        raise typer.Exit(1)
