# OpenHack Group 1: Core Structural Improvements — Design Spec

**Date:** 2026-05-11
**Scope:** Backend-only changes for multi-hackathon support, custom registration questions, and registration review notes.

---

## 1. Multi-Hackathon Support

### Goal
Remove the single-hackathon-per-portal limit so one OpenHack deployment can host multiple hackathons with shared user accounts.

### Assumption
The database schema was already built with `hackathon_id` foreign keys on most child tables. The primary remaining work is removing the enforcement block in route code, auditing remaining hardcoded assumptions, and making organizer role checks hackathon-scoped.

### Model Changes
**No new models.** Existing tables already support this:
- `Hackathon` — top-level, one row per event.
- `Registration`, `Team`, `Submission`, `JudgingSession`, `Announcement`, `Workshop`, `Sponsor`, `Prize`, `HelpRequest`, `Track` — all have `hackathon_id`.

**One schema addition:**
- `HackathonOrganizer` junction table (or formalization of existing co-organizer pattern) to track which users are organizers for which hackathons. The existing `Hackathon` table already has `organizer_id` as the primary organizer. The co-organizer list is currently stored in `co_organizer_ids` (JSONB array). We keep this pattern for simplicity, but audit all queries that check "is this user an organizer?" to ensure they check both `organizer_id` and `co_organizer_ids` scoped to the specific `hackathon_id`.

### Route Changes
- `backend/app/routes/hackathons.py` — Remove the block that prevents creating a second `Hackathon` (lines ~105-108).
- `GET /api/hackathons` — Return all hackathons the current user has any relationship with (organizer, participant via registration, judge). Add query params: `?role=organizer&status=active`.
- `GET /api/hackathons/{id}` — No change; already fetches by ID.
- All organizer-scoped routes (`dashboard.py`, `registrations_organizer.py`, `tracks.py`, etc.) — Verify they already filter by `hackathon_id` passed in the path or query. No hardcoded global hackathon lookups remain.
- `backend/app/routes/hacker_dashboard.py` — Ensure it takes `{hackathon_id}` explicitly.

### Auth / Role Scope
- `UserRole` enum (`organizer`, `participant`, `judge`) stays global conceptually, but effective role is determined per-hackathon at runtime:
  - Participant: has a `Registration` row for this hackathon.
  - Organizer: `Hackathon.organizer_id == user.id` or `user.id in Hackathon.co_organizer_ids`.
  - Judge: to be determined by judge assignment presence in `JudgeAssignment` for this hackathon.
- JWT token only carries `user_id`. Route dependency `get_current_user` stays the same.
- **New dependency:** `require_hackathon_organizer(hackathon_id: UUID)` — calls `get_current_user`, then queries the specific `Hackathon` by ID and checks `organizer_id == user.id` OR `user.id in co_organizer_ids`. Raises 403 if not an organizer for this hackathon. This replaces the global `require_organizer` on all hackathon-scoped routes.

### Migration
- Alembic migration: verify no data migration needed (existing single-hackathon deployments simply have one row; new deployments can create more).

---

## 2. Custom Registration Questions

### Goal
Allow hackathon organizers to define custom application questions that hackers answer during registration, with support for multiple question types.

### New Models

#### `RegistrationQuestion`
| Column | Type | Notes |
|--------|------|-------|
| `id` | `Guid` (UUID) | PK |
| `hackathon_id` | `Guid` (FK → Hackathon) | Scoped per hackathon |
| `question_text` | `String(500)` | The prompt shown to hackers |
| `question_type` | `Enum` | `text`, `textarea`, `number`, `select`, `multiselect`, `checkbox`, `url`, `file` |
| `options` | `JsonType` | JSON array of strings for `select`/`multiselect`; null for others |
| `is_required` | `Boolean` | Default `True` |
| `sort_order` | `Integer` | Display order within the hackathon's question list |
| `created_at` | `DateTime` | UTC |
| `updated_at` | `DateTime` | UTC |

#### `RegistrationAnswer`
| Column | Type | Notes |
|--------|------|-------|
| `id` | `Guid` (UUID) | PK |
| `registration_id` | `Guid` (FK → Registration) | Cascade delete |
| `question_id` | `Guid` (FK → RegistrationQuestion) | Cascade delete |
| `answer_value` | `Text` | Stores JSON string for structured answers (multiselect, checkbox array), plain text for others |
| `created_at` | `DateTime` | UTC |
| `updated_at` | `DateTime` | UTC |

**Unique constraint:** `(registration_id, question_id)` — one answer per question per registration.

**Indexes:**
- `RegistrationQuestion`: index on `hackathon_id`
- `RegistrationAnswer`: index on `registration_id`, index on `question_id`
- `RegistrationReviewNote`: index on `registration_id`, index on `organizer_id`

### Route Changes

**Organizer-only:**
- `POST /api/hackathons/{hackathon_id}/registration-questions`
  - Body: `{question_text, question_type, options?, is_required, sort_order}`
  - Validates: `options` required for `select`/`multiselect`, forbidden for others.

- `GET /api/hackathons/{hackathon_id}/registration-questions`
  - Returns list ordered by `sort_order`. Requires `require_clerk_user` (user must be logged in) but does NOT require an existing registration — unregistered hackers need to see questions before they can register.

- `PUT /api/hackathons/{hackathon_id}/registration-questions/{question_id}`
  - Full update. If question type changes, existing answers may become invalid — allow this; organizer responsibility.

- `DELETE /api/hackathons/{hackathon_id}/registration-questions/{question_id}`
  - Cascade deletes related `RegistrationAnswer` rows.

**Registration flow integration:**
- `POST /api/hackathons/{hackathon_id}/register` (existing `registrations.py`) — accept `answers: [{question_id, value}, ...]` in payload.
  - Validation: all `is_required` questions must be present. `value` type must match `question_type`.
  - Atomic: answers are inserted in the same DB transaction as the `Registration` row.

- `GET /api/registrations/{registration_id}` (existing) — include `answers` array in response.

- Create `PUT /api/registrations/{registration_id}` — allow updating answers if registration is still in `pending` status. Once accepted/rejected, answers are read-only.

### Validation Rules
| question_type | value validation |
|---------------|------------------|
| `text` | non-empty string, max 500 chars |
| `textarea` | non-empty string, max 2000 chars |
| `number` | valid float/integer |
| `select` | must be one of `options` |
| `multiselect` | array of strings, each must be in `options` |
| `checkbox` | boolean |
| `url` | valid URL format |
| `file` | URL string (uploaded via MinIO upload endpoint, then URL stored here) |

### Pydantic Schemas
- `RegistrationQuestionCreate` — `question_text`, `question_type`, `options`, `is_required`, `sort_order`
- `RegistrationQuestionUpdate` — same fields, all optional
- `RegistrationAnswerItem` — `question_id` (UUID), `value` (Any — parsed/validated at runtime based on question type)
- `RegistrationCreate` (update existing stub in `registrations.py`) — add `answers: List[RegistrationAnswerItem]` field

### SQLAlchemy Relationships
- `RegistrationQuestion`:
  - `hackathon = relationship("Hackathon", back_populates="registration_questions")`
  - `answers = relationship("RegistrationAnswer", cascade="all, delete-orphan", back_populates="question")`
- `RegistrationAnswer`:
  - `registration = relationship("Registration", back_populates="answers")`
  - `question = relationship("RegistrationQuestion", back_populates="answers")`
- `Registration`:
  - `answers = relationship("RegistrationAnswer", cascade="all, delete-orphan", back_populates="registration")`
  - `review_notes = relationship("RegistrationReviewNote", cascade="all, delete-orphan", back_populates="registration")`
- `RegistrationReviewNote`:
  - `registration = relationship("Registration", back_populates="review_notes")`
  - `organizer = relationship("User")`

### Migration
- Alembic migration creates `registration_questions` and `registration_answers` tables.

---

## 3. Registration Review Notes

### Goal
Allow organizers to leave internal notes and optional ratings on individual registrations during the application review process.

### New Model

#### `RegistrationReviewNote`
| Column | Type | Notes |
|--------|------|-------|
| `id` | `Guid` (UUID) | PK |
| `registration_id` | `Guid` (FK → Registration) | Cascade delete |
| `organizer_id` | `Guid` (FK → User) | Who wrote the note |
| `note_text` | `Text` | Free-form review text |
| `rating` | `Integer` | 1–5, optional (null allowed) |
| `created_at` | `DateTime` | UTC |
| `updated_at` | `DateTime` | UTC |

### Route Changes

**Organizer-only, scoped to hackathon:**
- `POST /api/hackathons/{hackathon_id}/registrations/{registration_id}/notes`
  - Body: `{note_text, rating?}`
  - `organizer_id` set from `current_user.id`.

- `GET /api/hackathons/{hackathon_id}/registrations/{registration_id}/notes`
  - Returns list ordered by `created_at` desc. Includes organizer name/email.

- `PUT /api/hackathons/{hackathon_id}/registrations/{registration_id}/notes/{note_id}`
  - Only the original author (`organizer_id`) can edit.

- `DELETE /api/hackathons/{hackathon_id}/registrations/{registration_id}/notes/{note_id}`
  - Only the original author can delete.

**Dashboard integration:**
- `GET /api/hackathons/{hackathon_id}/registrations` (existing `registrations_organizer.py`) — include computed fields:
  - `review_notes_count`
  - `average_rating` (null if no ratings)
- Add query params for filtering:
  - `?has_notes=true/false`
  - `?min_rating=3`

### Migration
- Alembic migration creates `registration_review_notes` table.

---

## 4. Cross-Cutting Concerns

### File Uploads (for `file` question type)
- Reuse existing MinIO/S3 infrastructure (already in Docker stack).
- Extend `StorageService` in `backend/app/storage.py`:
  - Add `upload_generic(file, allowed_types: set[str] | None = None, max_size: int | None = None)` method.
  - Default `allowed_types` for registration uploads: `{"application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain", "image/png", "image/jpeg"}`.
  - Default `max_size` for registration uploads: 5 MB.
- Add `POST /api/hackathons/{hackathon_id}/upload` that accepts multipart file, uses `upload_generic`, stores in MinIO under `hackathons/{hackathon_id}/uploads/{uuid}`, returns public/presigned URL.
- Store the returned URL in `RegistrationAnswer.answer_value` when `question_type == file`.

### Error Handling
- Standard OpenFastAPI patterns: 404 when hackathon/registration/question not found; 403 when role check fails; 422 when validation fails.

### Testing
- Each new route gets corresponding tests in `tests/routes/` following existing patterns.
- Service layer tests for validation logic (question types, answer formats).

---

## 5. Files to Modify / Create

### New files
- `backend/app/models_registration.py` — `RegistrationQuestion`, `RegistrationAnswer`, `RegistrationReviewNote` (or add to existing `models.py` if preferred)
- `backend/app/routes/registration_questions.py`
- `backend/app/routes/registration_notes.py`
- `backend/app/services/registration_question_service.py`
- `backend/app/services/registration_note_service.py`
- Corresponding test files

### Modified files
- `backend/app/models.py` — add new models
- `backend/app/main.py` — register new routers
- `backend/app/routes/hackathons.py` — remove single-hackathon limit
- `backend/app/routes/registrations.py` — accept and return answers
- `backend/app/routes/registrations_organizer.py` — include review note aggregations
- `backend/app/routes/config.py` or new route — file upload endpoint for MinIO

---

## Approval

| Feature | Status |
|---------|--------|
| Multi-hackathon support | Approved |
| Custom registration questions | Approved |
| Registration review notes | Approved |
