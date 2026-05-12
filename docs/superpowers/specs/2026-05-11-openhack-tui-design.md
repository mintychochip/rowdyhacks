# OpenHack TUI Design Spec

> Date: 2026-05-11
> Project: OpenHack — Hackathon Management Platform

## Goal

Build an interactive Terminal User Interface (TUI) for OpenHack that serves as both a one-time setup wizard and a persistent management dashboard, using Textual (built on Rich).

## Architecture

The TUI is invoked via `openhack tui` (or `openhack setup` for first-run). It communicates directly with the database and services (SQLAlchemy), not via HTTP API. This means it works even when the backend server is not running.

```
cli/tui/
├── __init__.py
├── app.py          # Textual App entry point
├── screens/
│   ├── __init__.py
│   ├── welcome.py      # Step 1: Welcome / first-run detection
│   ├── database.py     # Step 2: DB connection + test
│   ├── services.py     # Step 3: Redis, email, other infra
│   ├── admin.py        # Step 4: Create first admin user
│   ├── migrations.py   # Step 5: Alembic migrate + seed
│   ├── hackathon.py    # Step 6: Create first hackathon
│   ├── theme.py        # Step 7: Theme preview + save
│   ├── dashboard.py    # Persistent: main dashboard shell
│   ├── overview.py     # Dashboard tab: live stats
│   ├── hackathons.py   # Dashboard tab: manage hackathons
│   ├── users.py        # Dashboard tab: manage users
│   ├── registrations.py # Dashboard tab: manage registrations
│   └── settings.py     # Dashboard tab: site settings
├── widgets/
│   ├── __init__.py
│   ├── config_form.py  # Reusable form for key/value pairs
│   ├── data_table.py   # Reusable sortable/filterable table
│   ├── confirm_dialog.py  # Reusable confirmation modal
│   └── status_bar.py   # Bottom status bar (DB connected, etc.)
```

## Widget Interfaces

All custom widgets expose clear public APIs. Screens compose them without reading internals.

### `ConfigFormWidget`
- **Constructor params**: `fields: list[FieldSpec]` where `FieldSpec = (key, label, type, default, required)`.
- **Valid `type` values**: `"text"`, `"email"`, `"date"`, `"int"`, `"select"`, `"color"`, `"checkbox"`.
- **Reactive attributes**: `values: dict[str, str]` (current form state).
- **Public methods**: `get_values() -> dict[str, str]`, `set_value(key, value)`, `validate() -> list[str]` (returns error messages).
- **Custom event**: `ConfigFormWidget.Submitted(values)` posted on button press.
- **Validation**: each field validates based on `type` (email → regex, date → `datetime.fromisoformat`, color → hex regex, int → `int()`).

### `DataTableWidget`
- **Constructor params**: `columns: list[str]`, `data: list[dict]`, `enable_selection: bool = False`.
- **Reactive attributes**: `cursor_row: int` (currently highlighted row, read-only — driven by ↑/↓/click), `selected_rows: set[int]` (checked rows for bulk actions), `filter_text: str`.
- **Public methods**: `refresh_data(data)`, `set_filter(text)`, `get_selected() -> list[dict]`, `get_highlighted() -> dict`.
- **Custom events**: `DataTableWidget.CursorMoved(row)` (highlight changed via ↑/↓), `DataTableWidget.RowActivated(row)` (Enter or click), `DataTableWidget.RowToggled(row)` (Space on a row with `enable_selection=True`).
- **Selection**: `Space` toggles selection of current row (only when `enable_selection=True`). `Ctrl+A` selects all visible rows. Only used in tabs that support bulk actions (Registrations). The `CursorMoved` event is used by the master-detail sidebar to update detail view on ↑/↓ navigation.

### `ConfirmDialog`
- **Constructor params**: `message: str`, `danger: bool = False`.
- **Pattern**: Internal implementation pushes itself via `app.push_screen(self)`. The dialog dismisses itself with `self.dismiss(True)` or `self.dismiss(False)`. Consumers await the result via `await app.push_screen_wait(ConfirmDialog(...))`.
- **Usage**: `result = await app.push_screen_wait(ConfirmDialog("Delete?", danger=True))` → `result` is `True`/`False`.
- **Behavior**: modal overlay. `Enter` confirms, `Esc` cancels.

### `StatusBar`
- **Constructor params**: `connected: bool`, `last_refresh: datetime | None`.
- **Public methods**: `set_connected(bool)`, `set_refresh_time(dt)`.
- **Display**: left = DB status (green/red dot + "DB: Connected/Disconnected"), right = "Last refresh: HH:MM:SS".

## Setup Wizard (7 Steps)

### Step 1: Welcome
- Detect if database is initialized:
  - If `DATABASE_URL` env var is set, try connecting. If connection succeeds and `users` table exists → not first run.
  - If `DATABASE_URL` is not set or connection fails → first run (no DB configured yet).
- If first run: show "Welcome to OpenHack — let's set things up".
- If not first run: show "OpenHack is already configured. Continue to dashboard or re-run setup?"
- Navigation: Next → Step 2

### Step 2: Database
- Form fields: `DATABASE_URL` (text input, required). Pre-filled from `os.environ.get("DATABASE_URL", "")` if already set.
- Validation: must be a non-empty string. No deep URL parsing required (let SQLAlchemy fail if invalid).
- On "Test": run `create_async_engine(url).connect()` in try/except, then close.
- On success: green checkmark + "Connected to PostgreSQL".
- On failure: red error message with exception text.
- **Persistence**: the entered `DATABASE_URL` is displayed at the end of the wizard as a `.env` snippet for the user to copy. The TUI does not write files outside its process.
- Navigation: Back, Next (only if test passes)
- Edge case: if DB already has tables, show warning "Database already has tables. Continuing will use existing data."

### Step 3: Services
- Form fields: `REDIS_URL` (text, optional), `EMAIL_PROVIDER` (select: sendgrid/none, default none), `SENDGRID_API_KEY` (text, shown only if email_provider == sendgrid).
- Validation: if email_provider == sendgrid, API key must be non-empty.
- **Persistence**: `REDIS_URL`, `EMAIL_PROVIDER`, and `SENDGRID_API_KEY` are displayed at the end of the wizard as a `.env` snippet for the user to copy. The TUI does not write files outside its process.
- Optional — skip button available. Skipping stores `email_provider = "none"`.
- Navigation: Back, Skip, Next

### Step 4: Admin Account
- Form: name (text, required), email (text, required, must match email regex), role (select: organizer/participant/judge/volunteer, default organizer).
- Validation: name must be 1–200 chars. Email must match `^[^@]+@[^@]+\.[^@]+$`.
- Edge case: if a user with this email already exists, show "User already exists" error and do not create duplicate.
- Creates a `User` row directly in DB via `db_session()`.
- **Auth limitation**: this admin exists in the DB but cannot log into the web frontend (which requires Clerk OAuth). The TUI-admin is for backend DB operations only. To enable web login, the admin must sign up through the web app first, then the TUI can change their role to organizer. Document this in a warning banner.
- Navigation: Back, Next

### Step 5: Migrations + Seed
- Show current Alembic revision (run `alembic current --quiet`).
- "Run migrations" button → `asyncio.create_subprocess_exec("alembic", "upgrade", "head")` (non-blocking, with a Textual worker to keep the spinner animated).
- "Seed defaults" button → `seed_default_content(db)` via `db_session()`. This runs after the admin exists so seed data can reference the organizer.
- Progress indicator (spinner) during subprocess run.
- Edge case: if alembic returns non-zero, show stderr in red toast.
- Navigation: Back, Next

### Step 6: First Hackathon
- Form: name (text, required, max 300), description (text, optional), start_date (date input, required), end_date (date input, required), venue_address (text, optional), max_participants (int, optional), waitlist_enabled (checkbox, default False).
- Validation: `end_date > start_date`. `max_participants >= 0` if provided.
- Preview card: shows a simple textual card using the current theme colors (read from `ConfigService`). TUI cannot render web fonts, so fonts are shown as labels, not rendered.
- `organizer_id` is automatically set to the admin user created in Step 4 (required non-nullable FK on `Hackathon` model).
- Navigation: Back, Next

### Step 7: Theme Preview
- Live preview of the current theme colors on a sample card.
- Editable fields: `hackathon_name`, `hackathon_tagline`, `hackathon_primary_color`, `hackathon_background_color`, `hackathon_text_color`, `hackathon_accent_color`, `hackathon_font_heading`, `hackathon_font_body`.
- Validation: color fields must match `^#[0-9a-fA-F]{6}$`.
- Font fields: any non-empty string (no font validation — TUI cannot verify web fonts).
- "Save & Finish" writes to DB via `ConfigService.set` for each changed key.
- Final screen: "Setup complete. Start server?" with `openhack server start` shortcut.
- Navigation: Back, Finish

## Dashboard (5 Tabs)

The dashboard is a single `Screen` with a tab bar at the top (`TabbedContent`) and a `StatusBar` at the bottom. Each tab is its own `Widget` containing either static info + buttons or a `DataTableWidget` + action bar.

### Tab Interaction Model

All tabs with tables use a **master-detail layout**: left 60% = table, right 40% = detail sidebar.
- **Row selection** (`↑/↓` or click) highlights row and populates sidebar.
- **Row activation** (`Enter` or double-click) opens a **modal overlay** with a full edit form.
- **Keyboard**: `Tab` cycles between table → filter input → action buttons → back to table. `Esc` closes modals.
- **Refresh**: `Ctrl+R` re-runs the data query and redraws the table.

### Tab 1: Overview
- **Live counters** (updated on mount, manual refresh button):
  - Total hackathons (count Hackathon rows)
  - Total registrations by status (count Registration rows grouped by status)
  - Checked-in count (count registrations with `checked_in_at` not null)
  - Help queue open items (count help requests with status == "open")
- **Upcoming deadlines**: hackathons with `start_date` within next 7 days. Sorted by start_date ascending.
- **Status bar**: DB connectivity (ping every 30s), last refresh timestamp.

### Tab 2: Hackathons
- `DataTableWidget` columns: ID, Name, Start Date, End Date, Participants, Status.
- Status computed as: `Upcoming` if `start_date > now`, `Active` if `start_date <= now < end_date`, `Ended` if `end_date <= now`.
- Participant count = count of `Registration` rows with `hackathon_id == h.id` and `status == accepted`.
- Sidebar: detail view with Name, Dates, Venue, Max Participants, Waitlist Enabled.
- Modal edit form: same fields as Step 6. For *new* hackathons, `organizer_id` is a required dropdown populated from existing users (default: first organizer found). For *edits*, `organizer_id` is preserved from the existing row and not shown.
- Buttons: "Refresh", "Create New" (opens modal with empty form), "Delete" (confirm dialog).

### Tab 3: Users
- `DataTableWidget` columns: ID, Name, Email, Role, Banned.
- Filters: role dropdown (select: all/organizer/participant/judge/volunteer), search input (filters name/email by substring, case-insensitive).
- Sidebar: detail view with all user fields.
- Actions per row (in sidebar or modal): "Change Role" → role select dialog, "Ban" → confirm dialog, "Unban" → no confirm.
- Edge case: banning sets `is_banned = True`, `banned_at = now(UTC)`. Unban clears both.

### Tab 4: Registrations
- `DataTableWidget` columns: ID, User Name, Hackathon Name, Status, Applied At.
- Filter by status: dropdown (all/pending/accepted/rejected/waitlisted/offered/checked_in).
- Selection: `Space` toggles checkbox on current row. `Ctrl+A` selects all visible rows.
- Bulk actions (enabled only when 1+ rows selected): "Accept Selected", "Waitlist Selected", "Reject Selected".
- Each bulk action shows a `ConfirmDialog` with count of selected rows.
- Single-row actions: sidebar shows user + hackathon details. "Accept", "Waitlist", "Reject" buttons.

### Tab 5: Settings
- `ConfigFormWidget` with all keys from `ConfigService.DEFAULTS`.
- Each row: label (human-readable title-cased version of the key, e.g., `hackathon_primary_color` → "Hackathon Primary Color"), current value, source badge (env = yellow, db = green, default = dim).
- Read-only env vars: show value but disable editing. Source badge = "env (read-only)".
- Editable DB values: text input. Changes are saved on `blur` or `Enter` keypress via `ConfigService.set(key, value, db)`. No debounce — discrete saves only.
- "Reset to default" button per editable row → `ConfirmDialog` → `ConfigService.delete(key, db)`.

## Data Flow

```
TUI Screen → Async SQLAlchemy Session (cli.utils.db_session)
           → Service layer (ConfigService, existing services where available)
           → Raw model queries (for simple counts/listing not wrapped by a service)
           → PostgreSQL
```

No HTTP requests. The TUI is a standalone DB client. Where existing services exist (e.g., `ConfigService`), the TUI uses them. For simple CRUD not yet extracted to services, raw SQLAlchemy queries against models are acceptable. All mutations that have service-layer validation in the HTTP API should eventually call through the same service layer to avoid inconsistency.

## Error Handling

- DB connection failure on mount → show reconnect button, disable data-dependent tabs.
- Service method failure → Textual `notify()` toast (red for errors, green for success).
- Form validation failure → show inline error message below offending field, block submit.
- Alembic subprocess failure → capture stderr, show in red toast, keep screen open for retry.
- All DB writes wrapped in try/except with explicit `await db.rollback()` on failure.
- Unsaved changes guard: if any form is dirty, `Ctrl+Q` shows confirm dialog before quitting. Same guard applies to wizard Back/Next navigation — pressing Back or Next with a dirty form shows a "Discard changes?" confirm dialog.

## Testing Strategy

- Textual provides `Pilot` for UI automation testing.
- Each screen gets a `test_<screen>.py` file using `Pilot`.
- Mock `db_session()` and services same as CLI tests (AsyncMock context manager pattern).
- Wizard tests: simulate button clicks / key presses to flow Step 1 → Step 7.
- Dashboard tests: switch tabs, type in filter inputs, trigger refresh.
- Form tests: enter invalid data, assert error message appears; enter valid data, assert submit event fires.
- Confirm dialog tests: press Enter to confirm, Esc to cancel.

## Dependencies

Add to `pyproject.toml`:
```toml
dependencies = [
    ...
    "textual>=0.52",
]
```

## Entry Points

```python
# cli/main.py
from cli.tui.app import TuiApp

@app.command("tui")
def tui():
    """Launch the interactive TUI dashboard."""
    tui_app = TuiApp()
    tui_app.run()

@app.command("setup")
def setup():
    """Run the interactive setup wizard."""
    tui_app = TuiApp(mode="setup")
    tui_app.run()
```

## Keybindings

- `Ctrl+Q` — quit (confirm if unsaved changes in any form).
- `Ctrl+C` — hard quit (no confirm, standard terminal behavior).
- `Tab` / `Shift+Tab` — cycle focus within current tab.
- `Ctrl+R` — refresh current tab data.
- `?` — help overlay with all keybindings.
- `Esc` — close modal / clear selection / unfocus input.
- `Space` — toggle row selection (in tables with bulk actions only).
- `Ctrl+A` — select all visible rows (bulk action tables only).

---

*Approved for implementation planning.*
