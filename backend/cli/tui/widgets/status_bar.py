from datetime import datetime
from textual.reactive import reactive
from textual.widgets import Static


class StatusBar(Static):
    connected = reactive(False)
    last_refresh = reactive(None)

    def __init__(self, connected: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.connected = connected
        self._render_content()

    def watch_connected(self, connected: bool):
        self._render_content()

    def watch_last_refresh(self, refresh: datetime | None):
        self._render_content()

    def _render_content(self):
        status = "[green]● Connected[/green]" if self.connected else "[red]● Disconnected[/red]"
        refresh = self.last_refresh.strftime("%H:%M:%S") if self.last_refresh else "Never"
        self.update(f"DB: {status} | Last refresh: {refresh}")

    def set_connected(self, connected: bool) -> None:
        self.connected = connected

    def set_refresh_time(self, dt: datetime) -> None:
        self.last_refresh = dt
