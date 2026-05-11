"""Stub schema exports to satisfy imports until full schemas are restored."""

from typing import Any, List, Optional

from pydantic import BaseModel


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


class JudgingSessionCreate(BaseModel):
    """Pydantic schema for creating a new judging session.

    Behavior:
    1. Accepts a list of scoring criteria.
    2. Passed to the judging session factory to initialize evaluation state.

    Raises: ValidationError on type mismatches.
    Side Effects: None.
    Dependencies: pydantic.BaseModel.
    Consumers: POST /api/judging/sessions route, admin judging panel.
    """
    criteria: List[Any] = []


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
    scores: List[Any] = []


class RegistrationCreate(BaseModel):
    """Pydantic schema for creating a new hackathon registration.

    Behavior:
    1. Stub schema with no fields until full registration flow is restored.
    2. Reserved for future fields: team_name, dietary_restrictions, etc.

    Raises: ValidationError on unexpected extra fields if strict mode is enabled.
    Side Effects: None.
    Dependencies: pydantic.BaseModel.
    Consumers: POST /api/registrations route, signup wizard.
    """
    pass


class AnnouncementCreate(BaseModel):
    """Pydantic schema for creating a new announcement.

    Behavior:
    1. Stub schema with no fields until full announcement flow is restored.
    2. Reserved for future fields: title, body, priority, target_audience.

    Raises: ValidationError on unexpected extra fields if strict mode is enabled.
    Side Effects: None.
    Dependencies: pydantic.BaseModel.
    Consumers: POST /api/announcements route, organizer broadcast panel.
    """
    pass


class AnnouncementResponse(BaseModel):
    """Pydantic schema for a serialized announcement.

    Behavior:
    1. Stub schema with no fields until full announcement flow is restored.
    2. Reserved for future fields: id, title, body, created_at, sender.

    Raises: ValidationError on unexpected extra fields if strict mode is enabled.
    Side Effects: None.
    Dependencies: pydantic.BaseModel.
    Consumers: GET /api/announcements route, dashboard feed, public timeline.
    """
    pass


class ConflictOfInterestCreate(BaseModel):
    """Pydantic schema for creating a new conflict-of-interest declaration.

    Behavior:
    1. Stub schema with no fields until full COI flow is restored.
    2. Reserved for future fields: judge_id, team_id, reason.

    Raises: ValidationError on unexpected extra fields if strict mode is enabled.
    Side Effects: None.
    Dependencies: pydantic.BaseModel.
    Consumers: POST /api/coi route, judge declaration form.
    """
    pass


class ConflictOfInterestResponse(BaseModel):
    """Pydantic schema for a serialized conflict-of-interest record.

    Behavior:
    1. Stub schema with no fields until full COI flow is restored.
    2. Reserved for future fields: id, judge_id, team_id, status, created_at.

    Raises: ValidationError on unexpected extra fields if strict mode is enabled.
    Side Effects: None.
    Dependencies: pydantic.BaseModel.
    Consumers: GET /api/coi route, admin review panel.
    """
    pass


class HackathonCreate(BaseModel):
    """Pydantic schema for creating a new hackathon event.

    Behavior:
    1. Stub schema with no fields until full hackathon creation flow is restored.
    2. Reserved for future fields: name, start_date, end_date, max_participants, url_slug.

    Raises: ValidationError on unexpected extra fields if strict mode is enabled.
    Side Effects: None.
    Dependencies: pydantic.BaseModel.
    Consumers: POST /api/hackathons route, organizer event wizard.
    """
    pass
