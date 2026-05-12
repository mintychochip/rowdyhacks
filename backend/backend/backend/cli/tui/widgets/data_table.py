from textual.containers import Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import DataTable as TextualDataTable


class DataTableWidget(Vertical):
    class CursorMoved(Message):
        def __init__(self, row: dict) -> None:
            self.row = row
            super().__init__()

    class RowActivated(Message):
        def __init__(self, row: dict) -> None:
            self.row = row
            super().__init__()

    class RowToggled(Message):
        def __init__(self, row: dict) -> None:
            self.row = row
            super().__init__()

    cursor_row = reactive(0)
    selected_rows = reactive(set())
    filter_text = reactive("")

    def __init__(self, columns, data, enable_selection=False, **kwargs):
        super().__init__(**kwargs)
        self._columns = columns
        self._all_data = data
        self._enable_selection = enable_selection
        self._filtered_data = data

    def compose(self):
        table = TextualDataTable(id="table")
        for col in self._columns:
            table.add_column(col, key=col)
        self._populate_table(table)
        yield table

    def _populate_table(self, table):
        table.clear()
        for i, row in enumerate(self._filtered_data):
            vals = [str(row.get(c, "")) for c in self._columns]
            table.add_row(*vals, key=str(i))

    def refresh_data(self, data: list[dict]) -> None:
        self._all_data = data
        self._apply_filter()

    def set_filter(self, text: str) -> None:
        self.filter_text = text.lower()
        self._apply_filter()

    def _apply_filter(self) -> None:
        if self.filter_text:
            self._filtered_data = [
                r for r in self._all_data if any(self.filter_text in str(v).lower() for v in r.values())
            ]
        else:
            self._filtered_data = self._all_data
        table = self.query_one(TextualDataTable)
        self._populate_table(table)

    def get_highlighted(self) -> dict:
        if 0 <= self.cursor_row < len(self._filtered_data):
            return self._filtered_data[self.cursor_row]
        return {}

    def get_selected(self) -> list[dict]:
        return [self._filtered_data[i] for i in sorted(self.selected_rows) if i < len(self._filtered_data)]

    def on_data_table_row_highlighted(self, event: TextualDataTable.RowHighlighted) -> None:
        idx = int(event.row_key.value)
        self.cursor_row = idx
        if 0 <= idx < len(self._filtered_data):
            self.post_message(self.CursorMoved(self._filtered_data[idx]))

    def on_data_table_row_selected(self, event: TextualDataTable.RowSelected) -> None:
        idx = int(event.row_key.value)
        if self._enable_selection:
            if idx in self.selected_rows:
                self.selected_rows.discard(idx)
            else:
                self.selected_rows.add(idx)
            if 0 <= idx < len(self._filtered_data):
                self.post_message(self.RowToggled(self._filtered_data[idx]))
        else:
            if 0 <= idx < len(self._filtered_data):
                self.post_message(self.RowActivated(self._filtered_data[idx]))

    def action_select_all(self) -> None:
        if self._enable_selection:
            self.selected_rows = set(range(len(self._filtered_data)))
