from textual.screen import Screen
from textual.widgets import Static, Input, Button, Select
from textual.containers import Vertical


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
            self.app.push_screen("admin")
        elif event.button.id == "back":
            self.app.pop_screen()
