from textual.screen import Screen
from textual.widgets import Static, Button
from textual.containers import Vertical
from datetime import datetime
from cli.tui.widgets.config_form import ConfigFormWidget
from cli.utils import db_session
from app.models import Hackathon, User, UserRole
from sqlalchemy import select


class HackathonScreen(Screen):
    def compose(self):
        yield Static("Create First Hackathon", id="title")
        fields = [
            ("name", "Name", "text", "", True),
            ("description", "Description", "text", "", False),
            ("start_date", "Start Date", "date", "", True),
            ("end_date", "End Date", "date", "", True),
            ("venue_address", "Venue", "text", "", False),
            ("max_participants", "Max Participants", "int", "", False),
            ("waitlist_enabled", "Waitlist Enabled", "checkbox", "false", False),
        ]
        yield ConfigFormWidget(fields, id="hackathon-form")
        yield Button("Create", id="create", variant="primary")
        yield Static("", id="result")
        with Vertical():
            yield Button("Back", id="back")
            yield Button("Next", id="next", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create":
            self.run_worker(self._create_hackathon())
        elif event.button.id == "next":
            self.app.push_screen("theme")
        elif event.button.id == "back":
            self.app.pop_screen()

    async def _create_hackathon(self):
        form = self.query_one("#hackathon-form", ConfigFormWidget)
        errors = form.validate()
        if errors:
            self.query_one("#result", Static).update(f"[red]{'; '.join(errors)}[/red]")
            return
        vals = form.get_values()
        try:
            async with db_session() as db:
                organizer = await db.scalar(select(User).where(User.role == UserRole.organizer))
                if not organizer:
                    organizer = await db.scalar(select(User))
                hack = Hackathon(
                    name=vals["name"],
                    description=vals.get("description"),
                    start_date=datetime.fromisoformat(vals["start_date"]),
                    end_date=datetime.fromisoformat(vals["end_date"]),
                    venue_address=vals.get("venue_address"),
                    max_participants=int(vals["max_participants"]) if vals.get("max_participants") else None,
                    waitlist_enabled=vals.get("waitlist_enabled", "false").lower() == "true",
                    organizer_id=organizer.id if organizer else None,
                )
                db.add(hack)
                await db.commit()
            self.query_one("#result", Static).update(f"[green]Hackathon '{vals['name']}' created[/green]")
        except Exception as exc:
            self.query_one("#result", Static).update(f"[red]Error: {exc}[/red]")
