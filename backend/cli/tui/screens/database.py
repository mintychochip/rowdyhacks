from textual.screen import Screen
from textual.widgets import Static, Input, Button
from textual.containers import Vertical
from sqlalchemy.ext.asyncio import create_async_engine
import os


class DatabaseScreen(Screen):
    def compose(self):
        yield Static("Database Configuration", id="title")
        default = os.environ.get("DATABASE_URL", "")
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
