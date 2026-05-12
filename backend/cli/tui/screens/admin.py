from textual.screen import Screen
from textual.widgets import Static, Button
from textual.containers import Vertical
from cli.tui.widgets.config_form import ConfigFormWidget
from cli.utils import db_session
from app.models import User, UserRole
from sqlalchemy import select


class AdminScreen(Screen):
    def compose(self):
        yield Static("Create Admin Account", id="title")
        yield Static("[yellow]Note:[/yellow] Web login requires Clerk OAuth. This account is for TUI operations.")
        fields = [
            ("name", "Name", "text", "", True),
            ("email", "Email", "email", "", True),
            ("role", "Role", "select", "organizer", True),
        ]
        yield ConfigFormWidget(fields, id="admin-form")
        yield Button("Create Admin", id="create-admin", variant="primary")
        yield Static("", id="result")
        with Vertical():
            yield Button("Back", id="back")
            yield Button("Next", id="next", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create-admin":
            self.run_worker(self._create_admin())
        elif event.button.id == "next":
            self.app.push_screen("migrations")
        elif event.button.id == "back":
            self.app.pop_screen()

    async def _create_admin(self):
        form = self.query_one("#admin-form", ConfigFormWidget)
        errors = form.validate()
        if errors:
            self.query_one("#result", Static).update(f"[red]{'; '.join(errors)}[/red]")
            return
        values = form.get_values()
        try:
            async with db_session() as db:
                existing = await db.scalar(select(User).where(User.email == values["email"]))
                if existing:
                    self.query_one("#result", Static).update("[red]User already exists[/red]")
                    return
                user = User(
                    name=values["name"],
                    email=values["email"],
                    role=UserRole(values.get("role", "organizer")),
                )
                db.add(user)
                await db.commit()
            self.query_one("#result", Static).update(f"[green]Admin {values['name']} created[/green]")
        except Exception as exc:
            self.query_one("#result", Static).update(f"[red]Error: {exc}[/red]")
