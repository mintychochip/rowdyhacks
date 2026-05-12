# OpenHack TUI Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an interactive Textual TUI for OpenHack with a 7-step setup wizard and a 5-tab management dashboard that talks directly to the PostgreSQL database.

**Architecture:** Textual app with reusable widgets (`ConfigFormWidget`, `DataTableWidget`, `ConfirmDialog`, `StatusBar`) composed into wizard screens and dashboard tabs. All data access goes through `cli.utils.db_session()` async context manager and existing `ConfigService`.

**Tech Stack:** Textual >=0.52, Rich (already installed), SQLAlchemy async (already installed), pytest + Textual Pilot for UI automation testing.

---

## Chunk 1: Infrastructure

### Task 1: Add textual dependency and directory structure

**Files:**
- Modify: `backend/pyproject.toml`
- Create: `backend/cli/tui/__init__.py`
- Create: `backend/cli/tui/screens/__init__.py`
- Create: `backend/cli/tui/widgets/__init__.py`
- Create: `backend/tests/tui/__init__.py`
- Create: `backend/tests/tui/screens/__init__.py`
- Create: `backend/tests/tui/widgets/__init__.py`

- [ ] **Step 1: Add textual dependency**

Add `"textual>=0.52"` to `dependencies` in `backend/pyproject.toml`.

- [ ] **Step 2: Install**

Run: `cd backend && pip install "textual>=0.52"`

- [ ] **Step 3: Create directories**

Create all `__init__.py` files listed above.

- [ ] **Step 4: Verify**

Run: `python -c "from textual.app import App; print('ok')"`
Expected: `ok`.

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/cli/tui backend/tests/tui
git commit -m "deps(tui): add textual and scaffold directories"
```

---

### Task 2: TuiApp base class with screen registry

**Files:**
- Create: `backend/cli/tui/app.py`
- Create: `backend/cli/tui/screens/welcome.py`
- Create: `backend/cli/tui/screens/dashboard.py`
- Test: `backend/tests/tui/test_app.py`

- [ ] **Step 1: Write test**

```python
import pytest
from cli.tui.app import TuiApp

@pytest.mark.asyncio
async def test_tui_app_mounts():
    app = TuiApp()
    async with app.run_test() as pilot:
        assert app.is_running
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Implement**

```python
# backend/cli/tui/app.py
from textual.app import App

from cli.tui.screens.welcome import WelcomeScreen
from cli.tui.screens.dashboard import DashboardScreen


class TuiApp(App):
    CSS_PATH = None
    SCREENS = {
        "welcome": WelcomeScreen,
        "dashboard": DashboardScreen,
    }

    def __init__(self, mode: str = "dashboard", **kwargs):
        super().__init__(**kwargs)
        self.mode = mode

    def on_mount(self):
        if self.mode == "setup":
            self.push_screen("welcome")
        else:
            self.push_screen("dashboard")
```

```python
# backend/cli/tui/screens/welcome.py
from textual.screen import Screen
class WelcomeScreen(Screen):
    pass
```

```python
# backend/cli/tui/screens/dashboard.py
from textual.screen import Screen
class DashboardScreen(Screen):
    pass
```

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add backend/cli/tui/app.py backend/cli/tui/screens/welcome.py backend/cli/tui/screens/dashboard.py backend/tests/tui/test_app.py
git commit -m "feat(tui): TuiApp with screen registry"
```

---

### Task 3: Wire `tui` and `setup` CLI commands

**Files:**
- Modify: `backend/cli/main.py`
- Test: `backend/tests/test_cli.py` (append)

- [ ] **Step 1: Add tests**

Append to `backend/tests/test_cli.py`:

```python
class TestTUICommands:
    def test_tui_help(self):
        result = runner.invoke(app, ["tui", "--help"])
        assert result.exit_code == 0

    def test_setup_help(self):
        result = runner.invoke(app, ["setup", "--help"])
        assert result.exit_code == 0
```

- [ ] **Step 2: Implement**

In `backend/cli/main.py`, add imports and commands:

```python
from cli.tui.app import TuiApp

@app.command("tui")
def tui():
    """Launch the interactive TUI dashboard."""
    tui_app = TuiApp(mode="dashboard")
    tui_app.run()

@app.command("setup")
def setup():
    """Run the interactive setup wizard."""
    tui_app = TuiApp(mode="setup")
    tui_app.run()
```

- [ ] **Step 3: Run tests, expect PASS**

- [ ] **Step 4: Commit**

```bash
git add backend/cli/main.py backend/tests/test_cli.py
git commit -m "feat(cli): add tui and setup commands"
```

---

## Chunk 2: Widgets

### Task 4: ConfigFormWidget with validation

**Files:**
- Create: `backend/cli/tui/widgets/config_form.py`
- Test: `backend/tests/tui/widgets/test_config_form.py`

- [ ] **Step 1: Write tests**

```python
import pytest
from cli.tui.widgets.config_form import ConfigFormWidget

@pytest.mark.asyncio
async def test_config_form_submits():
    fields = [("name", "Name", "text", "Alice", True)]
    widget = ConfigFormWidget(fields)
    async with widget.run_test() as pilot:
        await pilot.click("#submit")
        assert widget._submitted_values == [{"name": "Alice"}]

@pytest.mark.asyncio
async def test_config_form_validates_required():
    fields = [("name", "Name", "text", "", True)]
    widget = ConfigFormWidget(fields)
    async with widget.run_test() as pilot:
        await pilot.click("#submit")
        errors = widget.validate()
        assert any("required" in e for e in errors)
```

- [ ] **Step 2: Implement**

```python
from textual.containers import Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static, Input, Button
import re


class ConfigFormWidget(Vertical):
    class Submitted(Message):
        def __init__(self, values: dict[str, str]) -> None:
            self.values = values
            super().__init__()

    values = reactive({})

    def __init__(self, fields=None, **kwargs):
        super().__init__(**kwargs)
        self._fields = fields or []
        self._inputs: dict[str, Input] = {}
        self._submitted_values: list[dict] = []

    def compose(self):
        for key, label, ftype, default, required in self._fields:
            yield Static(f"{label}{' *' if required else ''}")
            inp = Input(value=default or "", id=f"input-{key}", placeholder=label)
            yield inp
            self._inputs[key] = inp
        yield Button("Submit", id="submit", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit":
            values = self.get_values()
            self._submitted_values.append(values)
            self.post_message(self.Submitted(values))

    def get_values(self) -> dict[str, str]:
        return {k: v.value for k, v in self._inputs.items()}

    def set_value(self, key: str, value: str) -> None:
        if key in self._inputs:
            self._inputs[key].value = value

    def validate(self) -> list[str]:
        errors = []
        for key, label, ftype, default, required in self._fields:
            val = self._inputs[key].value
            if required and not val:
                errors.append(f"{label} is required")
                continue
            if ftype == "email" and val:
                if not re.match(r"^[^@]+@[^@]+\.[^@]+$", val):
                    errors.append(f"{label} must be a valid email")
            elif ftype == "color" and val:
                if not re.match(r"^#[0-9a-fA-F]{6}$", val):
                    errors.append(f"{label} must be a hex color (#RRGGBB)")
            elif ftype == "int" and val:
                try:
                    int(val)
                except ValueError:
                    errors.append(f"{label} must be an integer")
        return errors
```

- [ ] **Step 3: Run tests, expect PASS**

- [ ] **Step 4: Commit**

```bash
git add backend/cli/tui/widgets/config_form.py backend/tests/tui/widgets/test_config_form.py
git commit -m "feat(tui): ConfigFormWidget with type validation"
```

---

### Task 5: DataTableWidget with filter and selection

**Files:**
- Create: `backend/cli/tui/widgets/data_table.py`
- Test: `backend/tests/tui/widgets/test_data_table.py`

- [ ] **Step 1: Write tests**

```python
import pytest
from cli.tui.widgets.data_table import DataTableWidget

@pytest.mark.asyncio
async def test_data_table_shows_rows():
    data = [{"id": "1", "name": "Alice"}]
    widget = DataTableWidget(columns=["id", "name"], data=data)
    async with widget.run_test() as pilot:
        table = widget.query_one("#table")
        assert table.row_count == 1

@pytest.mark.asyncio
async def test_data_table_filters():
    data = [{"id": "1", "name": "Alice"}, {"id": "2", "name": "Bob"}]
    widget = DataTableWidget(columns=["id", "name"], data=data)
    async with widget.run_test() as pilot:
        widget.set_filter("Alice")
        table = widget.query_one("#table")
        assert table.row_count == 1
```

- [ ] **Step 2: Implement**

```python
from textual.containers import Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import DataTable as TextualDataTable


class DataTableWidget(Vertical):
    class CursorMoved(Message):
        def __init__(self, row: dict) -> None:
            self.row = row
            super().__init__()

    class RowActivated(Message):
        def __init__(self, row: dict) -> None:
            self.row = row
            super().__init__()

    class RowToggled(Message):
        def __init__(self, row: dict) -> None:
            self.row = row
            super().__init__()

    cursor_row = reactive(0)
    selected_rows = reactive(set())
    filter_text = reactive("")

    def __init__(self, columns, data, enable_selection=False, **kwargs):
        super().__init__(**kwargs)
        self._columns = columns
        self._all_data = data
        self._enable_selection = enable_selection
        self._filtered_data = data

    def compose(self):
        table = TextualDataTable(id="table")
        for col in self._columns:
            table.add_column(col, key=col)
        self._populate_table(table)
        yield table

    def _populate_table(self, table):
        table.clear()
        for i, row in enumerate(self._filtered_data):
            vals = [str(row.get(c, "")) for c in self._columns]
            table.add_row(*vals, key=str(i))

    def refresh_data(self, data: list[dict]) -> None:
        self._all_data = data
        self._apply_filter()

    def set_filter(self, text: str) -> None:
        self.filter_text = text.lower()
        self._apply_filter()

    def _apply_filter(self) -> None:
        if self.filter_text:
            self._filtered_data = [
                r for r in self._all_data
                if any(self.filter_text in str(v).lower() for v in r.values())
            ]
        else:
            self._filtered_data = self._all_data
        table = self.query_one(TextualDataTable)
        self._populate_table(table)

    def get_highlighted(self) -> dict:
        if 0 <= self.cursor_row < len(self._filtered_data):
            return self._filtered_data[self.cursor_row]
        return {}

    def get_selected(self) -> list[dict]:
        return [self._filtered_data[i] for i in sorted(self.selected_rows) if i < len(self._filtered_data)]

    def on_data_table_row_highlighted(self, event: TextualDataTable.RowHighlighted) -> None:
        idx = int(event.row_key.value)
        self.cursor_row = idx
        if 0 <= idx < len(self._filtered_data):
            self.post_message(self.CursorMoved(self._filtered_data[idx]))

    def on_data_table_row_selected(self, event: TextualDataTable.RowSelected) -> None:
        idx = int(event.row_key.value)
        if self._enable_selection:
            if idx in self.selected_rows:
                self.selected_rows.discard(idx)
            else:
                self.selected_rows.add(idx)
            if 0 <= idx < len(self._filtered_data):
                self.post_message(self.RowToggled(self._filtered_data[idx]))
        else:
            if 0 <= idx < len(self._filtered_data):
                self.post_message(self.RowActivated(self._filtered_data[idx]))

    def action_select_all(self) -> None:
        if self._enable_selection:
            self.selected_rows = set(range(len(self._filtered_data)))
```

- [ ] **Step 3: Run tests, expect PASS**

- [ ] **Step 4: Commit**

```bash
git add backend/cli/tui/widgets/data_table.py backend/tests/tui/widgets/test_data_table.py
git commit -m "feat(tui): DataTableWidget with filter and selection"
```

---

### Task 6: ConfirmDialog

**Files:**
- Create: `backend/cli/tui/widgets/confirm_dialog.py`
- Test: `backend/tests/tui/widgets/test_confirm_dialog.py`

- [ ] **Step 1: Write test**

```python
import pytest
from cli.tui.widgets.confirm_dialog import ConfirmDialog

@pytest.mark.asyncio
async def test_confirm_dialog_compose():
    dialog = ConfirmDialog("Delete?", danger=True)
    async with dialog.run_test() as pilot:
        assert dialog.query_one("#confirm") is not None
        assert dialog.query_one("#cancel") is not None
```

- [ ] **Step 2: Implement**

```python
from textual.screen import ModalScreen
from textual.containers import Horizontal, Vertical
from textual.widgets import Static, Button


class ConfirmDialog(ModalScreen[bool]):
    def __init__(self, message: str, danger: bool = False) -> None:
        self._message = message
        self._danger = danger
        super().__init__()

    def compose(self):
        with Vertical(id="dialog"):
            yield Static(self._message)
            with Horizontal():
                variant = "error" if self._danger else "primary"
                yield Button("Confirm", id="confirm", variant=variant)
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)
```

- [ ] **Step 3: Run, expect PASS**

- [ ] **Step 4: Commit**

```bash
git add backend/cli/tui/widgets/confirm_dialog.py backend/tests/tui/widgets/test_confirm_dialog.py
git commit -m "feat(tui): ConfirmDialog modal"
```

---

### Task 7: StatusBar

**Files:**
- Create: `backend/cli/tui/widgets/status_bar.py`
- Test: `backend/tests/tui/widgets/test_status_bar.py`

- [ ] **Step 1: Write test**

```python
import pytest
from datetime import datetime
from cli.tui.widgets.status_bar import StatusBar

@pytest.mark.asyncio
async def test_status_bar_connected():
    bar = StatusBar(connected=True)
    async with bar.run_test() as pilot:
        text = str(bar.render())
        assert "Connected" in text

@pytest.mark.asyncio
async def test_status_bar_refresh_time():
    bar = StatusBar()
    async with bar.run_test() as pilot:
        bar.set_refresh_time(datetime.now())
        text = str(bar.render())
        assert "Last refresh" in text
```

- [ ] **Step 2: Implement**

```python
from datetime import datetime
from textual.reactive import reactive
from textual.widgets import Static


class StatusBar(Static):
    connected = reactive(False)
    last_refresh = reactive(None)

    def __init__(self, connected: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.connected = connected
        self._render_content()

    def watch_connected(self, connected: bool):
        self._render_content()

    def watch_last_refresh(self, refresh: datetime | None):
        self._render_content()

    def _render_content(self):
        status = "[green]● Connected[/green]" if self.connected else "[red]● Disconnected[/red]"
        refresh = self.last_refresh.strftime("%H:%M:%S") if self.last_refresh else "Never"
        self.update(f"DB: {status} | Last refresh: {refresh}")

    def set_connected(self, connected: bool) -> None:
        self.connected = connected

    def set_refresh_time(self, dt: datetime) -> None:
        self.last_refresh = dt
```

- [ ] **Step 3: Run, expect PASS**

- [ ] **Step 4: Commit**

```bash
git add backend/cli/tui/widgets/status_bar.py backend/tests/tui/widgets/test_status_bar.py
git commit -m "feat(tui): StatusBar with connection state"
```

---

## Chunk 3: Setup Wizard Screens

### Task 8: WelcomeScreen with first-run detection

**Files:**
- Modify: `backend/cli/tui/screens/welcome.py`
- Test: `backend/tests/tui/screens/test_welcome.py`

- [ ] **Step 1: Test**

```python
import pytest
from cli.tui.screens.welcome import WelcomeScreen

@pytest.mark.asyncio
async def test_welcome_has_next():
    screen = WelcomeScreen()
    async with screen.run_test() as pilot:
        assert screen.query_one("#next") is not None
```

- [ ] **Step 2: Implement**

```python
from textual.screen import Screen
from textual.widgets import Static, Button
from textual.containers import Vertical


class WelcomeScreen(Screen):
    def compose(self):
        yield Static("Welcome to OpenHack", id="title")
        yield Static("Let's get your hackathon platform set up.")
        with Vertical():
            yield Button("Next", id="next", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "next":
            self.app.push_screen("database")
```

- [ ] **Step 3: Run, expect PASS**

- [ ] **Step 4: Commit**

```bash
git add backend/cli/tui/screens/welcome.py backend/tests/tui/screens/test_welcome.py
git commit -m "feat(tui): WelcomeScreen"
```

---

### Task 9: DatabaseScreen with connection test

**Files:**
- Create: `backend/cli/tui/screens/database.py`
- Test: `backend/tests/tui/screens/test_database.py`

- [ ] **Step 1: Test**

```python
import pytest
from cli.tui.screens.database import DatabaseScreen

@pytest.mark.asyncio
async def test_database_screen_fields():
    screen = DatabaseScreen()
    async with screen.run_test() as pilot:
        assert screen.query_one("#database-url") is not None
        assert screen.query_one("#test-connection") is not None
```

- [ ] **Step 2: Implement**

```python
from textual.screen import Screen
from textual.widgets import Static, Input, Button
from textual.containers import Vertical
from sqlalchemy.ext.asyncio import create_async_engine
import os


class DatabaseScreen(Screen):
    def compose(self):
        yield Static("Database Configuration", id="title")
        default = os.environ.get("DATABASE_URL", "")
        yield Input(value=default, placeholder="postgresql+asyncpg://...", id="database-url")
        yield Button("Test Connection", id="test-connection")
        yield Static("", id="test-result")
        with Vertical():
            yield Button("Back", id="back")
            yield Button("Next", id="next", variant="primary")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "test-connection":
            await self._test_connection()
        elif event.button.id == "next":
            self.app.push_screen("services")
        elif event.button.id == "back":
            self.app.pop_screen()

    async def _test_connection(self):
        url = self.query_one("#database-url", Input).value
        result = self.query_one("#test-result", Static)
        if not url:
            result.update("[red]URL is required[/red]")
            return
        try:
            engine = create_async_engine(url)
            async with engine.connect() as conn:
                pass
            result.update("[green]Connected to PostgreSQL[/green]")
        except Exception as exc:
            result.update(f"[red]Connection failed: {exc}[/red]")
```

- [ ] **Step 3: Run, expect PASS**

- [ ] **Step 4: Commit**

```bash
git add backend/cli/tui/screens/database.py backend/tests/tui/screens/test_database.py
git commit -m "feat(tui): DatabaseScreen with connection test"
```

---

### Task 10: ServicesScreen

**Files:**
- Create: `backend/cli/tui/screens/services.py`
- Test: `backend/tests/tui/screens/test_services.py`

- [ ] **Step 1: Test**

```python
import pytest
from cli.tui.screens.services import ServicesScreen

@pytest.mark.asyncio
async def test_services_screen_fields():
    screen = ServicesScreen()
    async with screen.run_test() as pilot:
        assert screen.query_one("#redis-url") is not None
        assert screen.query_one("#email-provider") is not None
```

- [ ] **Step 2: Implement**

```python
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
```

- [ ] **Step 3: Run, expect PASS**

- [ ] **Step 4: Commit**

```bash
git add backend/cli/tui/screens/services.py backend/tests/tui/screens/test_services.py
git commit -m "feat(tui): ServicesScreen"
```

---

### Task 11: AdminScreen with DB write

**Files:**
- Create: `backend/cli/tui/screens/admin.py`
- Test: `backend/tests/tui/screens/test_admin.py`

- [ ] **Step 1: Test**

```python
import pytest
from unittest.mock import AsyncMock, patch
from cli.tui.screens.admin import AdminScreen

@pytest.mark.asyncio
async def test_admin_screen_form():
    screen = AdminScreen()
    async with screen.run_test() as pilot:
        assert screen.query_one("#admin-form") is not None
```

- [ ] **Step 2: Implement**

```python
from textual.screen import Screen
from textual.widgets import Static, Button
from textual.containers import Vertical
from cli.tui.widgets.config_form import ConfigFormWidget
from cli.utils import db_session
from app.models import User, UserRole


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
```

- [ ] **Step 3: Run, expect PASS**

- [ ] **Step 4: Commit**

```bash
git add backend/cli/tui/screens/admin.py backend/tests/tui/screens/test_admin.py
git commit -m "feat(tui): AdminScreen with DB write"
```

---

### Task 12: MigrationsScreen with async subprocess

**Files:**
- Create: `backend/cli/tui/screens/migrations.py`
- Test: `backend/tests/tui/screens/test_migrations.py`

- [ ] **Step 1: Test**

```python
import pytest
from cli.tui.screens.migrations import MigrationsScreen

@pytest.mark.asyncio
async def test_migrations_buttons():
    screen = MigrationsScreen()
    async with screen.run_test() as pilot:
        assert screen.query_one("#run-migrations") is not None
        assert screen.query_one("#seed-defaults") is not None
```

- [ ] **Step 2: Implement**

```python
import asyncio
from textual.screen import Screen
from textual.widgets import Static, Button
from textual.containers import Vertical


class MigrationsScreen(Screen):
    def compose(self):
        yield Static("Database Migrations", id="title")
        yield Button("Run Migrations", id="run-migrations")
        yield Button("Seed Defaults", id="seed-defaults")
        yield Static("", id="result")
        with Vertical():
            yield Button("Back", id="back")
            yield Button("Next", id="next", variant="primary")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "run-migrations":
            self.run_worker(self._run_migrations())
        elif event.button.id == "seed-defaults":
            self.run_worker(self._seed_defaults())
        elif event.button.id == "next":
            self.app.push_screen("hackathon")
        elif event.button.id == "back":
            self.app.pop_screen()

    async def _run_migrations(self):
        result = self.query_one("#result", Static)
        result.update("[blue]Running migrations...[/blue]")
        proc = await asyncio.create_subprocess_exec(
            "alembic", "upgrade", "head",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            result.update("[green]Migrations applied[/green]")
        else:
            result.update(f"[red]Failed:[/red] {stderr.decode()}")

    async def _seed_defaults(self):
        from cli.utils import db_session
        from app.seed_content import seed_default_content
        result = self.query_one("#result", Static)
        result.update("[blue]Seeding...[/blue]")
        try:
            async with db_session() as db:
                await seed_default_content(db)
            result.update("[green]Seeded successfully[/green]")
        except Exception as exc:
            result.update(f"[red]Seed failed:[/red] {exc}")
```

- [ ] **Step 3: Run, expect PASS**

- [ ] **Step 4: Commit**

```bash
git add backend/cli/tui/screens/migrations.py backend/tests/tui/screens/test_migrations.py
git commit -m "feat(tui): MigrationsScreen with async subprocess"
```

---

### Task 13: HackathonScreen with DB write

**Files:**
- Create: `backend/cli/tui/screens/hackathon.py`
- Test: `backend/tests/tui/screens/test_hackathon.py`

- [ ] **Step 1: Test**

```python
import pytest
from cli.tui.screens.hackathon import HackathonScreen

@pytest.mark.asyncio
async def test_hackathon_form():
    screen = HackathonScreen()
    async with screen.run_test() as pilot:
        assert screen.query_one("#hackathon-form") is not None
```

- [ ] **Step 2: Implement**

```python
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
```

- [ ] **Step 3: Run, expect PASS**

- [ ] **Step 4: Commit**

```bash
git add backend/cli/tui/screens/hackathon.py backend/tests/tui/screens/test_hackathon.py
git commit -m "feat(tui): HackathonScreen with DB write"
```

---

### Task 14: ThemeScreen with ConfigService

**Files:**
- Create: `backend/cli/tui/screens/theme.py`
- Test: `backend/tests/tui/screens/test_theme.py`

- [ ] **Step 1: Test**

```python
import pytest
from cli.tui.screens.theme import ThemeScreen

@pytest.mark.asyncio
async def test_theme_form():
    screen = ThemeScreen()
    async with screen.run_test() as pilot:
        assert screen.query_one("#theme-form") is not None
        assert screen.query_one("#save") is not None
```

- [ ] **Step 2: Implement**

```python
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
            self.query_one("#preview", Static).update("[green]Theme saved![/green]")
        except Exception as exc:
            self.query_one("#preview", Static).update(f"[red]Error: {exc}[/red]")
```

- [ ] **Step 3: Run, expect PASS**

- [ ] **Step 4: Commit**

```bash
git add backend/cli/tui/screens/theme.py backend/tests/tui/screens/test_theme.py
git commit -m "feat(tui): ThemeScreen with ConfigService integration"
```

---

## Chunk 4: Dashboard Tabs

### Task 15: DashboardScreen shell with tabs

**Files:**
- Modify: `backend/cli/tui/screens/dashboard.py`
- Create: `backend/cli/tui/screens/overview.py`
- Test: `backend/tests/tui/screens/test_dashboard.py`

- [ ] **Step 1: Test**

```python
import pytest
from cli.tui.screens.dashboard import DashboardScreen

@pytest.mark.asyncio
async def test_dashboard_tabs():
    screen = DashboardScreen()
    async with screen.run_test() as pilot:
        assert screen.query_one("TabbedContent") is not None
        assert screen.query_one("#status-bar") is not None
```

- [ ] **Step 2: Implement**

```python
# backend/cli/tui/screens/dashboard.py
from textual.screen import Screen
from textual.widgets import TabbedContent, TabPane
from cli.tui.widgets.status_bar import StatusBar
from cli.tui.screens.overview import OverviewTab


class DashboardScreen(Screen):
    def compose(self):
        with TabbedContent():
            with TabPane("Overview", id="overview"):
                yield OverviewTab()
            yield TabPane("Hackathons", id="hackathons")
            yield TabPane("Users", id="users")
            yield TabPane("Registrations", id="registrations")
            yield TabPane("Settings", id="settings")
        yield StatusBar(id="status-bar")

    def on_mount(self):
        self.query_one("#status-bar", StatusBar).set_connected(True)
```

```python
# backend/cli/tui/screens/overview.py
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
```

- [ ] **Step 3: Run, expect PASS**

- [ ] **Step 4: Commit**

```bash
git add backend/cli/tui/screens/dashboard.py backend/cli/tui/screens/overview.py backend/tests/tui/screens/test_dashboard.py
git commit -m "feat(tui): DashboardScreen with OverviewTab"
```

---

### Task 16: HackathonsTab

**Files:**
- Create: `backend/cli/tui/screens/hackathons_tab.py`
- Modify: `backend/cli/tui/screens/dashboard.py`
- Test: `backend/tests/tui/screens/test_hackathons_tab.py`

- [ ] **Step 1: Test**

```python
import pytest
from cli.tui.screens.hackathons_tab import HackathonsTab

@pytest.mark.asyncio
async def test_hackathons_tab():
    tab = HackathonsTab()
    async with tab.run_test() as pilot:
        assert tab.query_one("#hackathons-table") is not None
```

- [ ] **Step 2: Implement**

```python
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
                data.append({
                    "ID": str(h.id)[:8],
                    "Name": h.name,
                    "Start": str(h.start_date)[:10] if h.start_date else "",
                    "End": str(h.end_date)[:10] if h.end_date else "",
                    "Participants": str(participants or 0),
                    "Status": status,
                })
        self.query_one("#hackathons-table", DataTableWidget).refresh_data(data)
```

- [ ] **Step 3: Wire into DashboardScreen**

In `dashboard.py`, import `HackathonsTab` and replace empty `TabPane("Hackathons")` with:
```python
with TabPane("Hackathons", id="hackathons"):
    yield HackathonsTab()
```

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add backend/cli/tui/screens/hackathons_tab.py backend/cli/tui/screens/dashboard.py backend/tests/tui/screens/test_hackathons_tab.py
git commit -m "feat(tui): HackathonsTab with live data"
```

---

### Task 17: UsersTab

**Files:**
- Create: `backend/cli/tui/screens/users_tab.py`
- Modify: `backend/cli/tui/screens/dashboard.py`
- Test: `backend/tests/tui/screens/test_users_tab.py`

- [ ] **Step 1: Test**

```python
import pytest
from cli.tui.screens.users_tab import UsersTab

@pytest.mark.asyncio
async def test_users_tab():
    tab = UsersTab()
    async with tab.run_test() as pilot:
        assert tab.query_one("#users-table") is not None
```

- [ ] **Step 2: Implement**

```python
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
                [("All", ""), ("Organizer", "organizer"), ("Participant", "participant"), ("Judge", "judge"), ("Volunteer", "volunteer")],
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
                data.append({
                    "ID": str(u.id)[:8],
                    "Name": u.name or "",
                    "Email": u.email or "",
                    "Role": u.role.value if u.role else "",
                    "Banned": "Yes" if u.is_banned else "No",
                })
        self.query_one("#users-table", DataTableWidget).refresh_data(data)
```

- [ ] **Step 3: Wire into DashboardScreen**

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add backend/cli/tui/screens/users_tab.py backend/cli/tui/screens/dashboard.py backend/tests/tui/screens/test_users_tab.py
git commit -m "feat(tui): UsersTab with role filter and search"
```

---

### Task 18: RegistrationsTab

**Files:**
- Create: `backend/cli/tui/screens/registrations_tab.py`
- Modify: `backend/cli/tui/screens/dashboard.py`
- Test: `backend/tests/tui/screens/test_registrations_tab.py`

- [ ] **Step 1: Test**

```python
import pytest
from cli.tui.screens.registrations_tab import RegistrationsTab

@pytest.mark.asyncio
async def test_registrations_tab():
    tab = RegistrationsTab()
    async with tab.run_test() as pilot:
        assert tab.query_one("#registrations-table") is not None
```

- [ ] **Step 2: Implement**

```python
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
                    ("All", ""), ("Pending", "pending"), ("Accepted", "accepted"),
                    ("Rejected", "rejected"), ("Waitlisted", "waitlisted"),
                    ("Offered", "offered"), ("Checked In", "checked_in"),
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
            query = select(Registration).order_by(Registration.created_at.desc())
            if status_filter:
                query = query.where(Registration.status == RegistrationStatus(status_filter))
            result = await db.execute(query)
            regs = result.scalars().all()
            data = []
            for r in regs:
                data.append({
                    "ID": str(r.id)[:8],
                    "User": str(r.user_id)[:8],
                    "Hackathon": str(r.hackathon_id)[:8],
                    "Status": r.status.value,
                    "Applied": str(r.created_at)[:10] if r.created_at else "",
                })
        self.query_one("#registrations-table", DataTableWidget).refresh_data(data)
```

- [ ] **Step 3: Wire into DashboardScreen**

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add backend/cli/tui/screens/registrations_tab.py backend/cli/tui/screens/dashboard.py backend/tests/tui/screens/test_registrations_tab.py
git commit -m "feat(tui): RegistrationsTab with status filter"
```

---

### Task 19: SettingsTab

**Files:**
- Create: `backend/cli/tui/screens/settings_tab.py`
- Modify: `backend/cli/tui/screens/dashboard.py`
- Test: `backend/tests/tui/screens/test_settings_tab.py`

- [ ] **Step 1: Test**

```python
import pytest
from cli.tui.screens.settings_tab import SettingsTab

@pytest.mark.asyncio
async def test_settings_tab():
    tab = SettingsTab()
    async with tab.run_test() as pilot:
        assert tab.query_one("#settings-form") is not None
```

- [ ] **Step 2: Implement**

```python
from textual.widgets import Static, Button
from textual.containers import Vertical
from cli.tui.widgets.config_form import ConfigFormWidget
from cli.utils import db_session
from app.services.config_service import ConfigService, DEFAULTS

config_service = ConfigService()


class SettingsTab(Vertical):
    def compose(self):
        yield Static("Settings", id="title")
        yield Button("Refresh", id="refresh")
        fields = []
        for key, (default, env_attr, category) in DEFAULTS.items():
            label = key.replace("_", " ").title()
            fields.append((key, label, "text", str(default), False))
        yield ConfigFormWidget(fields, id="settings-form")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "refresh":
            self.run_worker(self._refresh())

    async def _refresh(self):
        async with db_session() as db:
            values = await config_service.get_all(db)
        form = self.query_one("#settings-form", ConfigFormWidget)
        for key, val in values.items():
            form.set_value(key, str(val))
```

- [ ] **Step 3: Wire into DashboardScreen**

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add backend/cli/tui/screens/settings_tab.py backend/cli/tui/screens/dashboard.py backend/tests/tui/screens/test_settings_tab.py
git commit -m "feat(tui): SettingsTab with ConfigService"
```

---

## Chunk 5: Global Features

### Task 20: Global keybindings

**Files:**
- Modify: `backend/cli/tui/app.py`
- Test: `backend/tests/tui/test_keybindings.py`

- [ ] **Step 1: Test**

```python
import pytest
from cli.tui.app import TuiApp

@pytest.mark.asyncio
async def test_app_has_bindings():
    app = TuiApp()
    assert "action_quit" in [b.action for b in app._bindings.key_bindings.values()]
```

- [ ] **Step 2: Implement**

In `backend/cli/tui/app.py`, add to `TuiApp`:

```python
BINDINGS = [
    ("ctrl+q", "quit", "Quit"),
    ("ctrl+r", "refresh", "Refresh"),
    ("?", "help", "Help"),
]

CSS = """
Screen { align: center middle; }
"""

async def action_refresh(self):
    screen = self.screen
    if hasattr(screen, "action_refresh"):
        await screen.action_refresh()

async def action_help(self):
    self.notify("Ctrl+Q: Quit | Ctrl+R: Refresh | Tab: Next focus | Esc: Close modal")
```

- [ ] **Step 3: Run, expect PASS**

- [ ] **Step 4: Commit**

```bash
git add backend/cli/tui/app.py backend/tests/tui/test_keybindings.py
git commit -m "feat(tui): global keybindings"
```

---

### Task 21: Final integration test

**Files:**
- Test: `backend/tests/tui/test_integration.py`

- [ ] **Step 1: Write test**

```python
import pytest
from cli.tui.app import TuiApp

@pytest.mark.asyncio
async def test_setup_mode_shows_welcome():
    app = TuiApp(mode="setup")
    async with app.run_test() as pilot:
        assert app.screen.__class__.__name__ == "WelcomeScreen"

@pytest.mark.asyncio
async def test_dashboard_mode_shows_dashboard():
    app = TuiApp(mode="dashboard")
    async with app.run_test() as pilot:
        assert app.screen.__class__.__name__ == "DashboardScreen"
```

- [ ] **Step 2: Run**

Run: `pytest backend/tests/tui/test_integration.py -v`
Expected: PASS.

- [ ] **Step 3: Run all TUI tests**

Run: `pytest backend/tests/tui/ -v --tb=short`
Expected: all PASS.

- [ ] **Step 4: Run full test suite**

Run: `pytest backend/tests/ -v --tb=short`
Expected: existing tests still PASS, new TUI tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/tui/test_integration.py
git commit -m "test(tui): integration tests for setup and dashboard modes"
```

---

## Chunk 6: Review

After all tasks complete, the TUI should be fully functional with:
- 7-step setup wizard (Welcome → Database → Services → Admin → Migrations → Hackathon → Theme)
- 5-tab dashboard (Overview, Hackathons, Users, Registrations, Settings)
- Reusable widgets (ConfigForm, DataTable, ConfirmDialog, StatusBar)
- Global keybindings (Ctrl+Q, Ctrl+R, ?)
- Direct DB integration via existing services
- Comprehensive UI automation tests with Textual Pilot

Total new files: ~25 screens/widgets + ~25 test files.
