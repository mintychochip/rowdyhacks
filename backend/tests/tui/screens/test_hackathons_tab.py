import pytest
from textual.app import App, ComposeResult
from cli.tui.screens.hackathons_tab import HackathonsTab


class HackathonsApp(App[None]):
    def compose(self) -> ComposeResult:
        yield HackathonsTab()


@pytest.mark.asyncio
async def test_hackathons_tab():
    app = HackathonsApp()
    async with app.run_test() as pilot:
        assert app.screen.query_one("#hackathons-table") is not None
