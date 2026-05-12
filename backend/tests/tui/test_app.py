import pytest
from cli.tui.app import TuiApp


@pytest.mark.asyncio
async def test_tui_app_mounts():
    app = TuiApp()
    async with app.run_test() as pilot:
        assert app.is_running
