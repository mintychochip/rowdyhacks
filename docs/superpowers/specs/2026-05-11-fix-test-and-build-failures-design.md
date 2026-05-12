# Fix Test and Build Failures — Design Spec

## Date
2026-05-11

## Scope
Fix all currently failing backend tests and frontend build errors identified via CLI diagnostics.

## Issues and Fixes

### 1. `RegistrationCreate` Schema Is Empty
- **File:** `backend/app/schemas/__init__.py`
- **Problem:** `RegistrationCreate` is `pass` (no fields). The service reads `team_name` / `team_members` via `getattr`, but Pydantic drops extra fields.
- **Fix:** Add `team_name: str | None`, `team_members: list[str] | None`, `linkedin_url`, `github_url`, `resume_url` as optional fields.

### 2. Duplicate FastAPI Operation IDs
- **Files:** `backend/app/routes/registrations.py`, `backend/app/routes/registrations_organizer.py`
- **Problem:** Both files define `list_hackathon_registrations`, `accept_registration`, `reject_registration`, `checkin_registration`. FastAPI auto-generates operation IDs from function names, causing SDK generator warnings/crashes.
- **Fix:** Add explicit `operation_id` kwargs to the organizer routes with disambiguated names (e.g., `organizer_list_hackathon_registrations`).

### 3. SDK Generator Script Bug
- **File:** `backend/scripts/generate-sdk.py`
- **Problem:** `_resolve_ref` assumes `schema` is always a dict, but OpenAPI can have `additionalProperties: true` (a boolean), causing `TypeError: argument of type 'bool' is not iterable`.
- **Fix:** Guard `_resolve_ref` to return non-dict schemas unchanged.

### 4. Missing `app.assistant.site_pages` Module
- **File:** `backend/app/main.py` (line 125)
- **Problem:** Lifespan imports `app.assistant.site_pages.index_site_pages`, but the module does not exist.
- **Fix:** Create `backend/app/assistant/site_pages.py` with a no-op `async def index_site_pages(): pass`.

### 5. Frontend Build Errors
- **Files:** Multiple (see below)
- **Problems:**
  - `Layout.tsx` imports missing `CommandPalette` component
  - `theme.ts` missing `shadows.elevated` and `shadows.card` tokens
  - `AssistantPage.tsx` type mismatches: `Tool[]` vs `AgentTool[]`, `ChatMessage[]` vs `AgentMessage[]`
- **Fixes:**
  - Create stub `frontend/src/components/CommandPalette.tsx`
  - Add missing shadow tokens to `frontend/src/theme.ts`
  - Add type casts / interface alignment in `AssistantPage.tsx`

## Success Criteria
- `pytest backend/tests/` returns 0 failures
- `npm run build` in `frontend/` completes without TypeScript errors
- Backend app imports cleanly (`python -c "from app.main import app"`)
- SDK generator script runs successfully (`python backend/scripts/generate-sdk.py`)

## Out of Scope
- Functional changes to registration logic (only schema fix)
- Visual/design changes to frontend (only fix build errors)
- Adding new features
