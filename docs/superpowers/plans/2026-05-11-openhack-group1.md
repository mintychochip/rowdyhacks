# OpenHack Group 1 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement multi-hackathon support, custom registration questions, and registration review notes in the OpenHack backend.

**Architecture:** Remove the single-hackathon-per-portal limit by introducing a `require_hackathon_organizer` scoped dependency. Add `RegistrationQuestion`/`RegistrationAnswer` models with a validation service. Add `RegistrationReviewNote` for organizer applicant review. All changes follow existing FastAPI + SQLAlchemy + Alembic patterns.

**Tech Stack:** FastAPI, SQLAlchemy (async), PostgreSQL/SQLite, Alembic, Pydantic, Pytest, MinIO/S3

---

## File Map

| File | Responsibility |
|------|---------------|
| `backend/app/clerk_auth.py` | Add `require_hackathon_organizer` dependency |
| `backend/app/models.py` | Add `RegistrationQuestion`, `RegistrationAnswer`, `RegistrationReviewNote` models + relationships |
| `backend/app/schemas/__init__.py` | Add Pydantic schemas for questions, answers, notes, and fix `RegistrationCreate` |
| `backend/app/storage.py` | Add `upload_generic` method for non-image file uploads |
| `backend/app/services/registration_question_service.py` | Validation service for question CRUD and answer validation |
| `backend/app/services/registration_note_service.py` | Service for review note CRUD and aggregation |
| `backend/app/routes/registration_questions.py` | CRUD routes for questions + hackathon-scoped upload endpoint |
| `backend/app/routes/registration_notes.py` | CRUD routes for review notes |
| `backend/app/routes/hackathons.py` | Remove single-hackathon limit, update list endpoint |
| `backend/app/routes/registrations.py` | Integrate answers into registration create/update |
| `backend/app/routes/registrations_organizer.py` | Add review note aggregations to list endpoint |
| `backend/app/main.py` | Register new routers |
| `backend/alembic/versions/2026_05_11_add_registration_questions_and_notes.py` | Alembic migration |
| `backend/tests/routes/test_registration_questions.py` | Tests for question routes |
| `backend/tests/routes/test_registration_notes.py` | Tests for review note routes |
| `backend/tests/conftest.py` | Add `require_hackathon_organizer` override fixture |

---

## Chunk 1: Multi-Hackathon Support

### Task 1: Add `require_hackathon_organizer` dependency

**Files:**
- Modify: `backend/app/clerk_auth.py`
- Test: `backend/tests/conftest.py`

- [ ] **Step 1: Write the dependency**

```python
# In backend/app/clerk_auth.py, after require_organizer

import uuid as uuid_module
from sqlalchemy import and_, select

async def require_hackathon_organizer(
    hackathon_id: uuid_module.UUID,
    authorization: str | None = Header(alias="Authorization", default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """FastAPI dependency: validate Clerk token and require organizer role for a specific hackathon.

    Returns the same dict as require_clerk_user_with_db.
    Raises 403 if user is not an organizer for this hackathon.
    """
    auth = await require_clerk_user_with_db(authorization, db)
    user = auth["user"]

    from app.models import Hackathon, HackathonOrganizer

    # Primary organizer check
    result = await db.execute(
        select(Hackathon).where(
            and_(Hackathon.id == hackathon_id, Hackathon.organizer_id == user.id)
        )
    )
    if result.scalar_one_or_none():
        return auth

    # Co-organizer check
    co_result = await db.execute(
        select(HackathonOrganizer).where(
            and_(
                HackathonOrganizer.hackathon_id == hackathon_id,
                HackathonOrganizer.user_id == user.id,
            )
        )
    )
    if co_result.scalar_one_or_none():
        return auth

    raise HTTPException(status_code=403, detail="Only the hackathon organizer can perform this action")
```

- [ ] **Step 2: Add conftest override**

```python
# In backend/tests/conftest.py, after _override_require_organizer

async def _override_require_hackathon_organizer(hackathon_id: uuid.UUID):
    """Override require_hackathon_organizer for testing."""
    return {
        "user": type(
            "FakeUser",
            (),
            {
                "role": UserRole.organizer,
                "id": "test-organizer-id",
                "email": "organizer@test.com",
                "name": "Test Organizer",
            },
        )(),
        "sub": "test-organizer-id",
        "email": "organizer@test.com",
        "payload": {},
    }
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/clerk_auth.py backend/tests/conftest.py
git commit -m "feat(auth): add require_hackathon_organizer scoped dependency"
```

---

### Task 2: Remove single-hackathon limit in hackathons.py

**Files:**
- Modify: `backend/app/routes/hackathons.py:79-108`
- Test: `backend/tests/routes/test_hackathons.py` (create if needed, or manual curl)

- [ ] **Step 1: Remove the single-hackathon block**

In `backend/app/routes/hackathons.py`, replace:

```python
    # Only one hackathon per portal
    existing = await db.execute(select(Hackathon).limit(1))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="A hackathon already exists. Only one hackathon is supported.")
```

with nothing (just delete lines 105-108).

- [ ] **Step 2: Update `GET /api/hackathons` list endpoint**

Find the existing list endpoint in `hackathons.py`. If it doesn't exist, add one. If it exists, modify it to return hackathons the user has a relationship with.

```python
@router.get("")
async def list_hackathons(
    role: str | None = Query(None, description="Filter by role: organizer, participant, judge"),
    status: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    auth: dict = Depends(require_clerk_user_with_db),
    db: AsyncSession = Depends(get_db),
):
    """List hackathons the current user has a relationship with."""
    user = auth["user"]

    from app.models import Registration

    # Build a subquery of hackathon IDs this user is related to
    related_ids = set()

    # As organizer
    org_result = await db.execute(
        select(Hackathon.id).where(Hackathon.organizer_id == user.id)
    )
    related_ids.update(str(r) for r in org_result.scalars().all())

    # As co-organizer
    co_result = await db.execute(
        select(HackathonOrganizer.hackathon_id).where(HackathonOrganizer.user_id == user.id)
    )
    related_ids.update(str(r) for r in co_result.scalars().all())

    # As participant
    reg_result = await db.execute(
        select(Registration.hackathon_id).where(Registration.user_id == user.id)
    )
    related_ids.update(str(r) for r in reg_result.scalars().all())

    if not related_ids:
        return {"hackathons": [], "total": 0, "limit": limit, "offset": offset}

    query = select(Hackathon).where(Hackathon.id.in_(list(related_ids)))
    count_query = select(func.count(Hackathon.id)).where(Hackathon.id.in_(list(related_ids)))

    if status:
        query = query.where(Hackathon.status == status)
        count_query = count_query.where(Hackathon.status == status)

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(Hackathon.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    hackathons = result.scalars().all()

    return {
        "hackathons": [
            {
                "id": str(h.id),
                "name": h.name,
                "start_date": h.start_date.isoformat() if h.start_date else None,
                "end_date": h.end_date.isoformat() if h.end_date else None,
                "organizer_id": h.organizer_id,
                "description": h.description,
                "application_deadline": h.application_deadline.isoformat() if h.application_deadline else None,
                "max_participants": h.max_participants,
                "current_participants": h.current_participants,
                "waitlist_enabled": h.waitlist_enabled,
                "created_at": h.created_at.isoformat(),
            }
            for h in hackathons
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/routes/hackathons.py
git commit -m "feat(hackathons): remove single-hackathon limit, add user-scoped list endpoint"
```

---

### Task 3: Fix registrations.py organizer check to use scoped dependency

**Files:**
- Modify: `backend/app/routes/registrations.py:60-94`

- [ ] **Step 1: Replace `_ensure_hackathon_organizer` with scoped check**

Replace the existing `_ensure_hackathon_organizer` function in `registrations.py`:

```python
async def _ensure_hackathon_organizer(
    db: AsyncSession,
    user_id: str,
    hackathon_id: uuid.UUID,
) -> Hackathon:
    """Verify the current user is the organizer or co-organizer of the given hackathon."""
    from app.clerk_auth import require_hackathon_organizer
    from app.models import Hackathon

    # This reuses the same logic as the dependency but as a callable
    hk_result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = hk_result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    # Primary organizer check
    if hackathon.organizer_id == user_id:
        return hackathon

    # Co-organizer check
    co_result = await db.execute(
        select(HackathonOrganizer).where(
            and_(HackathonOrganizer.hackathon_id == hackathon_id, HackathonOrganizer.user_id == user_id)
        )
    )
    if co_result.scalar_one_or_none():
        return hackathon

    raise HTTPException(status_code=403, detail="Only the hackathon organizer can perform this action")
```

Note: Keep the existing callers of `_ensure_hackathon_organizer` unchanged — they pass `(db, user_payload["sub"], hackathon_id)` which still works.

- [ ] **Step 2: Remove global role check from the helper**

The existing helper checks `user.role != UserRole.organizer` at line 77. Remove that line so co-organizers who have global `participant` role are not rejected.

```python
    # REMOVE THIS BLOCK:
    # user = user_result.scalar_one_or_none()
    # if not user or user.role != UserRole.organizer:
    #     raise HTTPException(status_code=403, detail="Only organizers can perform this action")
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/routes/registrations.py
git commit -m "fix(registrations): remove global role check from hackathon organizer verification"
```

---

## Chunk 2: Custom Registration Questions — Foundation

### Task 4: Add models and relationships

**Files:**
- Modify: `backend/app/models.py`

- [ ] **Step 1: Add `QuestionType` enum**

After the existing enums (around line 175), add:

```python
class QuestionType(str, enum.Enum):
    """Type of a custom registration question."""

    text = "text"
    textarea = "textarea"
    number = "number"
    select = "select"
    multiselect = "multiselect"
    checkbox = "checkbox"
    url = "url"
    file = "file"
```

- [ ] **Step 2: Add `RegistrationQuestion` model**

After the `Registration` model (around line 473), add:

```python
class RegistrationQuestion(Base):
    """A custom question that hackers answer during registration."""

    __tablename__ = "registration_questions"
    __table_args__ = (Index("ix_registration_questions_hackathon_id", "hackathon_id"),)

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False)
    question_text = Column(String(500), nullable=False)
    question_type = Column(SAEnum(QuestionType), nullable=False)
    options = Column(JsonType, nullable=True)  # JSON array of strings for select/multiselect
    is_required = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)

    hackathon = relationship("Hackathon", back_populates="registration_questions")
    answers = relationship("RegistrationAnswer", cascade="all, delete-orphan", back_populates="question")

    def __repr__(self) -> str:
        return f"<RegistrationQuestion {self.question_text[:30]}...>"
```

- [ ] **Step 3: Add `RegistrationAnswer` model**

```python
class RegistrationAnswer(Base):
    """A hacker's answer to a custom registration question."""

    __tablename__ = "registration_answers"
    __table_args__ = (
        Index("ix_registration_answers_registration_id", "registration_id"),
        Index("ix_registration_answers_question_id", "question_id"),
        Index("ix_registration_answers_unique", "registration_id", "question_id", unique=True),
    )

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    registration_id = Column(Guid, ForeignKey("registrations.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(Guid, ForeignKey("registration_questions.id", ondelete="CASCADE"), nullable=False)
    answer_value = Column(Text, nullable=False)  # JSON string for structured answers, plain text for others
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)

    registration = relationship("Registration", back_populates="answers")
    question = relationship("RegistrationQuestion", back_populates="answers")

    def __repr__(self) -> str:
        return f"<RegistrationAnswer question={self.question_id}>"
```

- [ ] **Step 4: Add `RegistrationReviewNote` model**

```python
class RegistrationReviewNote(Base):
    """An organizer's internal review note on a registration."""

    __tablename__ = "registration_review_notes"
    __table_args__ = (
        Index("ix_registration_review_notes_registration_id", "registration_id"),
        Index("ix_registration_review_notes_organizer_id", "organizer_id"),
    )

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    registration_id = Column(Guid, ForeignKey("registrations.id", ondelete="CASCADE"), nullable=False)
    organizer_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    note_text = Column(Text, nullable=False)
    rating = Column(Integer, nullable=True)  # 1-5, optional
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)

    registration = relationship("Registration", back_populates="review_notes")
    organizer = relationship("User", foreign_keys=[organizer_id])

    def __repr__(self) -> str:
        return f"<RegistrationReviewNote reg={self.registration_id} rating={self.rating}>"
```

- [ ] **Step 5: Add relationships to existing models**

On `Hackathon` model, add:
```python
    registration_questions = relationship("RegistrationQuestion", back_populates="hackathon", cascade="all, delete-orphan")
```

On `Registration` model, add:
```python
    answers = relationship("RegistrationAnswer", cascade="all, delete-orphan", back_populates="registration")
    review_notes = relationship("RegistrationReviewNote", cascade="all, delete-orphan", back_populates="registration")
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/models.py
git commit -m "feat(models): add RegistrationQuestion, RegistrationAnswer, RegistrationReviewNote"
```

---

### Task 5: Add Pydantic schemas

**Files:**
- Modify: `backend/app/schemas/__init__.py`

- [ ] **Step 1: Add question schemas**

```python
from typing import Any, List, Optional
from pydantic import BaseModel, Field

class RegistrationQuestionCreate(BaseModel):
    """Schema for creating a custom registration question."""
    question_text: str = Field(..., max_length=500)
    question_type: str  # one of QuestionType values
    options: Optional[List[str]] = None
    is_required: bool = True
    sort_order: int = 0

class RegistrationQuestionUpdate(BaseModel):
    """Schema for updating a custom registration question."""
    question_text: Optional[str] = Field(None, max_length=500)
    question_type: Optional[str] = None
    options: Optional[List[str]] = None
    is_required: Optional[bool] = None
    sort_order: Optional[int] = None

class RegistrationAnswerItem(BaseModel):
    """Schema for a single answer within a registration payload."""
    question_id: str
    value: Any
```

- [ ] **Step 2: Add review note schemas**

```python
class RegistrationReviewNoteCreate(BaseModel):
    """Schema for creating a review note."""
    note_text: str
    rating: Optional[int] = Field(None, ge=1, le=5)

class RegistrationReviewNoteUpdate(BaseModel):
    """Schema for updating a review note."""
    note_text: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
```

- [ ] **Step 3: Fix `RegistrationCreate` to include all fields + answers**

Replace the `pass` stub:

```python
class RegistrationCreate(BaseModel):
    """Schema for creating a new hackathon registration."""

    team_name: Optional[str] = None
    team_members: Optional[Any] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    resume_url: Optional[str] = None
    experience_level: Optional[str] = None
    t_shirt_size: Optional[str] = None
    phone: Optional[str] = None
    dietary_restrictions: Optional[str] = None
    what_build: Optional[str] = None
    why_participate: Optional[str] = None
    age: Optional[int] = None
    school: Optional[str] = None
    major: Optional[str] = None
    pronouns: Optional[str] = None
    skills: Optional[List[str]] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    answers: Optional[List[RegistrationAnswerItem]] = None
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/__init__.py
git commit -m "feat(schemas): add question, answer, review note schemas; fix RegistrationCreate"
```

---

### Task 6: Create Alembic migration

**Files:**
- Create: `backend/alembic/versions/2026_05_11_add_registration_questions_and_notes.py`

- [ ] **Step 1: Generate migration (or write manually)**

If alembic autogenerate works:
```bash
cd backend
alembic revision --autogenerate -m "add registration questions and notes"
```

If not, create manually following the existing pattern:

```python
"""Add registration_questions, registration_answers, registration_review_notes tables.

Revision ID: 2026_05_11_add_registration_questions_and_notes
Revises: 2026_05_11_add_plugins
Create Date: 2026-05-11 00:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "2026_05_11_add_registration_questions_and_notes"
down_revision: Union[str, None] = "2026_05_11_add_plugins"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    dialect = op.get_context().dialect.name

    if dialect == "postgresql":
        id_type = postgresql.UUID(as_uuid=True)
        created_default = sa.text("now()")
    else:
        id_type = sa.String(36)
        created_default = sa.text("CURRENT_TIMESTAMP")

    op.create_table(
        "registration_questions",
        sa.Column("id", id_type, primary_key=True, nullable=False),
        sa.Column("hackathon_id", id_type, sa.ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_text", sa.String(500), nullable=False),
        sa.Column("question_type", sa.String(20), nullable=False),
        sa.Column("options", sa.Text, nullable=True),  # JSON for SQLite, will be JSONB via JsonType in app
        sa.Column("is_required", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=created_default, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=created_default, nullable=False),
    )
    op.create_index("ix_registration_questions_hackathon_id", "registration_questions", ["hackathon_id"])

    op.create_table(
        "registration_answers",
        sa.Column("id", id_type, primary_key=True, nullable=False),
        sa.Column("registration_id", id_type, sa.ForeignKey("registrations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_id", id_type, sa.ForeignKey("registration_questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("answer_value", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=created_default, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=created_default, nullable=False),
    )
    op.create_index("ix_registration_answers_registration_id", "registration_answers", ["registration_id"])
    op.create_index("ix_registration_answers_question_id", "registration_answers", ["question_id"])
    op.create_index("ix_registration_answers_unique", "registration_answers", ["registration_id", "question_id"], unique=True)

    op.create_table(
        "registration_review_notes",
        sa.Column("id", id_type, primary_key=True, nullable=False),
        sa.Column("registration_id", id_type, sa.ForeignKey("registrations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organizer_id", sa.String(64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("note_text", sa.Text, nullable=False),
        sa.Column("rating", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=created_default, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=created_default, nullable=False),
    )
    op.create_index("ix_registration_review_notes_registration_id", "registration_review_notes", ["registration_id"])
    op.create_index("ix_registration_review_notes_organizer_id", "registration_review_notes", ["organizer_id"])


def downgrade() -> None:
    op.drop_index("ix_registration_review_notes_organizer_id", table_name="registration_review_notes")
    op.drop_index("ix_registration_review_notes_registration_id", table_name="registration_review_notes")
    op.drop_table("registration_review_notes")
    op.drop_index("ix_registration_answers_unique", table_name="registration_answers")
    op.drop_index("ix_registration_answers_question_id", table_name="registration_answers")
    op.drop_index("ix_registration_answers_registration_id", table_name="registration_answers")
    op.drop_table("registration_answers")
    op.drop_index("ix_registration_questions_hackathon_id", table_name="registration_questions")
    op.drop_table("registration_questions")
```

- [ ] **Step 2: Run migration locally**

```bash
cd backend
alembic upgrade head
```

Expected: migration succeeds with no errors.

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/2026_05_11_add_registration_questions_and_notes.py
git commit -m "feat(migrations): add registration questions, answers, and review notes tables"
```

---

### Task 7: Create validation service

**Files:**
- Create: `backend/app/services/registration_question_service.py`

- [ ] **Step 1: Write the service**

```python
"""Service for registration question CRUD and answer validation."""

import json
import uuid
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RegistrationAnswer, RegistrationQuestion, QuestionType


class RegistrationQuestionService:
    """Business logic for custom registration questions and answers."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_questions_for_hackathon(self, hackathon_id: uuid.UUID) -> list[RegistrationQuestion]:
        """Return all questions for a hackathon, ordered by sort_order."""
        result = await self.db.execute(
            select(RegistrationQuestion)
            .where(RegistrationQuestion.hackathon_id == hackathon_id)
            .order_by(RegistrationQuestion.sort_order)
        )
        return list(result.scalars().all())

    async def validate_answers(
        self,
        hackathon_id: uuid.UUID,
        answers: list[dict[str, Any]],
    ) -> list[RegistrationAnswer]:
        """Validate a list of answers against the hackathon's questions.

        Returns a list of RegistrationAnswer objects ready to be added to the DB.
        Raises ValueError with descriptive message on validation failure.
        """
        # Fetch all questions for this hackathon
        questions_result = await self.db.execute(
            select(RegistrationQuestion).where(RegistrationQuestion.hackathon_id == hackathon_id)
        )
        questions = {q.id: q for q in questions_result.scalars().all()}

        # Build lookup for required questions
        required_question_ids = {q.id for q in questions.values() if q.is_required}
        answered_question_ids = set()

        result = []
        for ans in answers:
            qid = ans.get("question_id")
            if not qid:
                raise ValueError("Each answer must have a question_id")
            try:
                qid_uuid = uuid.UUID(qid)
            except ValueError:
                raise ValueError(f"Invalid question_id: {qid}")

            answered_question_ids.add(qid_uuid)
            question = questions.get(qid_uuid)
            if not question:
                raise ValueError(f"Question {qid} does not exist for this hackathon")

            value = ans.get("value")
            validated_value = self._validate_answer_value(question, value)
            result.append(
                RegistrationAnswer(
                    question_id=qid_uuid,
                    answer_value=validated_value,
                )
            )

        # Check all required questions are answered
        missing = required_question_ids - answered_question_ids
        if missing:
            raise ValueError(f"Missing required answers for questions: {[str(m) for m in missing]}")

        return result

    def _validate_answer_value(self, question: RegistrationQuestion, value: Any) -> str:
        """Validate a single answer value against its question type.

        Returns the string to store in answer_value (JSON for structured types).
        """
        qt = question.question_type

        if qt == QuestionType.text:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Question '{question.question_text}': text answer must be a non-empty string")
            if len(value) > 500:
                raise ValueError(f"Question '{question.question_text}': text answer exceeds 500 characters")
            return value

        if qt == QuestionType.textarea:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Question '{question.question_text}': textarea answer must be a non-empty string")
            if len(value) > 2000:
                raise ValueError(f"Question '{question.question_text}': textarea answer exceeds 2000 characters")
            return value

        if qt == QuestionType.number:
            if not isinstance(value, (int, float)):
                raise ValueError(f"Question '{question.question_text}': number answer must be numeric")
            return str(value)

        if qt == QuestionType.select:
            if not isinstance(value, str):
                raise ValueError(f"Question '{question.question_text}': select answer must be a string")
            options = question.options or []
            if value not in options:
                raise ValueError(f"Question '{question.question_text}': '{value}' is not a valid option")
            return value

        if qt == QuestionType.multiselect:
            if not isinstance(value, list):
                raise ValueError(f"Question '{question.question_text}': multiselect answer must be a list")
            options = question.options or []
            for v in value:
                if v not in options:
                    raise ValueError(f"Question '{question.question_text}': '{v}' is not a valid option")
            return json.dumps(value)

        if qt == QuestionType.checkbox:
            if not isinstance(value, bool):
                raise ValueError(f"Question '{question.question_text}': checkbox answer must be a boolean")
            return json.dumps(value)

        if qt == QuestionType.url:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Question '{question.question_text}': URL answer must be a non-empty string")
            # Basic URL format check
            if not value.startswith(("http://", "https://")):
                raise ValueError(f"Question '{question.question_text}': URL must start with http:// or https://")
            return value

        if qt == QuestionType.file:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Question '{question.question_text}': file answer must be a URL string")
            return value

        raise ValueError(f"Unknown question type: {qt}")

    async def create_question(
        self,
        hackathon_id: uuid.UUID,
        question_text: str,
        question_type: str,
        options: list[str] | None,
        is_required: bool,
        sort_order: int,
    ) -> RegistrationQuestion:
        """Create and persist a new registration question."""
        qt = QuestionType(question_type)
        if qt in (QuestionType.select, QuestionType.multiselect):
            if not options:
                raise ValueError(f"Question type '{qt.value}' requires options")
        else:
            if options is not None:
                raise ValueError(f"Question type '{qt.value}' does not accept options")

        question = RegistrationQuestion(
            hackathon_id=hackathon_id,
            question_text=question_text,
            question_type=qt,
            options=options,
            is_required=is_required,
            sort_order=sort_order,
        )
        self.db.add(question)
        await self.db.commit()
        await self.db.refresh(question)
        return question
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/registration_question_service.py
git commit -m "feat(services): add RegistrationQuestionService with validation"
```

---

### Task 8: Create review note service

**Files:**
- Create: `backend/app/services/registration_note_service.py`

- [ ] **Step 1: Write the service**

```python
"""Service for registration review note CRUD and aggregation."""

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RegistrationReviewNote


class RegistrationNoteService:
    """Business logic for organizer review notes on registrations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_note(
        self,
        registration_id: uuid.UUID,
        organizer_id: str,
        note_text: str,
        rating: Optional[int],
    ) -> RegistrationReviewNote:
        """Create a review note."""
        note = RegistrationReviewNote(
            registration_id=registration_id,
            organizer_id=organizer_id,
            note_text=note_text,
            rating=rating,
        )
        self.db.add(note)
        await self.db.commit()
        await self.db.refresh(note)
        return note

    async def list_notes_for_registration(
        self,
        registration_id: uuid.UUID,
    ) -> list[RegistrationReviewNote]:
        """Return all notes for a registration, ordered by created_at desc."""
        result = await self.db.execute(
            select(RegistrationReviewNote)
            .where(RegistrationReviewNote.registration_id == registration_id)
            .order_by(RegistrationReviewNote.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_note(self, note_id: uuid.UUID) -> Optional[RegistrationReviewNote]:
        """Get a single note by ID."""
        result = await self.db.execute(
            select(RegistrationReviewNote).where(RegistrationReviewNote.id == note_id)
        )
        return result.scalar_one_or_none()

    async def update_note(
        self,
        note: RegistrationReviewNote,
        note_text: Optional[str] = None,
        rating: Optional[int] = None,
    ) -> RegistrationReviewNote:
        """Update a note's text and/or rating."""
        if note_text is not None:
            note.note_text = note_text
        if rating is not None:
            note.rating = rating
        await self.db.commit()
        await self.db.refresh(note)
        return note

    async def delete_note(self, note: RegistrationReviewNote) -> None:
        """Delete a note."""
        await self.db.delete(note)
        await self.db.commit()

    async def get_aggregates_for_registration(
        self,
        registration_id: uuid.UUID,
    ) -> dict:
        """Return note count and average rating for a registration."""
        count_result = await self.db.execute(
            select(func.count(RegistrationReviewNote.id))
            .where(RegistrationReviewNote.registration_id == registration_id)
        )
        count = count_result.scalar() or 0

        avg_result = await self.db.execute(
            select(func.avg(RegistrationReviewNote.rating))
            .where(
                RegistrationReviewNote.registration_id == registration_id,
                RegistrationReviewNote.rating.isnot(None),
            )
        )
        avg = avg_result.scalar()

        return {
            "review_notes_count": count,
            "average_rating": round(avg, 2) if avg is not None else None,
        }
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/registration_note_service.py
git commit -m "feat(services): add RegistrationNoteService for review notes"
```

---

## Chunk 3: Custom Registration Questions — Routes & Integration

### Task 9: Create question CRUD routes

**Files:**
- Create: `backend/app/routes/registration_questions.py`

- [ ] **Step 1: Write the router**

```python
"""Routes for custom registration questions."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import require_clerk_user, require_hackathon_organizer
from app.database import get_db
from app.schemas import RegistrationQuestionCreate, RegistrationQuestionUpdate
from app.services.registration_question_service import RegistrationQuestionService
from app.storage import StorageService

router = APIRouter(prefix="/api/hackathons", tags=["registration-questions"])


@router.post("/{hackathon_id}/registration-questions", status_code=201)
async def create_question(
    hackathon_id: uuid.UUID,
    body: RegistrationQuestionCreate,
    auth: dict = Depends(require_hackathon_organizer),
    db: AsyncSession = Depends(get_db),
):
    """Create a custom registration question. Organizer only."""
    service = RegistrationQuestionService(db)
    try:
        question = await service.create_question(
            hackathon_id=hackathon_id,
            question_text=body.question_text,
            question_type=body.question_type,
            options=body.options,
            is_required=body.is_required,
            sort_order=body.sort_order,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return {
        "id": str(question.id),
        "hackathon_id": str(question.hackathon_id),
        "question_text": question.question_text,
        "question_type": question.question_type.value,
        "options": question.options,
        "is_required": question.is_required,
        "sort_order": question.sort_order,
        "created_at": question.created_at.isoformat(),
    }


@router.get("/{hackathon_id}/registration-questions")
async def list_questions(
    hackathon_id: uuid.UUID,
    auth: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """List custom registration questions for a hackathon. Logged-in users only."""
    service = RegistrationQuestionService(db)
    questions = await service.get_questions_for_hackathon(hackathon_id)
    return {
        "questions": [
            {
                "id": str(q.id),
                "question_text": q.question_text,
                "question_type": q.question_type.value,
                "options": q.options,
                "is_required": q.is_required,
                "sort_order": q.sort_order,
            }
            for q in questions
        ]
    }


@router.put("/{hackathon_id}/registration-questions/{question_id}")
async def update_question(
    hackathon_id: uuid.UUID,
    question_id: uuid.UUID,
    body: RegistrationQuestionUpdate,
    auth: dict = Depends(require_hackathon_organizer),
    db: AsyncSession = Depends(get_db),
):
    """Update a custom registration question. Organizer only."""
    from sqlalchemy import select
    from app.models import RegistrationQuestion, QuestionType

    result = await db.execute(
        select(RegistrationQuestion).where(
            RegistrationQuestion.id == question_id,
            RegistrationQuestion.hackathon_id == hackathon_id,
        )
    )
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    if body.question_text is not None:
        question.question_text = body.question_text
    if body.question_type is not None:
        question.question_type = QuestionType(body.question_type)
    if body.options is not None:
        question.options = body.options
    if body.is_required is not None:
        question.is_required = body.is_required
    if body.sort_order is not None:
        question.sort_order = body.sort_order

    await db.commit()
    await db.refresh(question)

    return {
        "id": str(question.id),
        "question_text": question.question_text,
        "question_type": question.question_type.value,
        "options": question.options,
        "is_required": question.is_required,
        "sort_order": question.sort_order,
    }


@router.delete("/{hackathon_id}/registration-questions/{question_id}", status_code=204)
async def delete_question(
    hackathon_id: uuid.UUID,
    question_id: uuid.UUID,
    auth: dict = Depends(require_hackathon_organizer),
    db: AsyncSession = Depends(get_db),
):
    """Delete a custom registration question. Organizer only."""
    from sqlalchemy import select
    from app.models import RegistrationQuestion

    result = await db.execute(
        select(RegistrationQuestion).where(
            RegistrationQuestion.id == question_id,
            RegistrationQuestion.hackathon_id == hackathon_id,
        )
    )
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    await db.delete(question)
    await db.commit()
    return None


@router.post("/{hackathon_id}/upload")
async def upload_file(
    hackathon_id: uuid.UUID,
    file: UploadFile = File(...),
    auth: dict = Depends(require_clerk_user),
):
    """Upload a file for registration answers (MinIO/S3)."""
    storage = StorageService()
    try:
        result = await storage.upload_generic(
            file,
            folder=f"hackathons/{hackathon_id}/uploads",
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return result
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/routes/registration_questions.py
git commit -m "feat(routes): add registration question CRUD and file upload"
```

---

### Task 10: Extend StorageService with `upload_generic`

**Files:**
- Modify: `backend/app/storage.py`

- [ ] **Step 1: Add `upload_generic` method**

Add after the existing `upload` method in `backend/app/storage.py`:

```python
    # Generic file upload constants for registration attachments
    GENERIC_ALLOWED_TYPES = {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "image/png",
        "image/jpeg",
    }
    MAX_GENERIC_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

    async def upload_generic(
        self,
        file: UploadFile,
        folder: str = "assets",
        allowed_types: set[str] | None = None,
        max_size: int | None = None,
    ) -> dict:
        """Validate and upload a generic file (not just images), returning its public URL.

        Args:
            file: The uploaded file.
            folder: S3 folder prefix.
            allowed_types: Set of allowed MIME types. Defaults to GENERIC_ALLOWED_TYPES.
            max_size: Max file size in bytes. Defaults to MAX_GENERIC_FILE_SIZE.

        Raises:
            ValueError: If file exceeds size limit or has unsupported type.
        """
        allowed = allowed_types or self.GENERIC_ALLOWED_TYPES
        max_sz = max_size or self.MAX_GENERIC_FILE_SIZE

        contents = await file.read()
        if len(contents) > max_sz:
            raise ValueError(f"File exceeds {max_sz // (1024 * 1024)}MB limit ({len(contents)} bytes)")

        detected = file.content_type or "application/octet-stream"
        try:
            import magic
            detected = magic.from_buffer(contents, mime=True)
        except Exception:
            pass

        if detected not in allowed:
            raise ValueError(f"Unsupported file type: {detected}. Allowed: {allowed}")

        safe_name = self._sanitize_filename(file.filename or "asset")
        object_key = f"{folder}/{uuid.uuid4().hex}-{safe_name}"

        await self.ensure_bucket()
        s3 = self._get_client()
        await asyncio.to_thread(
            s3.put_object,
            Bucket=self._bucket,
            Key=object_key,
            Body=contents,
            ContentType=detected,
        )

        url = f"{self._public_base}/{object_key}"
        return {"key": object_key, "url": url}
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/storage.py
git commit -m "feat(storage): add upload_generic for non-image file uploads"
```

---

### Task 11: Integrate answers into registration flow

**Files:**
- Modify: `backend/app/routes/registrations.py:259-358`
- Modify: `backend/app/routes/registrations.py:396-420` (get registration)

- [ ] **Step 1: Modify `register_for_hackathon` to accept and validate answers**

In `backend/app/routes/registrations.py`, after line 324 (where `reg = Registration(...)` is created), add:

```python
    # Validate and attach custom question answers
    if body.answers:
        from app.services.registration_question_service import RegistrationQuestionService
        service = RegistrationQuestionService(db)
        try:
            answer_objects = await service.validate_answers(
                hackathon_id=hackathon_id,
                answers=[{"question_id": a.question_id, "value": a.value} for a in body.answers],
            )
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

        for ans in answer_objects:
            ans.registration_id = reg.id
            db.add(ans)
```

This must be added AFTER `db.add(reg)` but BEFORE `await db.commit()`. The exact placement is after the `Registration(...)` object is created and before the commit.

Also modify `_registration_to_response` to include answers. After the existing fields, add:

```python
        "answers": [
            {
                "question_id": str(a.question_id),
                "question_text": a.question.question_text if a.question else None,
                "question_type": a.question.question_type.value if a.question else None,
                "value": a.answer_value,
            }
            for a in (r.answers or [])
        ],
```

Note: Since `_registration_to_response` is called in many places, we need to ensure `r.answers` is loaded. Use `selectinload` in queries that call `_registration_to_response`.

- [ ] **Step 2: Add selectinload for answers in registration queries**

Find queries that load registrations and add `.options(selectinload(Registration.answers).selectinload(RegistrationAnswer.question))`.

For `get_registration`:
```python
    query = (
        select(Registration)
        .where(and_(Registration.id == registration_id, Registration.user_id == user.id))
        .options(selectinload(Registration.user))
        .options(selectinload(Registration.answers).selectinload(RegistrationAnswer.question))
    )
```

For `list_my_registrations`:
```python
    query = (
        select(Registration)
        .where(Registration.user_id == user.id)
        .options(selectinload(Registration.user))
        .options(selectinload(Registration.answers).selectinload(RegistrationAnswer.question))
        .order_by(Registration.registered_at.desc())
        .offset(offset)
        .limit(limit)
    )
```

For `register_for_hackathon` (return path), refresh with options:
```python
    from sqlalchemy.orm import selectinload
    await db.refresh(reg, attribute_names=["answers"])
```
Actually, after commit we can just do a fresh query for the response:
```python
    result = await db.execute(
        select(Registration)
        .where(Registration.id == reg.id)
        .options(selectinload(Registration.user))
        .options(selectinload(Registration.answers).selectinload(RegistrationAnswer.question))
    )
    reg = result.scalar_one()
```

- [ ] **Step 3: Create PUT endpoint for updating registration answers**

Add after `get_registration`:

```python
@router.put("/registrations/{registration_id}")
async def update_registration(
    registration_id: uuid.UUID,
    body: RegistrationCreate,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a pending registration and its answers."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(User).where(User.id == user_payload["sub"])
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    reg_result = await db.execute(
        select(Registration)
        .where(and_(Registration.id == registration_id, Registration.user_id == user.id))
        .options(selectinload(Registration.answers))
    )
    reg = reg_result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")

    if reg.status != RegistrationStatus.pending:
        raise HTTPException(status_code=409, detail="Can only update pending registrations")

    # Update standard fields
    for field in [
        "team_name", "team_members", "linkedin_url", "github_url", "resume_url",
        "experience_level", "t_shirt_size", "phone", "dietary_restrictions",
        "what_build", "why_participate", "age", "school", "major", "pronouns",
        "skills", "emergency_contact_name", "emergency_contact_phone",
    ]:
        val = getattr(body, field, None)
        if val is not None:
            setattr(reg, field, val)

    # Update answers
    if body.answers:
        from app.services.registration_question_service import RegistrationQuestionService
        service = RegistrationQuestionService(db)
        try:
            new_answers = await service.validate_answers(
                hackathon_id=reg.hackathon_id,
                answers=[{"question_id": a.question_id, "value": a.value} for a in body.answers],
            )
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

        # Remove old answers and add new ones
        for old in reg.answers:
            await db.delete(old)
        for ans in new_answers:
            ans.registration_id = reg.id
            db.add(ans)

    await db.commit()
    await db.refresh(reg)

    # Reload with relationships
    reg_result = await db.execute(
        select(Registration)
        .where(Registration.id == reg.id)
        .options(selectinload(Registration.user))
        .options(selectinload(Registration.answers).selectinload(RegistrationAnswer.question))
    )
    reg = reg_result.scalar_one()

    return _registration_to_response(reg, reg.user)
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/routes/registrations.py
git commit -m "feat(registrations): integrate custom question answers into create/update/get"
```

---

## Chunk 4: Registration Review Notes — Routes & Integration

### Task 12: Create review note routes

**Files:**
- Create: `backend/app/routes/registration_notes.py`

- [ ] **Step 1: Write the router**

```python
"""Routes for registration review notes (organizer-only)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import require_hackathon_organizer
from app.database import get_db
from app.schemas import RegistrationReviewNoteCreate, RegistrationReviewNoteUpdate
from app.services.registration_note_service import RegistrationNoteService

router = APIRouter(prefix="/api/hackathons", tags=["registration-notes"])


@router.post("/{hackathon_id}/registrations/{registration_id}/notes", status_code=201)
async def create_note(
    hackathon_id: uuid.UUID,
    registration_id: uuid.UUID,
    body: RegistrationReviewNoteCreate,
    auth: dict = Depends(require_hackathon_organizer),
    db: AsyncSession = Depends(get_db),
):
    """Add a review note to a registration. Organizer only."""
    from sqlalchemy import and_, select
    from app.models import Registration

    # Verify registration belongs to this hackathon
    reg_result = await db.execute(
        select(Registration).where(
            and_(Registration.id == registration_id, Registration.hackathon_id == hackathon_id)
        )
    )
    reg = reg_result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")

    service = RegistrationNoteService(db)
    note = await service.create_note(
        registration_id=registration_id,
        organizer_id=auth["user"].id,
        note_text=body.note_text,
        rating=body.rating,
    )

    return {
        "id": str(note.id),
        "registration_id": str(note.registration_id),
        "organizer_id": note.organizer_id,
        "organizer_name": auth["user"].name,
        "note_text": note.note_text,
        "rating": note.rating,
        "created_at": note.created_at.isoformat(),
    }


@router.get("/{hackathon_id}/registrations/{registration_id}/notes")
async def list_notes(
    hackathon_id: uuid.UUID,
    registration_id: uuid.UUID,
    auth: dict = Depends(require_hackathon_organizer),
    db: AsyncSession = Depends(get_db),
):
    """List review notes for a registration. Organizer only."""
    from sqlalchemy import and_, select
    from app.models import Registration, User

    reg_result = await db.execute(
        select(Registration).where(
            and_(Registration.id == registration_id, Registration.hackathon_id == hackathon_id)
        )
    )
    reg = reg_result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")

    service = RegistrationNoteService(db)
    notes = await service.list_notes_for_registration(registration_id)

    # Load organizers for names
    organizer_ids = [n.organizer_id for n in notes]
    users_result = await db.execute(
        select(User).where(User.id.in_(organizer_ids))
    )
    users = {u.id: u for u in users_result.scalars().all()}

    return {
        "notes": [
            {
                "id": str(n.id),
                "organizer_id": n.organizer_id,
                "organizer_name": users.get(n.organizer_id, {}).name if users.get(n.organizer_id) else None,
                "organizer_email": users.get(n.organizer_id, {}).email if users.get(n.organizer_id) else None,
                "note_text": n.note_text,
                "rating": n.rating,
                "created_at": n.created_at.isoformat(),
                "updated_at": n.updated_at.isoformat(),
            }
            for n in notes
        ]
    }


@router.put("/{hackathon_id}/registrations/{registration_id}/notes/{note_id}")
async def update_note(
    hackathon_id: uuid.UUID,
    registration_id: uuid.UUID,
    note_id: uuid.UUID,
    body: RegistrationReviewNoteUpdate,
    auth: dict = Depends(require_hackathon_organizer),
    db: AsyncSession = Depends(get_db),
):
    """Update a review note. Only the original author can edit."""
    from sqlalchemy import and_, select
    from app.models import Registration

    reg_result = await db.execute(
        select(Registration).where(
            and_(Registration.id == registration_id, Registration.hackathon_id == hackathon_id)
        )
    )
    reg = reg_result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")

    service = RegistrationNoteService(db)
    note = await service.get_note(note_id)
    if not note or note.registration_id != registration_id:
        raise HTTPException(status_code=404, detail="Note not found")

    if note.organizer_id != auth["user"].id:
        raise HTTPException(status_code=403, detail="Only the note author can edit this note")

    note = await service.update_note(
        note,
        note_text=body.note_text,
        rating=body.rating,
    )

    return {
        "id": str(note.id),
        "note_text": note.note_text,
        "rating": note.rating,
        "updated_at": note.updated_at.isoformat(),
    }


@router.delete("/{hackathon_id}/registrations/{registration_id}/notes/{note_id}", status_code=204)
async def delete_note(
    hackathon_id: uuid.UUID,
    registration_id: uuid.UUID,
    note_id: uuid.UUID,
    auth: dict = Depends(require_hackathon_organizer),
    db: AsyncSession = Depends(get_db),
):
    """Delete a review note. Only the original author can delete."""
    from sqlalchemy import and_, select
    from app.models import Registration

    reg_result = await db.execute(
        select(Registration).where(
            and_(Registration.id == registration_id, Registration.hackathon_id == hackathon_id)
        )
    )
    reg = reg_result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")

    service = RegistrationNoteService(db)
    note = await service.get_note(note_id)
    if not note or note.registration_id != registration_id:
        raise HTTPException(status_code=404, detail="Note not found")

    if note.organizer_id != auth["user"].id:
        raise HTTPException(status_code=403, detail="Only the note author can delete this note")

    await service.delete_note(note)
    return None
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/routes/registration_notes.py
git commit -m "feat(routes): add registration review note CRUD"
```

---

### Task 13: Integrate review note aggregations into organizer registration list

**Files:**
- Modify: `backend/app/routes/registrations_organizer.py:42-93`

- [ ] **Step 1: Add aggregations to list endpoint**

In `list_hackathon_registrations` in `registrations_organizer.py`, modify the response builder to include review note aggregates:

```python
    # Before building the response, get aggregates
    from app.services.registration_note_service import RegistrationNoteService
    note_service = RegistrationNoteService(db)

    registration_ids = [r.id for r in registrations]
    aggregates = {}
    for rid in registration_ids:
        aggregates[rid] = await note_service.get_aggregates_for_registration(rid)

    return {
        "registrations": [
            {
                "id": str(r.id),
                "hackathon_id": str(r.hackathon_id),
                "user_id": str(r.user_id),
                "status": r.status.value,
                "team_name": r.team_name,
                "team_members": r.team_members,
                "registered_at": r.registered_at.isoformat(),
                "accepted_at": r.accepted_at.isoformat() if r.accepted_at else None,
                "checked_in_at": r.checked_in_at.isoformat() if r.checked_in_at else None,
                "user_name": users[str(r.user_id)].name if str(r.user_id) in users else None,
                "user_email": users[str(r.user_id)].email if str(r.user_id) in users else None,
                "user_role": users[str(r.user_id)].role.value if str(r.user_id) in users else None,
                "review_notes_count": aggregates.get(r.id, {}).get("review_notes_count", 0),
                "average_rating": aggregates.get(r.id, {}).get("average_rating"),
            }
            for r in registrations
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/routes/registrations_organizer.py
git commit -m "feat(registrations): add review note aggregates to organizer list endpoint"
```

---

### Task 14: Register new routers in main.py

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Import and register routers**

Add imports:
```python
from app.routes.registration_questions import router as registration_questions_router
from app.routes.registration_notes import router as registration_notes_router
```

Add registrations:
```python
app.include_router(registration_questions_router)
app.include_router(registration_notes_router)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/main.py
git commit -m "feat(main): register registration question and note routers"
```

---

## Chunk 5: Tests

### Task 15: Write tests for registration questions

**Files:**
- Create: `backend/tests/routes/test_registration_questions.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for registration question routes."""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Hackathon, User, UserRole
from app.routes.registration_questions import router as questions_router

app = FastAPI()
app.include_router(questions_router)


async def _override_require_clerk_user():
    return {"sub": "test-user-id", "email": "test@example.com"}


async def _override_require_hackathon_organizer(hackathon_id):
    return {
        "user": type(
            "FakeUser",
            (),
            {
                "role": UserRole.organizer,
                "id": "test-organizer-id",
                "email": "organizer@test.com",
                "name": "Test Organizer",
            },
        )(),
        "sub": "test-organizer-id",
        "email": "organizer@test.com",
        "payload": {},
    }


@pytest_asyncio.fixture
async def question_client(engine):
    async_session_maker = __import__("sqlalchemy.ext.asyncio", fromlist=["async_sessionmaker"]).async_sessionmaker

    async def override_get_db():
        async with async_session_maker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
            yield session

    from app.clerk_auth import require_clerk_user, require_hackathon_organizer

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_clerk_user] = _override_require_clerk_user
    app.dependency_overrides[require_hackathon_organizer] = _override_require_hackathon_organizer
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def hackathon_with_questions(db_session: AsyncSession):
    from datetime import UTC, datetime
    from sqlalchemy import delete
    from app.models import RegistrationQuestion

    await db_session.execute(delete(RegistrationQuestion))
    await db_session.execute(delete(Hackathon))
    await db_session.execute(delete(User))
    await db_session.commit()

    user = User(id="test-organizer-id", email="organizer@test.com", name="Test Organizer", role=UserRole.organizer)
    db_session.add(user)

    hackathon = Hackathon(
        name="Test Hack",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id="test-organizer-id",
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)

    return hackathon


@pytest.mark.anyio
async def test_create_question(question_client, hackathon_with_questions):
    hackathon = hackathon_with_questions
    resp = await question_client.post(
        f"/api/hackathons/{hackathon.id}/registration-questions",
        json={
            "question_text": "What is your favorite programming language?",
            "question_type": "select",
            "options": ["Python", "JavaScript", "Rust", "Go"],
            "is_required": True,
            "sort_order": 1,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["question_text"] == "What is your favorite programming language?"
    assert data["question_type"] == "select"
    assert data["options"] == ["Python", "JavaScript", "Rust", "Go"]


@pytest.mark.anyio
async def test_list_questions(question_client, hackathon_with_questions):
    hackathon = hackathon_with_questions
    # Create a question first
    await question_client.post(
        f"/api/hackathons/{hackathon.id}/registration-questions",
        json={
            "question_text": "Tell us about yourself",
            "question_type": "textarea",
            "is_required": False,
            "sort_order": 2,
        },
    )

    resp = await question_client.get(f"/api/hackathons/{hackathon.id}/registration-questions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["questions"]) == 1
    assert data["questions"][0]["question_type"] == "textarea"


@pytest.mark.anyio
async def test_delete_question(question_client, hackathon_with_questions):
    hackathon = hackathon_with_questions
    create_resp = await question_client.post(
        f"/api/hackathons/{hackathon.id}/registration-questions",
        json={
            "question_text": "Delete me",
            "question_type": "text",
            "is_required": True,
            "sort_order": 3,
        },
    )
    qid = create_resp.json()["id"]

    resp = await question_client.delete(f"/api/hackathons/{hackathon.id}/registration-questions/{qid}")
    assert resp.status_code == 204

    list_resp = await question_client.get(f"/api/hackathons/{hackathon.id}/registration-questions")
    assert len(list_resp.json()["questions"]) == 0
```

- [ ] **Step 2: Run tests**

```bash
cd backend
pytest tests/routes/test_registration_questions.py -v
```

Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/routes/test_registration_questions.py
git commit -m "test(registration-questions): add CRUD route tests"
```

---

### Task 16: Write tests for review notes

**Files:**
- Create: `backend/tests/routes/test_registration_notes.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for registration review note routes."""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Hackathon, Registration, RegistrationStatus, User, UserRole
from app.routes.registration_notes import router as notes_router

app = FastAPI()
app.include_router(notes_router)


async def _override_require_hackathon_organizer(hackathon_id):
    return {
        "user": type(
            "FakeUser",
            (),
            {
                "role": UserRole.organizer,
                "id": "test-organizer-id",
                "email": "organizer@test.com",
                "name": "Test Organizer",
            },
        )(),
        "sub": "test-organizer-id",
        "email": "organizer@test.com",
        "payload": {},
    }


@pytest_asyncio.fixture
async def notes_client(engine):
    async_session_maker = __import__("sqlalchemy.ext.asyncio", fromlist=["async_sessionmaker"]).async_sessionmaker

    async def override_get_db():
        async with async_session_maker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
            yield session

    from app.clerk_auth import require_hackathon_organizer

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_hackathon_organizer] = _override_require_hackathon_organizer
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def hackathon_with_registration(db_session: AsyncSession):
    from datetime import UTC, datetime
    from sqlalchemy import delete

    await db_session.execute(delete(Registration))
    await db_session.execute(delete(Hackathon))
    await db_session.execute(delete(User))
    await db_session.commit()

    org = User(id="test-organizer-id", email="organizer@test.com", name="Test Organizer", role=UserRole.organizer)
    participant = User(id="test-user-id", email="test@example.com", name="Test User", role=UserRole.participant)
    db_session.add(org)
    db_session.add(participant)

    hackathon = Hackathon(
        name="Test Hack",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id="test-organizer-id",
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)

    reg = Registration(
        hackathon_id=hackathon.id,
        user_id="test-user-id",
        status=RegistrationStatus.pending,
    )
    db_session.add(reg)
    await db_session.commit()
    await db_session.refresh(reg)

    return hackathon, reg


@pytest.mark.anyio
async def test_create_note(notes_client, hackathon_with_registration):
    hackathon, reg = hackathon_with_registration
    resp = await notes_client.post(
        f"/api/hackathons/{hackathon.id}/registrations/{reg.id}/notes",
        json={"note_text": "Strong applicant", "rating": 5},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["note_text"] == "Strong applicant"
    assert data["rating"] == 5
    assert data["organizer_id"] == "test-organizer-id"


@pytest.mark.anyio
async def test_list_notes(notes_client, hackathon_with_registration):
    hackathon, reg = hackathon_with_registration
    await notes_client.post(
        f"/api/hackathons/{hackathon.id}/registrations/{reg.id}/notes",
        json={"note_text": "Note 1", "rating": 4},
    )
    await notes_client.post(
        f"/api/hackathons/{hackathon.id}/registrations/{reg.id}/notes",
        json={"note_text": "Note 2", "rating": 3},
    )

    resp = await notes_client.get(f"/api/hackathons/{hackathon.id}/registrations/{reg.id}/notes")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["notes"]) == 2


@pytest.mark.anyio
async def test_delete_note(notes_client, hackathon_with_registration):
    hackathon, reg = hackathon_with_registration
    create_resp = await notes_client.post(
        f"/api/hackathons/{hackathon.id}/registrations/{reg.id}/notes",
        json={"note_text": "To delete", "rating": 2},
    )
    note_id = create_resp.json()["id"]

    resp = await notes_client.delete(
        f"/api/hackathons/{hackathon.id}/registrations/{reg.id}/notes/{note_id}"
    )
    assert resp.status_code == 204

    list_resp = await notes_client.get(f"/api/hackathons/{hackathon.id}/registrations/{reg.id}/notes")
    assert len(list_resp.json()["notes"]) == 0
```

- [ ] **Step 2: Run tests**

```bash
cd backend
pytest tests/routes/test_registration_notes.py -v
```

Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/routes/test_registration_notes.py
git commit -m "test(registration-notes): add CRUD route tests"
```

---

### Task 17: Final integration test

**Files:**
- Test via curl / pytest

- [ ] **Step 1: Run all backend tests**

```bash
cd backend
pytest tests/routes/ -v --tb=short
```

Expected: All existing tests still pass. New tests pass.

- [ ] **Step 2: Commit if all pass**

```bash
git commit -m "test: all tests passing for Group 1 features"
```

---

## Plan Review Loop

After completing each chunk, dispatch the plan-document-reviewer subagent with:
- The chunk content
- Path to spec: `docs/superpowers/specs/2026-05-11-openhack-group1-design.md`

Fix any issues found, re-dispatch reviewer, repeat until approved.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-11-openhack-group1.md`. Ready to execute?

Execution path: **subagent-driven-development** (RECOMMENDED) — fresh subagent per task + two-stage review.
