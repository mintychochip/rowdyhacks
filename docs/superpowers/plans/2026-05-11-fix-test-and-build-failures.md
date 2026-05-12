# Fix Test and Build Failures — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all failing backend tests and frontend build errors so the project is green.

**Architecture:** Five independent bug fixes across backend schemas, route metadata, SDK generator script, missing module stub, and frontend TypeScript/type tokens.

**Tech Stack:** FastAPI + SQLAlchemy (backend), React + Vite + TypeScript (frontend), Pydantic v2, pytest, ruff.

---

## Chunk 1: Backend — `RegistrationCreate` Schema

**Files:**
- Modify: `backend/app/schemas/__init__.py:118-131`
- Test: `backend/tests/test_registrations.py`

- [ ] **Step 1: Add fields to `RegistrationCreate`**

```python
class RegistrationCreate(BaseModel):
    """Pydantic schema for creating a new hackathon registration.

    Behavior:
    1. Validates team_name, team_members, and optional social/profile links.
    2. Consumed by POST /api/hackathons/{hackathon_id}/register.

    Raises: ValidationError on unexpected extra fields if strict mode is enabled.
    Side Effects: None.
    Dependencies: pydantic.BaseModel.
    Consumers: POST /api/hackathons/{hackathon_id}/register route, signup wizard.
    """

    team_name: str | None = None
    team_members: list[str] | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    resume_url: str | None = None
```

- [ ] **Step 2: Run affected registration tests**

Run: `pytest backend/tests/test_registrations.py -v --tb=short`
Expected: All 12 tests pass (0 failures).

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/__init__.py
git commit -m "fix(schemas): add RegistrationCreate fields (team_name, team_members, links)"
```

---

## Chunk 2: Backend — Duplicate FastAPI Operation IDs

**Files:**
- Modify: `backend/app/routes/registrations_organizer.py:57-195`
- Test: `backend/tests/test_generate_sdk.py`

- [ ] **Step 1: Add `operation_id` kwargs to organizer routes**

Add `operation_id` to each of these decorators in `registrations_organizer.py`:

```python
@router.get("/{hackathon_id}/registrations", operation_id="organizer_list_hackathon_registrations")

@router.post("/{hackathon_id}/registrations/{registration_id}/accept", operation_id="organizer_accept_registration")

@router.post("/{hackathon_id}/registrations/{registration_id}/reject", operation_id="organizer_reject_registration")

@router.post("/{hackathon_id}/registrations/{registration_id}/checkin", operation_id="organizer_checkin_registration")
```

- [ ] **Step 2: Run SDK generator test**

Run: `pytest backend/tests/test_generate_sdk.py -v --tb=short`
Expected: `test_generate_sdk_creates_output_file` passes (script exits 0, file created).

- [ ] **Step 3: Commit**

```bash
git add backend/app/routes/registrations_organizer.py
git commit -m "fix(routes): disambiguate organizer operation IDs for SDK generation"
```

---

## Chunk 3: Backend — SDK Generator Script Bug

**Files:**
- Modify: `backend/scripts/generate-sdk.py:17-25`
- Test: `backend/tests/test_generate_sdk.py`

- [ ] **Step 1: Guard `_resolve_ref` against non-dict schemas**

```python
def _resolve_ref(spec, schema):
    if not isinstance(schema, dict):
        return schema
    if "$ref" not in schema:
        return schema
    ...
```

- [ ] **Step 2: Run SDK generator test again**

Run: `pytest backend/tests/test_generate_sdk.py -v --tb=short`
Expected: Passes.

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/generate-sdk.py
git commit -m "fix(scripts): guard _resolve_ref against boolean schema values"
```

---

## Chunk 4: Backend — Missing `app.assistant.site_pages` Module

**Files:**
- Create: `backend/app/assistant/site_pages.py`
- Test: `backend/tests/test_main.py`

- [ ] **Step 1: Create the missing module**

```python
"""Site page indexing stub for the assistant vector store."""


async def index_site_pages() -> None:
    """Index static site pages into the assistant vector store.

    Currently a no-op until site content indexing is implemented.
    """
    pass
```

- [ ] **Step 2: Run lifespan test**

Run: `pytest backend/tests/test_main.py::TestLifespan::test_lifespan_starts_and_shuts_down -v --tb=short`
Expected: Passes (no more `No module named 'app.assistant.site_pages'`).

- [ ] **Step 3: Commit**

```bash
git add backend/app/assistant/site_pages.py
git commit -m "fix(assistant): add missing site_pages stub module"
```

---

## Chunk 5: Frontend — Build Errors

**Files:**
- Create: `frontend/src/components/CommandPalette.tsx`
- Modify: `frontend/src/theme.ts`
- Modify: `frontend/src/pages/AssistantPage.tsx`
- Modify: `frontend/src/components/Primitives.tsx`
- Modify: `frontend/src/components/TagInput.tsx`
- Modify: `frontend/src/components/UrlInput.tsx`
- Modify: `frontend/src/pages/ApplyPage.tsx`
- Modify: `frontend/src/pages/CheckInPage.tsx`
- Modify: `frontend/src/pages/Dashboard.tsx`
- Modify: `frontend/src/components/Layout.tsx`
- Test: `cd frontend && npm run build`

- [ ] **Step 1: Add missing shadow tokens to theme**

In `frontend/src/theme.ts`, add to the `shadows` object:

```typescript
elevated: "0 4px 12px rgba(0, 0, 0, 0.4)",
card: "0 1px 2px rgba(0, 0, 0, 0.3)",
```

- [ ] **Step 2: Create stub `CommandPalette.tsx`**

```typescript
import React from "react";

export const CommandPalette: React.FC = () => {
  return null;
};
```

- [ ] **Step 3: Fix `Layout.tsx` nav item type**

Change the nav item type to accept `children?: React.ReactNode` if needed, or remove the children usage if it's not part of the intended design. (Inspect the actual usage first.)

- [ ] **Step 4: Fix `AssistantPage.tsx` type mismatches**

Cast/adjust types so `Tool[]` is compatible with `AgentTool[]` and `ChatMessage[]` with `AgentMessage[]`. Likely needs updating import types or adding missing fields (`createdAt`) to the local message creation.

- [ ] **Step 5: Run frontend build**

Run: `cd frontend && npm run build`
Expected: 0 TypeScript errors, build succeeds.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/theme.ts frontend/src/components/CommandPalette.tsx frontend/src/pages/AssistantPage.tsx frontend/src/components/Layout.tsx frontend/src/components/Primitives.tsx frontend/src/components/TagInput.tsx frontend/src/components/UrlInput.tsx frontend/src/pages/ApplyPage.tsx frontend/src/pages/CheckInPage.tsx frontend/src/pages/Dashboard.tsx
git commit -m "fix(frontend): resolve build errors — missing components, theme tokens, type mismatches"
```

---

## Final Verification

- [ ] **Run full backend test suite**

```bash
cd backend
pytest tests/ -v --tb=short
```
Expected: All pass, 0 failures.

- [ ] **Run frontend build**

```bash
cd frontend
npm run build
```
Expected: 0 errors.

- [ ] **Commit if any final tweaks**
