import pytest
from textual.app import App
from cli.tui.screens.dashboard import DashboardScreen


class DashboardApp(App[None]):
    def on_mount(self):
        self.push_screen(DashboardScreen())


@pytest.mark.asyncio
async def test_dashboard_tabs():
    app = DashboardApp()
    async with app.run_test() as pilot:
        assert app.screen.query_one("TabbedContent") is not None
        assert app.screen.query_one("#status-bar") is not None
