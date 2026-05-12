import pytest
from textual.app import App
from cli.tui.screens.migrations import MigrationsScreen


class MigrationsApp(App[None]):
    def on_mount(self):
        self.push_screen(MigrationsScreen())


@pytest.mark.asyncio
async def test_migrations_buttons():
    app = MigrationsApp()
    async with app.run_test() as pilot:
        assert app.screen.query_one("#run-migrations") is not None
        assert app.screen.query_one("#seed-defaults") is not None
