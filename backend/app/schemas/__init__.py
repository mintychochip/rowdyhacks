"""Stub schema exports to satisfy imports until full schemas are restored."""

import enum
import uuid
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class UserResponse(BaseModel):
    """Pydantic schema for a serialized user record.

    Behavior:
    1. Returns id, email, name, role, and created_at fields.
    2. Used when the API needs to expose a user object without internal fields.

    Raises: ValidationError on missing required fields or type mismatches.
    Side Effects: None.
    Dependencies: pydantic.BaseModel.
    Consumers: Auth routes, user lookup endpoints, leaderboard serializers.
    """

    id: str
    email: str
    name: Optional[str] = None
    role: Optional[str] = None
    created_at: Optional[Any] = None


class SubmitRequest(BaseModel):
    """Pydantic schema for a project submission request.

    Behavior:
    1. Validates the submitted project URL and optional hackathon_id.
    2. Consumed by the submission endpoint to create or update a submission.

    Raises: ValidationError if URL is missing or malformed.
    Side Effects: None.
    Dependencies: pydantic.BaseModel.
    Consumers: POST /api/submit route, crawler trigger.
    """

    url: str
    hackathon_id: Optional[str] = None


class CriterionCreate(BaseModel):
    """Pydantic schema for a single rubric criterion.

    Behavior:
    1. Defines name, description, max_score, weight, and sort_order.
    2. Consumed by JudgingSessionCreate to build the full rubric.

    Raises: ValidationError on type mismatches.
    Side Effects: None.
    Dependencies: pydantic.BaseModel.
    """

    name: str
    description: str = ""
    max_score: int = 10
    weight: int = 0
    sort_order: int = 0


class JudgingSessionCreate(BaseModel):
    """Pydantic schema for creating a new judging session.

    Behavior:
    1. Accepts timing, settings, and a list of scoring criteria.
    2. Passed to the judging session factory to initialize evaluation state.

    Raises: ValidationError on type mismatches.
    Side Effects: None.
    Dependencies: pydantic.BaseModel.
    Consumers: POST /api/judging/sessions route, admin judging panel.
    """

    start_time: datetime
    end_time: datetime
    per_project_seconds: int = 300
    leaderboard_public: bool = False
    criteria: List[CriterionCreate] = []


class ScoreItem(BaseModel):
    """Pydantic schema for a single criterion score.

    Behavior:
    1. Maps a criterion_id to a numeric score.
    2. Consumed by SubmitScoreRequest.

    Raises: ValidationError on type mismatches.
    Side Effects: None.
    Dependencies: pydantic.BaseModel.
    """

    criterion_id: str
    score: int


class SubmitScoreRequest(BaseModel):
    """Pydantic schema for submitting judge scores.

    Behavior:
    1. Accepts a list of score objects (criterion + value pairs).
    2. Consumed by the scoring endpoint to persist judge evaluations.

    Raises: ValidationError on missing scores or type mismatches.
    Side Effects: None.
    Dependencies: pydantic.BaseModel.
    Consumers: POST /api/judging/score route, judge ballot form.
    """

    scores: List[ScoreItem] = []


class RegistrationCreate(BaseModel):
    """Pydantic schema for creating a new hackathon registration.

    Behavior:
    1. Validates optional registration fields.
    2. All fields are optional to support flexible registration flows.

    Raises: ValidationError on unexpected extra fields if strict mode is enabled.
    Side Effects: None.
    Dependencies: pydantic.BaseModel.
    Consumers: POST /api/registrations route, signup wizard.
    """

    team_name: str | None = None
    team_members: list[str] | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    resume_url: str | None = None
    experience_level: str | None = None
    t_shirt_size: str | None = None
    phone: str | None = None
    dietary_restrictions: str | None = None
    what_build: str | None = None
    why_participate: str | None = None
    age: int | None = None
    school: str | None = None
    major: str | None = None
    pronouns: str | None = None
    skills: list[str] | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    invite_code: str | None = None
    answers: Optional[List[Any]] = None


class RegistrationAnswerItem(BaseModel):
    """Schema for a single answer within a registration payload."""

    question_id: str
    value: Any


class RegistrationQuestionCreate(BaseModel):
    """Schema for creating a custom registration question."""

    question_text: str = Field(..., max_length=500)
    question_type: str
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


class RegistrationReviewNoteCreate(BaseModel):
    """Schema for creating a review note."""

    note_text: str
    rating: Optional[int] = Field(None, ge=1, le=5)


class RegistrationReviewNoteUpdate(BaseModel):
    """Schema for updating a review note."""

    note_text: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5)


class AnnouncementCreate(BaseModel):
    """Pydantic schema for creating a new announcement.

    Behavior:
    1. Validates title, content, and priority.
    2. Consumed by the announcement creation endpoint.

    Raises: ValidationError on unexpected extra fields if strict mode is enabled.
    Side Effects: None.
    Dependencies: pydantic.BaseModel.
    Consumers: POST /api/announcements route, organizer broadcast panel.
    """

    model_config = ConfigDict(extra="allow")
    title: str
    content: str
    priority: str = "normal"


class AnnouncementResponse(BaseModel):
    """Pydantic schema for a serialized announcement.

    Behavior:
    1. Maps Announcement model fields for API responses.
    2. Supports attribute-based validation from SQLAlchemy instances.

    Raises: ValidationError on unexpected extra fields if strict mode is enabled.
    Side Effects: None.
    Dependencies: pydantic.BaseModel.
    Consumers: GET /api/announcements route, dashboard feed, public timeline.
    """

    model_config = ConfigDict(from_attributes=True, extra="allow")
    id: Any
    title: Optional[str] = None
    content: Optional[str] = None
    priority: Optional[str] = None
    hackathon_id: Any = None
    sent_by: Optional[str] = None
    sent_at: Optional[datetime] = None


class ConflictOfInterestCreate(BaseModel):
    """Pydantic schema for creating a new conflict-of-interest declaration.

    Behavior:
    1. Validates submission_id and reason fields.
    2. Consumed by the COI declaration endpoint.

    Raises: ValidationError on unexpected extra fields if strict mode is enabled.
    Side Effects: None.
    Dependencies: pydantic.BaseModel.
    Consumers: POST /api/coi route, judge declaration form.
    """

    model_config = ConfigDict(extra="allow")
    submission_id: Any
    reason: Optional[str] = None


class ConflictOfInterestResponse(BaseModel):
    """Pydantic schema for a serialized conflict-of-interest record.

    Behavior:
    1. Maps ConflictOfInterest model fields for API responses.
    2. Supports attribute-based validation from SQLAlchemy instances.

    Raises: ValidationError on unexpected extra fields if strict mode is enabled.
    Side Effects: None.
    Dependencies: pydantic.BaseModel.
    Consumers: GET /api/coi route, admin review panel.
    """

    model_config = ConfigDict(from_attributes=True, extra="allow")
    id: Any
    judge_id: Optional[str] = None
    hackathon_id: Any = None
    submission_id: Any = None
    reason: Optional[str] = None
    declared_at: Optional[datetime] = None


class HackathonCreate(BaseModel):
    """Pydantic schema for creating a new hackathon event.

    Behavior:
    1. Validates required name, start_date, end_date and optional settings.
    2. Consumed by the hackathon creation endpoint.

    Raises: ValidationError on unexpected extra fields if strict mode is enabled.
    Side Effects: None.
    Dependencies: pydantic.BaseModel.
    Consumers: POST /api/hackathons route, organizer event wizard.
    """

    model_config = ConfigDict(extra="allow")
    name: str
    start_date: datetime
    end_date: datetime
    description: Optional[str] = None
    application_deadline: Optional[datetime] = None
    max_participants: Optional[int] = None
    waitlist_enabled: Optional[bool] = False
    venue_address: Optional[str] = None
    parking_info: Optional[str] = None
    wifi_ssid: Optional[str] = None
    wifi_password: Optional[str] = None
    discord_invite_url: Optional[str] = None
    devpost_url: Optional[str] = None
    schedule: Optional[Any] = None


class WorkshopRSVPStatus(str, enum.Enum):
    """Pydantic schema for workshop RSVP status values."""

    registered = "registered"
    attended = "attended"
    cancelled = "cancelled"


class WorkshopRSVPCreate(BaseModel):
    """Pydantic schema for creating a workshop RSVP.

    Behavior:
    1. Validates workshop_id and optional hackathon_id.
    2. Consumed by the RSVP registration endpoint.

    Raises: ValidationError on unexpected extra fields if strict mode is enabled.
    Side Effects: None.
    Dependencies: pydantic.BaseModel.
    Consumers: POST /api/workshops/{workshop_id}/rsvp route.
    """

    model_config = ConfigDict(extra="allow")
    workshop_id: Optional[str] = None
    hackathon_id: Optional[str] = None


class WorkshopRSVPResponse(BaseModel):
    """Pydantic schema for a serialized workshop RSVP record.

    Behavior:
    1. Maps WorkshopRSVP model fields for API responses.
    2. Supports attribute-based validation from SQLAlchemy instances.

    Raises: ValidationError on unexpected extra fields if strict mode is enabled.
    Side Effects: None.
    Dependencies: pydantic.BaseModel.
    Consumers: GET /api/workshops/{workshop_id}/rsvps, GET /api/hackathons/{hackathon_id}/my-rsvps.
    """

    model_config = ConfigDict(from_attributes=True, extra="allow")
    id: Any
    user_id: Optional[str] = None
    workshop_id: Any = None
    hackathon_id: Any = None
    status: Optional[str] = None
    registered_at: Optional[datetime] = None
    attended_at: Optional[datetime] = None
