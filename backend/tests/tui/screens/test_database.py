import pytest
from textual.app import App
from cli.tui.screens.database import DatabaseScreen


class DatabaseApp(App[None]):
    def on_mount(self):
        self.push_screen(DatabaseScreen())


@pytest.mark.asyncio
async def test_database_screen_fields():
    app = DatabaseApp()
    async with app.run_test() as pilot:
        assert app.screen.query_one("#database-url") is not None
        assert app.screen.query_one("#test-connection") is not None
