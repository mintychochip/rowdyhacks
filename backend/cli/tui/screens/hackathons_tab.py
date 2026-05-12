from textual.widgets import Static, Button, Input
from textual.containers import Horizontal, Vertical
from cli.tui.widgets.data_table import DataTableWidget
from cli.utils import db_session
from sqlalchemy import select, func
from app.models import Hackathon, Registration
from datetime import datetime, UTC


class HackathonsTab(Vertical):
    def compose(self):
        yield Static("Hackathons", id="title")
        with Horizontal():
            yield Input(placeholder="Search...", id="search")
            yield Button("Refresh", id="refresh")
        yield DataTableWidget(
            columns=["ID", "Name", "Start", "End", "Participants", "Status"],
            data=[],
            id="hackathons-table",
        )
        yield Static("", id="detail")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "refresh":
            self.run_worker(self._refresh())

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search":
            self.query_one("#hackathons-table", DataTableWidget).set_filter(event.value)

    async def _refresh(self):
        async with db_session() as db:
            result = await db.execute(select(Hackathon))
            hackathons = result.scalars().all()
            data = []
            now = datetime.now(UTC)
            for h in hackathons:
                status = "Upcoming" if h.start_date > now else "Active" if h.start_date <= now < h.end_date else "Ended"
                participants = await db.scalar(
                    select(func.count(Registration.id)).where(
                        Registration.hackathon_id == h.id,
                        Registration.status == "accepted",
                    )
                )
                data.append(
                    {
                        "ID": str(h.id)[:8],
                        "Name": h.name,
                        "Start": str(h.start_date)[:10] if h.start_date else "",
                        "End": str(h.end_date)[:10] if h.end_date else "",
                        "Participants": str(participants or 0),
                        "Status": status,
                    }
                )
        self.query_one("#hackathons-table", DataTableWidget).refresh_data(data)
