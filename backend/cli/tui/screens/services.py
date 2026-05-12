from textual.screen import Screen
from textual.widgets import Static, Input, Button, Select
from textual.containers import Vertical
from cli.tui.docker_orchestrator import write_env


class ServicesScreen(Screen):
    def compose(self):
        yield Static("Services Configuration", id="title")
        yield Static("[yellow]Admin password is required for first-time setup.[/yellow]")
        yield Static("Admin Password (min 8 chars) *:")
        yield Input(placeholder="••••••••", id="admin-pwd", password=True)
        yield Static("Confirm Admin Password *:")
        yield Input(placeholder="••••••••", id="admin-pwd2", password=True)
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
        yield Static("", id="error")
        with Vertical():
            yield Button("Back", id="back")
            yield Button("Next", id="next", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "next":
            pwd = self.query_one("#admin-pwd", Input).value.strip()
            pwd2 = self.query_one("#admin-pwd2", Input).value.strip()
            if not pwd or len(pwd) < 8:
                self.query_one("#error", Static).update("[red]Admin password must be at least 8 characters.[/red]")
                return
            if pwd != pwd2:
                self.query_one("#error", Static).update("[red]Passwords do not match.[/red]")
                return
            self._save_env()
            self.app.push_screen("admin")
        elif event.button.id == "back":
            self.app.pop_screen()

    def _save_env(self):
        pwd = self.query_one("#admin-pwd", Input).value.strip()
        redis = self.query_one("#redis-url", Input).value
        email = self.query_one("#email-provider", Select).value
        key = self.query_one("#sendgrid-key", Input).value
        updates = {}
        if pwd:
            updates["HACKVERIFY_ADMIN_PASSWORD"] = pwd
        if redis:
            updates["HACKVERIFY_REDIS_URL"] = redis
        if email and email != "none":
            updates["HACKVERIFY_EMAIL_PROVIDER"] = email
        if key:
            updates["HACKVERIFY_SENDGRID_API_KEY"] = key
        if updates:
            write_env(updates)
