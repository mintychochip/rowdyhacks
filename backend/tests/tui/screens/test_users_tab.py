import pytest
from textual.app import App, ComposeResult
from cli.tui.screens.users_tab import UsersTab


class UsersApp(App[None]):
    def compose(self) -> ComposeResult:
        yield UsersTab()


@pytest.mark.asyncio
async def test_users_tab():
    app = UsersApp()
    async with app.run_test() as pilot:
        assert app.screen.query_one("#users-table") is not None
