from textual.widgets import Static, Button, Select
from textual.containers import Horizontal, Vertical
from cli.tui.widgets.data_table import DataTableWidget
from cli.utils import db_session
from sqlalchemy import select
from app.models import Registration, RegistrationStatus


class RegistrationsTab(Vertical):
    def compose(self):
        yield Static("Registrations", id="title")
        with Horizontal():
            yield Select(
                [
                    ("All", ""),
                    ("Pending", "pending"),
                    ("Accepted", "accepted"),
                    ("Rejected", "rejected"),
                    ("Waitlisted", "waitlisted"),
                    ("Offered", "offered"),
                    ("Checked In", "checked_in"),
                ],
                value="",
                id="status-filter",
            )
            yield Button("Refresh", id="refresh")
        yield DataTableWidget(
            columns=["ID", "User", "Hackathon", "Status", "Applied"],
            data=[],
            enable_selection=True,
            id="registrations-table",
        )
        yield Static("", id="detail")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "refresh":
            self.run_worker(self._refresh())

    async def _refresh(self):
        status_filter = self.query_one("#status-filter", Select).value
        async with db_session() as db:
            query = select(Registration).order_by(Registration.registered_at.desc())
            if status_filter:
                query = query.where(Registration.status == RegistrationStatus(status_filter))
            result = await db.execute(query)
            regs = result.scalars().all()
            data = []
            for r in regs:
                data.append(
                    {
                        "ID": str(r.id)[:8],
                        "User": str(r.user_id)[:8],
                        "Hackathon": str(r.hackathon_id)[:8],
                        "Status": r.status.value,
                        "Applied": str(r.registered_at)[:10] if r.registered_at else "",
                    }
                )
        self.query_one("#registrations-table", DataTableWidget).refresh_data(data)
