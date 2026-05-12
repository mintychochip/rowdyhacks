from textual.screen import Screen
from textual.widgets import Static, Input, Button, Select
from textual.containers import Vertical
from cli.tui.docker_orchestrator import write_env


class ServicesScreen(Screen):
    def compose(self):
        yield Static("Services Configuration", id="title")
        yield Static("[yellow]Clerk OAuth keys are required for login to work.[/yellow]")
        yield Static("Clerk Publishable Key (frontend) *:")
        yield Input(placeholder="pk_test_...", id="clerk-pk")
        yield Static("Clerk Secret Key (backend) *:")
        yield Input(placeholder="sk_test_...", id="clerk-sk", password=True)
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
            pk = self.query_one("#clerk-pk", Input).value.strip()
            sk = self.query_one("#clerk-sk", Input).value.strip()
            if not pk or not sk:
                self.query_one("#error", Static).update("[red]Both Clerk keys are required.[/red]")
                return
            self._save_env()
            self.app.push_screen("admin")
        elif event.button.id == "back":
            self.app.pop_screen()

    def _save_env(self):
        pk = self.query_one("#clerk-pk", Input).value.strip()
        sk = self.query_one("#clerk-sk", Input).value.strip()
        redis = self.query_one("#redis-url", Input).value
        email = self.query_one("#email-provider", Select).value
        key = self.query_one("#sendgrid-key", Input).value
        updates = {}
        if pk:
            updates["VITE_CLERK_PUBLISHABLE_KEY"] = pk
        if sk:
            updates["HACKVERIFY_CLERK_SECRET_KEY"] = sk
        if redis:
            updates["HACKVERIFY_REDIS_URL"] = redis
        if email and email != "none":
            updates["HACKVERIFY_EMAIL_PROVIDER"] = email
        if key:
            updates["HACKVERIFY_SENDGRID_API_KEY"] = key
        if updates:
            write_env(updates)
