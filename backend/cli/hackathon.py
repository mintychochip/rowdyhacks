"""Hackathon management commands for the OpenHack CLI."""

from datetime import UTC, datetime

import typer
from rich import box
from rich.console import Console
from rich.table import Table
from sqlalchemy import select

from app.models import Hackathon, Registration, RegistrationStatus
from cli.utils import db_session, run_async

console = Console()
app = typer.Typer(help="Manage hackathons")


@app.command("list")
def list_hackathons():
    """List all hackathons."""

    async def _list():
        async with db_session() as db:
            result = await db.execute(select(Hackathon).order_by(Hackathon.created_at.desc()))
            hackathons = result.scalars().all()

        if not hackathons:
            console.print("[dim]No hackathons found[/dim]")
            return

        table = Table(title="Hackathons", box=box.ROUNDED)
        table.add_column("ID", style="dim")
        table.add_column("Name", style="cyan")
        table.add_column("Start Date", style="green")
        table.add_column("End Date", style="green")
        table.add_column("Participants", style="yellow")
        table.add_column("Status", style="magenta")

        now = datetime.now(UTC)
        for h in hackathons:
            status = "Upcoming" if h.start_date > now else "Active" if h.end_date > now else "Ended"
            table.add_row(
                str(h.id)[:8],
                h.name,
                h.start_date.strftime("%Y-%m-%d") if h.start_date else "",
                h.end_date.strftime("%Y-%m-%d") if h.end_date else "",
                str(h.current_participants or 0),
                status,
            )

        console.print(table)

    run_async(_list())


@app.command("show")
def show_hackathon(
    hackathon_id: str = typer.Argument(..., help="Hackathon ID (prefix is fine)"),
):
    """Show detailed info about a hackathon."""

    async def _show():
        async with db_session() as db:
            result = await db.execute(select(Hackathon))
            hackathons = result.scalars().all()
            hackathon = next((h for h in hackathons if str(h.id).startswith(hackathon_id)), None)

            if not hackathon:
                console.print(f"[red]Hackathon '{hackathon_id}' not found[/red]")
                raise typer.Exit(1)

            reg_result = await db.execute(select(Registration).where(Registration.hackathon_id == hackathon.id))
            registrations = reg_result.scalars().all()

        accepted = sum(1 for r in registrations if r.status == RegistrationStatus.accepted)
        pending = sum(1 for r in registrations if r.status == RegistrationStatus.pending)
        waitlisted = sum(1 for r in registrations if r.status == RegistrationStatus.waitlisted)
        checked_in = sum(1 for r in registrations if r.checked_in_at is not None)

        table = Table(title=f"Hackathon: {hackathon.name}", box=box.ROUNDED)
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("ID", str(hackathon.id))
        table.add_row("Name", hackathon.name)
        table.add_row("Description", hackathon.description or "")
        table.add_row("Start Date", hackathon.start_date.isoformat() if hackathon.start_date else "")
        table.add_row("End Date", hackathon.end_date.isoformat() if hackathon.end_date else "")
        table.add_row("Venue", hackathon.venue_address or "")
        table.add_row("Max Participants", str(hackathon.max_participants or "Unlimited"))
        table.add_row("Waitlist Enabled", str(hackathon.waitlist_enabled))
        table.add_row("Accepted Registrations", str(accepted))
        table.add_row("Pending Registrations", str(pending))
        table.add_row("Waitlisted", str(waitlisted))
        table.add_row("Checked In", str(checked_in))

        console.print(table)

    run_async(_show())


@app.command("stats")
def hackathon_stats(
    hackathon_id: str = typer.Argument(..., help="Hackathon ID (prefix is fine)"),
):
    """Show registration statistics for a hackathon."""

    async def _stats():
        async with db_session() as db:
            result = await db.execute(select(Hackathon))
            hackathons = result.scalars().all()
            hackathon = next((h for h in hackathons if str(h.id).startswith(hackathon_id)), None)

            if not hackathon:
                console.print(f"[red]Hackathon '{hackathon_id}' not found[/red]")
                raise typer.Exit(1)

            reg_result = await db.execute(select(Registration).where(Registration.hackathon_id == hackathon.id))
            registrations = reg_result.scalars().all()

        from collections import Counter

        status_counts = Counter(r.status.value for r in registrations)

        table = Table(title=f"Registration Stats: {hackathon.name}", box=box.ROUNDED)
        table.add_column("Status", style="cyan")
        table.add_column("Count", style="green")

        for status, count in status_counts.most_common():
            table.add_row(status, str(count))

        table.add_row("[bold]Total[/bold]", str(len(registrations)), style="yellow")

        console.print(table)

    run_async(_stats())
