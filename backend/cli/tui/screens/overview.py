from textual.widgets import Static, Button
from textual.containers import Vertical


class OverviewTab(Vertical):
    def compose(self):
        yield Static("Overview", id="title")
        yield Static("Total Hackathons: 0", id="hackathons-count")
        yield Static("Total Registrations: 0", id="registrations-count")
        yield Static("Checked In: 0", id="checked-in-count")
        yield Static("Help Queue Open: 0", id="help-queue-count")
        yield Button("Refresh", id="refresh")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "refresh":
            self.run_worker(self._refresh())

    async def _refresh(self):
        from cli.utils import db_session
        from sqlalchemy import func, select
        from app.models import Hackathon, Registration, HelpRequest

        async with db_session() as db:
            hack_count = await db.scalar(select(func.count(Hackathon.id)))
            reg_count = await db.scalar(select(func.count(Registration.id)))
            checked = await db.scalar(select(func.count(Registration.id)).where(Registration.checked_in_at.isnot(None)))
            help_open = await db.scalar(select(func.count(HelpRequest.id)).where(HelpRequest.status == "open"))
        self.query_one("#hackathons-count", Static).update(f"Total Hackathons: {hack_count or 0}")
        self.query_one("#registrations-count", Static).update(f"Total Registrations: {reg_count or 0}")
        self.query_one("#checked-in-count", Static).update(f"Checked In: {checked or 0}")
        self.query_one("#help-queue-count", Static).update(f"Help Queue Open: {help_open or 0}")
