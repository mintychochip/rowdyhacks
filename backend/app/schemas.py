from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

# --- Auth Schemas ---


class UserRegister(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=200)
    password: str = Field(..., min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: UUID
    email: str
    name: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Check / Submission Schemas ---


class SubmitRequest(BaseModel):
    url: str = Field(..., description="Devpost or GitHub URL to check")
    hackathon_id: UUID | None = Field(default=None, description="Optional hackathon to associate submission with")


class SubmissionResponse(BaseModel):
    id: UUID
    devpost_url: str
    github_url: str | None = None
    project_title: str | None = None
    status: str
    risk_score: int | None = None
    verdict: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    check_results: list = []

    model_config = {"from_attributes": True}


# --- Hackathon Schemas ---


class HackathonCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    start_date: datetime
    end_date: datetime
    description: str | None = None
    application_deadline: datetime | None = None
    max_participants: int | None = Field(None, ge=1)
    waitlist_enabled: bool = False
    venue_address: str | None = None
    parking_info: str | None = None
    wifi_ssid: str | None = None
    wifi_password: str | None = None
    discord_invite_url: str | None = None
    devpost_url: str | None = None
    schedule: list[dict] | None = None  # [{"time": "", "title": "", "description": ""}]


# --- Registration Schemas ---


class RegistrationCreate(BaseModel):
    team_name: str | None = Field(None, max_length=200)
    team_members: list[str] | None = None
    linkedin_url: str | None = Field(None, max_length=500)
    github_url: str | None = Field(None, max_length=500)
    resume_url: str | None = Field(None, max_length=500)
    experience_level: str | None = Field(None, max_length=50)
    t_shirt_size: str | None = Field(None, max_length=10)
    phone: str | None = Field(None, max_length=20)
    dietary_restrictions: str | None = Field(None, max_length=500)
    what_build: str | None = None
    why_participate: str | None = None
    age: int | None = None
    school: str | None = Field(None, max_length=200)
    major: str | None = Field(None, max_length=200)
    pronouns: str | None = Field(None, max_length=50)
    skills: list[str] | None = None
    emergency_contact_name: str | None = Field(None, max_length=200)
    emergency_contact_phone: str | None = Field(None, max_length=30)


class RegistrationResponse(BaseModel):
    id: UUID
    hackathon_id: UUID
    user_id: UUID
    status: str
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
    qr_token: str | None = None  # included only for accepted own registrations
    registered_at: datetime
    accepted_at: datetime | None = None
    checked_in_at: datetime | None = None
    # Joined fields for organizer view
    user_name: str | None = None
    user_email: str | None = None

    model_config = {"from_attributes": True}


class RegistrationListResponse(BaseModel):
    registrations: list[RegistrationResponse]
    total: int
    limit: int
    offset: int


# --- Judging Schemas ---


class CriterionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=500)
    max_score: int = Field(default=10, ge=1, le=100)
    weight: int = Field(..., ge=0, le=100)  # percentage integer
    sort_order: int = 0


class JudgingSessionCreate(BaseModel):
    start_time: datetime
    end_time: datetime
    per_project_seconds: int = Field(default=300, ge=1, le=3600)
    leaderboard_public: bool = False
    criteria: list[CriterionCreate] = Field(..., min_length=1, max_length=10)


class SubmitScoreRequest(BaseModel):
    scores: list[dict]  # [{"criterion_id": "...", "score": 8}, ...]


class JudgingResultsResponse(BaseModel):
    hackathon_id: UUID
    rankings: list[dict]
    judge_stats: list[dict]


# --- Announcement Schemas ---


class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    priority: str = Field(default="normal", pattern="^(low|normal|high|urgent)$")


class AnnouncementResponse(BaseModel):
    id: UUID
    hackathon_id: UUID
    title: str
    content: str
    priority: str
    sent_by: UUID
    sent_at: datetime

    model_config = {"from_attributes": True}


# --- Conflict of Interest Schemas ---


class ConflictOfInterestCreate(BaseModel):
    submission_id: UUID
    reason: str | None = None


class ConflictOfInterestResponse(BaseModel):
    id: UUID
    judge_id: UUID
    hackathon_id: UUID
    submission_id: UUID
    reason: str | None = None
    declared_at: datetime

    model_config = {"from_attributes": True}
