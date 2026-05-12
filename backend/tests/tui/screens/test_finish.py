import pytest
from textual.app import App
from cli.tui.screens.finish import FinishScreen


class FinishApp(App[None]):
    def on_mount(self):
        self.push_screen(FinishScreen())


@pytest.mark.asyncio
async def test_finish_screen():
    app = FinishApp()
    async with app.run_test() as pilot:
        assert app.screen.query_one("#launch") is not None
