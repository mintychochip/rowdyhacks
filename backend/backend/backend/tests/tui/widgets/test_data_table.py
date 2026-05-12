import pytest
from textual.app import App, ComposeResult
from cli.tui.widgets.data_table import DataTableWidget


class DataTableApp(App[None]):
    def __init__(self, columns, data):
        super().__init__()
        self.columns = columns
        self.data = data
        self.widget = None

    def compose(self) -> ComposeResult:
        self.widget = DataTableWidget(columns=self.columns, data=self.data)
        yield self.widget


@pytest.mark.asyncio
async def test_data_table_shows_rows():
    app = DataTableApp(columns=["id", "name"], data=[{"id": "1", "name": "Alice"}])
    async with app.run_test() as pilot:
        table = app.widget.query_one("#table")
        assert table.row_count == 1


@pytest.mark.asyncio
async def test_data_table_filters():
    app = DataTableApp(columns=["id", "name"], data=[{"id": "1", "name": "Alice"}, {"id": "2", "name": "Bob"}])
    async with app.run_test() as pilot:
        app.widget.set_filter("Alice")
        table = app.widget.query_one("#table")
        assert table.row_count == 1
