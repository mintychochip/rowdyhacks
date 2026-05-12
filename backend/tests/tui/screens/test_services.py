import pytest
from textual.app import App
from cli.tui.screens.services import ServicesScreen


class ServicesApp(App[None]):
    def on_mount(self):
        self.push_screen(ServicesScreen())


@pytest.mark.asyncio
async def test_services_screen_fields():
    app = ServicesApp()
    async with app.run_test() as pilot:
        assert app.screen.query_one("#clerk-pk") is not None
        assert app.screen.query_one("#clerk-sk") is not None
        assert app.screen.query_one("#redis-url") is not None
        assert app.screen.query_one("#email-provider") is not None
