"""Database operations for the OpenHack CLI."""

import subprocess

import typer
from rich.console import Console

from cli.utils import confirm_action, db_session, run_async

console = Console()
app = typer.Typer(help="Database operations")


@app.command("migrate")
def migrate(
    revision: str = typer.Argument("head", help="Target revision (default: head)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be applied without executing"),
):
    """Run Alembic database migrations."""
    cmd = ["alembic", "upgrade", revision]
    if dry_run:
        console.print(f"[dim]Would run: {' '.join(cmd)}[/dim]")
        return

    console.print(f"[blue]Running migrations to {revision}...[/blue]")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        console.print(f"[red]Migration failed:[/red]\n{result.stderr}")
        raise typer.Exit(1)
    console.print("[green]Migrations applied successfully[/green]")
    if result.stdout:
        console.print(result.stdout)


@app.command("downgrade")
def downgrade(
    revision: str = typer.Argument(..., help="Target revision (e.g., -1 or a revision hash)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Downgrade database to a previous revision."""
    if not yes:
        confirm_action(f"Downgrade database to {revision}? This may lose data.", abort=True)

    console.print(f"[yellow]Downgrading to {revision}...[/yellow]")
    result = subprocess.run(["alembic", "downgrade", revision], capture_output=True, text=True)
    if result.returncode != 0:
        console.print(f"[red]Downgrade failed:[/red]\n{result.stderr}")
        raise typer.Exit(1)
    console.print("[green]Downgrade complete[/green]")


@app.command("revision")
def revision(
    message: str = typer.Option(..., "--message", "-m", help="Migration message"),
    autogenerate: bool = typer.Option(True, "--autogenerate/--no-autogenerate", help="Auto-detect model changes"),
):
    """Create a new Alembic migration revision."""
    cmd = ["alembic", "revision"]
    if autogenerate:
        cmd.append("--autogenerate")
    cmd.extend(["-m", message])

    console.print(f"[blue]Creating migration: {message}[/blue]")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        console.print(f"[red]Failed:[/red]\n{result.stderr}")
        raise typer.Exit(1)
    console.print("[green]Migration created[/green]")
    console.print(result.stdout)


@app.command("history")
def history():
    """Show Alembic migration history."""
    result = subprocess.run(["alembic", "history"], capture_output=True, text=True)
    if result.returncode != 0:
        console.print(f"[red]Failed:[/red]\n{result.stderr}")
        raise typer.Exit(1)
    console.print(result.stdout)


@app.command("current")
def current():
    """Show current database revision."""
    result = subprocess.run(["alembic", "current"], capture_output=True, text=True)
    if result.returncode != 0:
        console.print(f"[red]Failed:[/red]\n{result.stderr}")
        raise typer.Exit(1)
    console.print(result.stdout)


@app.command("seed")
def seed(
    fixture: str = typer.Argument("all", help="Fixture to load (all, hackathon, users, workshops)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Seed the database with default data."""
    if not yes:
        confirm_action("Seed database with default data?", abort=True)

    async def _seed():
        async with db_session() as db:
            from app.seed_content import seed_default_content

            await seed_default_content(db)
            console.print("[green]Database seeded successfully[/green]")

    run_async(_seed())


@app.command("reset")
def reset(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Reset the database (drop all tables and recreate)."""
    if not yes:
        confirm_action(
            "[bold red]WARNING:[/bold red] This will DROP all tables and recreate them. All data will be lost. Continue?",
            abort=True,
        )

    console.print("[red]Dropping all tables...[/red]")
    result = subprocess.run(["alembic", "downgrade", "base"], capture_output=True, text=True)
    if result.returncode != 0:
        console.print(f"[red]Drop failed:[/red]\n{result.stderr}")
        raise typer.Exit(1)

    console.print("[green]Recreating tables...[/green]")
    result = subprocess.run(["alembic", "upgrade", "head"], capture_output=True, text=True)
    if result.returncode != 0:
        console.print(f"[red]Recreate failed:[/red]\n{result.stderr}")
        raise typer.Exit(1)

    console.print("[green]Database reset complete[/green]")
