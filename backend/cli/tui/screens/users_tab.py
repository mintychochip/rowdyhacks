from textual.widgets import Static, Button, Input, Select
from textual.containers import Horizontal, Vertical
from cli.tui.widgets.data_table import DataTableWidget
from cli.utils import db_session
from sqlalchemy import select
from app.models import User, UserRole


class UsersTab(Vertical):
    def compose(self):
        yield Static("Users", id="title")
        with Horizontal():
            yield Input(placeholder="Search...", id="search")
            yield Select(
                [
                    ("All", ""),
                    ("Organizer", "organizer"),
                    ("Participant", "participant"),
                    ("Judge", "judge"),
                    ("Volunteer", "volunteer"),
                ],
                value="",
                id="role-filter",
            )
            yield Button("Refresh", id="refresh")
        yield DataTableWidget(
            columns=["ID", "Name", "Email", "Role", "Banned"],
            data=[],
            id="users-table",
        )
        yield Static("", id="detail")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "refresh":
            self.run_worker(self._refresh())

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search":
            self.query_one("#users-table", DataTableWidget).set_filter(event.value)

    async def _refresh(self):
        role_filter = self.query_one("#role-filter", Select).value
        search = self.query_one("#search", Input).value.lower()
        async with db_session() as db:
            query = select(User).order_by(User.created_at.desc())
            if role_filter:
                query = query.where(User.role == UserRole(role_filter))
            result = await db.execute(query)
            users = result.scalars().all()
            data = []
            for u in users:
                if search and search not in (u.name or "").lower() and search not in (u.email or "").lower():
                    continue
                data.append(
                    {
                        "ID": str(u.id)[:8],
                        "Name": u.name or "",
                        "Email": u.email or "",
                        "Role": u.role.value if u.role else "",
                        "Banned": "Yes" if u.is_banned else "No",
                    }
                )
        self.query_one("#users-table", DataTableWidget).refresh_data(data)
