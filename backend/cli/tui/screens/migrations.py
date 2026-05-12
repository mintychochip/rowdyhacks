import asyncio
from textual.screen import Screen
from textual.widgets import Static, Button
from textual.containers import Vertical


class MigrationsScreen(Screen):
    def compose(self):
        yield Static("Database Migrations", id="title")
        yield Button("Run Migrations", id="run-migrations")
        yield Button("Seed Defaults", id="seed-defaults")
        yield Static("", id="result")
        with Vertical():
            yield Button("Back", id="back")
            yield Button("Next", id="next", variant="primary")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "run-migrations":
            self.run_worker(self._run_migrations())
        elif event.button.id == "seed-defaults":
            self.run_worker(self._seed_defaults())
        elif event.button.id == "next":
            self.app.push_screen("hackathon")
        elif event.button.id == "back":
            self.app.pop_screen()

    async def _run_migrations(self):
        result = self.query_one("#result", Static)
        result.update("[blue]Running migrations...[/blue]")
        proc = await asyncio.create_subprocess_exec(
            "alembic",
            "upgrade",
            "head",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            result.update("[green]Migrations applied[/green]")
        else:
            result.update(f"[red]Failed:[/red] {stderr.decode()}")

    async def _seed_defaults(self):
        from cli.utils import db_session
        from app.seed_content import seed_default_content

        result = self.query_one("#result", Static)
        result.update("[blue]Seeding...[/blue]")
        try:
            async with db_session() as db:
                await seed_default_content(db)
            result.update("[green]Seeded successfully[/green]")
        except Exception as exc:
            result.update(f"[red]Seed failed:[/red] {exc}")
