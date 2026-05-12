import pytest
from cli.tui.app import TuiApp


@pytest.mark.asyncio
async def test_setup_mode_shows_welcome():
    app = TuiApp(mode="setup")
    async with app.run_test() as pilot:
        assert app.screen.__class__.__name__ == "WelcomeScreen"


@pytest.mark.asyncio
async def test_dashboard_mode_shows_dashboard():
    app = TuiApp(mode="dashboard")
    async with app.run_test() as pilot:
        assert app.screen.__class__.__name__ == "DashboardScreen"
