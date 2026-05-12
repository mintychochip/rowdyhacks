import pytest
from textual.app import App, ComposeResult
from cli.tui.screens.registrations_tab import RegistrationsTab


class RegistrationsApp(App[None]):
    def compose(self) -> ComposeResult:
        yield RegistrationsTab()


@pytest.mark.asyncio
async def test_registrations_tab():
    app = RegistrationsApp()
    async with app.run_test() as pilot:
        assert app.screen.query_one("#registrations-table") is not None
