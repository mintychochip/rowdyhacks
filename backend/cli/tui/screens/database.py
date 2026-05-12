from textual.screen import Screen
from textual.widgets import Static, Input, Button
from textual.containers import Vertical
from sqlalchemy.ext.asyncio import create_async_engine
import os
import re
from cli.tui.docker_orchestrator import write_env, env_exists


class DatabaseScreen(Screen):
    def compose(self):
        yield Static("Database Configuration", id="title")
        default = os.environ.get("DATABASE_URL", "")
        if not default and not env_exists():
            default = "postgresql+asyncpg://hackverify:changeme@db:5432/hackverify"
        yield Input(value=default, placeholder="postgresql+asyncpg://...", id="database-url")
        yield Button("Test Connection", id="test-connection")
        yield Static("", id="test-result")
        with Vertical():
            yield Button("Back", id="back")
            yield Button("Next", id="next", variant="primary")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "test-connection":
            await self._test_connection()
        elif event.button.id == "next":
            await self._save_env()
            self.app.push_screen("services")
        elif event.button.id == "back":
            self.app.pop_screen()

    async def _test_connection(self):
        url = self.query_one("#database-url", Input).value
        result = self.query_one("#test-result", Static)
        if not url:
            result.update("[red]URL is required[/red]")
            return
        try:
            engine = create_async_engine(url)
            async with engine.connect() as conn:
                pass
            result.update("[green]Connected to PostgreSQL[/green]")
        except Exception as exc:
            result.update(f"[red]Connection failed: {exc}[/red]")

    async def _save_env(self):
        url = self.query_one("#database-url", Input).value
        # Parse URL to extract credentials for docker-compose env vars
        # e.g. postgresql+asyncpg://USER:PASS@HOST:PORT/DB
        m = re.match(r"postgresql\+asyncpg://([^:]+):([^@]+)@([^:/]+)(?::(\d+))?/(.+)", url)
        if m:
            user, password, host, port, db = m.groups()
            write_env(
                {
                    "POSTGRES_USER": user,
                    "POSTGRES_PASSWORD": password,
                    "POSTGRES_DB": db,
                    "HACKVERIFY_DATABASE_URL": url,
                }
            )
