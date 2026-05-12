import pytest
from datetime import datetime
from textual.app import App, ComposeResult
from cli.tui.widgets.status_bar import StatusBar


class StatusBarApp(App[None]):
    def __init__(self, connected: bool = False):
        super().__init__()
        self.bar = StatusBar(connected=connected)

    def compose(self) -> ComposeResult:
        yield self.bar


@pytest.mark.asyncio
async def test_status_bar_connected():
    app = StatusBarApp(connected=True)
    async with app.run_test() as pilot:
        text = str(app.bar.render())
        assert "Connected" in text


@pytest.mark.asyncio
async def test_status_bar_disconnected():
    app = StatusBarApp(connected=False)
    async with app.run_test() as pilot:
        text = str(app.bar.render())
        assert "Disconnected" in text


@pytest.mark.asyncio
async def test_status_bar_refresh_time():
    app = StatusBarApp()
    async with app.run_test() as pilot:
        app.bar.set_refresh_time(datetime.now())
        await pilot.pause()
        text = str(app.bar.render())
        assert "Last refresh" in text


@pytest.mark.asyncio
async def test_status_bar_set_connected():
    app = StatusBarApp(connected=False)
    async with app.run_test() as pilot:
        app.bar.set_connected(True)
        await pilot.pause()
        text = str(app.bar.render())
        assert "Connected" in text
