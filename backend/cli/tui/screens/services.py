from textual.screen import Screen
from textual.widgets import Static, Input, Button, Select
from textual.containers import Vertical
from cli.tui.docker_orchestrator import write_env


class ServicesScreen(Screen):
    def compose(self):
        yield Static("Services Configuration", id="title")
        yield Static("REDIS_URL (optional):")
        yield Input(placeholder="redis://localhost:6379", id="redis-url")
        yield Static("Email Provider:")
        yield Select(
            [("None", "none"), ("SendGrid", "sendgrid")],
            value="none",
            id="email-provider",
        )
        yield Static("SendGrid API Key (if selected):")
        yield Input(placeholder="SG.xxx", id="sendgrid-key", password=True)
        with Vertical():
            yield Button("Back", id="back")
            yield Button("Skip", id="skip")
            yield Button("Next", id="next", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id in ("next", "skip"):
            self._save_env()
            self.app.push_screen("admin")
        elif event.button.id == "back":
            self.app.pop_screen()

    def _save_env(self):
        redis = self.query_one("#redis-url", Input).value
        email = self.query_one("#email-provider", Select).value
        key = self.query_one("#sendgrid-key", Input).value
        updates = {}
        if redis:
            updates["HACKVERIFY_REDIS_URL"] = redis
        if email and email != "none":
            updates["HACKVERIFY_EMAIL_PROVIDER"] = email
        if key:
            updates["HACKVERIFY_SENDGRID_API_KEY"] = key
        if updates:
            write_env(updates)
