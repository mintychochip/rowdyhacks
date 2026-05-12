from textual.screen import Screen
from textual.widgets import Static, Button
from textual.containers import Vertical
from cli.tui.widgets.config_form import ConfigFormWidget
from cli.utils import db_session
from app.services.config_service import ConfigService

config_service = ConfigService()


class ThemeScreen(Screen):
    def compose(self):
        yield Static("Theme Configuration", id="title")
        fields = [
            ("hackathon_name", "Hackathon Name", "text", "OpenHack", True),
            ("hackathon_tagline", "Tagline", "text", "", False),
            ("hackathon_primary_color", "Primary Color", "color", "#2563eb", True),
            ("hackathon_background_color", "Background Color", "color", "#0f172a", True),
            ("hackathon_text_color", "Text Color", "color", "#f1f5f9", True),
            ("hackathon_accent_color", "Accent Color", "color", "#06b6d4", True),
            ("hackathon_font_heading", "Heading Font", "text", "Space Grotesk, sans-serif", False),
            ("hackathon_font_body", "Body Font", "text", "Inter, sans-serif", False),
        ]
        yield ConfigFormWidget(fields, id="theme-form")
        yield Static("Preview: [Primary] [Background] [Text] [Accent]", id="preview")
        yield Button("Save & Finish", id="save", variant="primary")
        with Vertical():
            yield Button("Back", id="back")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.run_worker(self._save_theme())
        elif event.button.id == "back":
            self.app.pop_screen()

    async def _save_theme(self):
        form = self.query_one("#theme-form", ConfigFormWidget)
        errors = form.validate()
        if errors:
            self.query_one("#preview", Static).update(f"[red]{'; '.join(errors)}[/red]")
            return
        vals = form.get_values()
        try:
            async with db_session() as db:
                for key, val in vals.items():
                    await config_service.set(key, val, db)
            # Write remaining env vars
            from cli.tui.docker_orchestrator import write_env, generate_secret_key, env_exists, read_env

            updates = {}
            if not env_exists():
                updates["HACKVERIFY_SECRET_KEY"] = generate_secret_key()
            # Ensure base URLs are set for docker-compose defaults
            existing = read_env()
            if "BASE_URL" not in existing:
                updates["BASE_URL"] = "http://localhost"
            if "FRONTEND_URL" not in existing:
                updates["FRONTEND_URL"] = "http://localhost:3000"
            if updates:
                write_env(updates)
            self.query_one("#preview", Static).update("[green]Theme saved! Proceeding to launch...[/green]")
            self.app.push_screen("finish")
        except Exception as exc:
            self.query_one("#preview", Static).update(f"[red]Error: {exc}[/red]")
