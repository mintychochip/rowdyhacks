import pytest
from textual.app import App
from cli.tui.screens.theme import ThemeScreen


class ThemeApp(App[None]):
    def on_mount(self):
        self.push_screen(ThemeScreen())


@pytest.mark.asyncio
async def test_theme_form():
    app = ThemeApp()
    async with app.run_test() as pilot:
        assert app.screen.query_one("#theme-form") is not None
        assert app.screen.query_one("#save") is not None
