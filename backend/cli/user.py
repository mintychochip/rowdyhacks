"""User management commands for the OpenHack CLI."""

import typer
from rich import box
from rich.console import Console
from rich.table import Table
from sqlalchemy import select

from app.models import User, UserRole
from cli.utils import confirm_action, db_session, run_async

console = Console()
app = typer.Typer(help="Manage users")


@app.command("list")
def list_users(
    role: str = typer.Option(None, "--role", "-r", help="Filter by role (organizer, participant, judge, volunteer)"),
    search: str = typer.Option(None, "--search", "-s", help="Search by name or email"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max results"),
):
    """List all users with optional filtering."""

    async def _list():
        async with db_session() as db:
            query = select(User).order_by(User.created_at.desc()).limit(limit)
            if role:
                try:
                    role_enum = UserRole(role)
                    query = query.where(User.role == role_enum)
                except ValueError:
                    console.print(f"[red]Invalid role: {role}[/red]")
                    raise typer.Exit(1)

            result = await db.execute(query)
            users = result.scalars().all()

        if not users:
            console.print("[dim]No users found[/dim]")
            return

        table = Table(title="Users", box=box.ROUNDED)
        table.add_column("ID", style="dim")
        table.add_column("Name", style="cyan")
        table.add_column("Email", style="green")
        table.add_column("Role", style="yellow")
        table.add_column("Banned", style="red")

        for u in users:
            if (
                search
                and search.lower() not in (u.name or "").lower()
                and search.lower() not in (u.email or "").lower()
            ):
                continue
            banned = "Yes" if getattr(u, "is_banned", False) else "No"
            table.add_row(
                str(u.id)[:8],
                u.name or "",
                u.email or "",
                u.role.value if u.role else "",
                banned,
            )

        console.print(table)

    run_async(_list())


@app.command("show")
def show_user(
    user_id: str = typer.Argument(..., help="User ID (prefix is fine)"),
):
    """Show detailed info about a user."""

    async def _show():
        async with db_session() as db:
            result = await db.execute(select(User))
            users = result.scalars().all()
            user = next((u for u in users if str(u.id).startswith(user_id)), None)

            if not user:
                console.print(f"[red]User '{user_id}' not found[/red]")
                raise typer.Exit(1)

        table = Table(title=f"User: {user.name or user.email}", box=box.ROUNDED)
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("ID", str(user.id))
        table.add_row("Name", user.name or "")
        table.add_row("Email", user.email or "")
        table.add_row("Role", user.role.value if user.role else "")
        table.add_row("Banned", str(getattr(user, "is_banned", False)))
        table.add_row("Bio", getattr(user, "bio", "") or "")
        table.add_row("Skills", ", ".join(getattr(user, "skills", []) or []))

        console.print(table)

    run_async(_show())


@app.command("promote")
def promote_user(
    user_id: str = typer.Argument(..., help="User ID (prefix is fine)"),
    role: str = typer.Argument(..., help="New role (organizer, participant, judge, volunteer)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Change a user's role."""

    if not yes:
        confirm_action(f"Promote user {user_id} to {role}?", abort=True)

    async def _promote():
        async with db_session() as db:
            result = await db.execute(select(User))
            users = result.scalars().all()
            user = next((u for u in users if str(u.id).startswith(user_id)), None)

            if not user:
                console.print(f"[red]User '{user_id}' not found[/red]")
                raise typer.Exit(1)

            try:
                user.role = UserRole(role)
            except ValueError:
                valid = ", ".join(r.value for r in UserRole)
                console.print(f"[red]Invalid role. Valid roles: {valid}[/red]")
                raise typer.Exit(1)

            await db.commit()
            console.print(f"[green]User {user.name or user.email} promoted to {role}[/green]")

    run_async(_promote())


@app.command("ban")
def ban_user(
    user_id: str = typer.Argument(..., help="User ID (prefix is fine)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Ban a user from the platform."""

    if not yes:
        confirm_action(f"Ban user {user_id}?", abort=True)

    async def _ban():
        async with db_session() as db:
            result = await db.execute(select(User))
            users = result.scalars().all()
            user = next((u for u in users if str(u.id).startswith(user_id)), None)

            if not user:
                console.print(f"[red]User '{user_id}' not found[/red]")
                raise typer.Exit(1)

            user.is_banned = True
            from datetime import UTC, datetime

            user.banned_at = datetime.now(UTC)
            await db.commit()
            console.print(f"[red]User {user.name or user.email} banned[/red]")

    run_async(_ban())


@app.command("unban")
def unban_user(
    user_id: str = typer.Argument(..., help="User ID (prefix is fine)"),
):
    """Unban a previously banned user."""

    async def _unban():
        async with db_session() as db:
            result = await db.execute(select(User))
            users = result.scalars().all()
            user = next((u for u in users if str(u.id).startswith(user_id)), None)

            if not user:
                console.print(f"[red]User '{user_id}' not found[/red]")
                raise typer.Exit(1)

            user.is_banned = False
            user.banned_at = None
            await db.commit()
            console.print(f"[green]User {user.name or user.email} unbanned[/green]")

    run_async(_unban())
