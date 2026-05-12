import pytest
from textual.app import App
from cli.tui.screens.welcome import WelcomeScreen


class WelcomeApp(App[None]):
    def on_mount(self):
        self.push_screen(WelcomeScreen())


@pytest.mark.asyncio
async def test_welcome_has_next():
    app = WelcomeApp()
    async with app.run_test() as pilot:
        assert app.screen.query_one("#next") is not None
