import pytest
from textual.app import App, ComposeResult
from cli.tui.widgets.config_form import ConfigFormWidget


class ConfigFormApp(App[None]):
    def __init__(self, fields):
        super().__init__()
        self.fields = fields
        self.widget = None

    def compose(self) -> ComposeResult:
        self.widget = ConfigFormWidget(self.fields)
        yield self.widget


@pytest.mark.asyncio
async def test_config_form_submits():
    app = ConfigFormApp(fields=[("name", "Name", "text", "Alice", True)])
    async with app.run_test() as pilot:
        await pilot.click("#submit")
        assert app.widget._submitted_values == [{"name": "Alice"}]


@pytest.mark.asyncio
async def test_config_form_validates_required():
    app = ConfigFormApp(fields=[("name", "Name", "text", "", True)])
    async with app.run_test() as pilot:
        await pilot.click("#submit")
        errors = app.widget.validate()
        assert any("required" in e for e in errors)
