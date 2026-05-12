import pytest
from textual.app import App, ComposeResult
from cli.tui.screens.settings_tab import SettingsTab


class SettingsApp(App[None]):
    def compose(self) -> ComposeResult:
        yield SettingsTab()


@pytest.mark.asyncio
async def test_settings_tab():
    app = SettingsApp()
    async with app.run_test() as pilot:
        assert app.screen.query_one("#settings-form") is not None
