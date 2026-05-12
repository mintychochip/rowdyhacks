from textual.widgets import Static, Button
from textual.containers import Vertical
from cli.tui.widgets.config_form import ConfigFormWidget
from cli.utils import db_session
from app.services.config_service import ConfigService, DEFAULTS

config_service = ConfigService()


class SettingsTab(Vertical):
    def compose(self):
        yield Static("Settings", id="title")
        yield Button("Refresh", id="refresh")
        fields = []
        for key, (default, env_attr, category) in DEFAULTS.items():
            label = key.replace("_", " ").title()
            fields.append((key, label, "text", str(default), False))
        yield ConfigFormWidget(fields, id="settings-form")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "refresh":
            self.run_worker(self._refresh())

    async def _refresh(self):
        async with db_session() as db:
            values = await config_service.get_all(db)
        form = self.query_one("#settings-form", ConfigFormWidget)
        for key, val in values.items():
            form.set_value(key, str(val))
