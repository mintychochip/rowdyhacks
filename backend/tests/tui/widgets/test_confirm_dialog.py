import pytest
from textual.app import App
from cli.tui.widgets.confirm_dialog import ConfirmDialog


class ConfirmDialogApp(App[None]):
    def __init__(self, message: str, danger: bool = False):
        super().__init__()
        self.message = message
        self.danger = danger
        self.result = None

    def on_mount(self) -> None:
        dialog = ConfirmDialog(self.message, danger=self.danger)
        self.push_screen(dialog, lambda value: setattr(self, "result", value))


@pytest.mark.asyncio
async def test_confirm_dialog_compose():
    app = ConfirmDialogApp("Delete?", danger=True)
    async with app.run_test() as pilot:
        assert app.screen.query_one("#confirm") is not None
        assert app.screen.query_one("#cancel") is not None


@pytest.mark.asyncio
async def test_confirm_dialog_dismiss_true():
    app = ConfirmDialogApp("Are you sure?")
    async with app.run_test() as pilot:
        await pilot.click("#confirm")
        await pilot.pause()
        assert app.result is True


@pytest.mark.asyncio
async def test_confirm_dialog_dismiss_false():
    app = ConfirmDialogApp("Are you sure?")
    async with app.run_test() as pilot:
        await pilot.click("#cancel")
        await pilot.pause()
        assert app.result is False
