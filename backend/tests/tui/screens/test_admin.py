import pytest
from textual.app import App
from cli.tui.screens.admin import AdminScreen


class AdminApp(App[None]):
    def on_mount(self):
        self.push_screen(AdminScreen())


@pytest.mark.asyncio
async def test_admin_screen_form():
    app = AdminApp()
    async with app.run_test() as pilot:
        assert app.screen.query_one("#admin-form") is not None
