import pytest
from textual.app import App
from cli.tui.screens.hackathon import HackathonScreen


class HackathonApp(App[None]):
    def on_mount(self):
        self.push_screen(HackathonScreen())


@pytest.mark.asyncio
async def test_hackathon_form():
    app = HackathonApp()
    async with app.run_test() as pilot:
        assert app.screen.query_one("#hackathon-form") is not None
