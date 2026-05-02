from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from uuid import UUID


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
    github_url: Optional[str] = None
    project_title: Optional[str] = None
    status: str
    risk_score: Optional[int] = None
    verdict: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    check_results: list = []

    model_config = {"from_attributes": True}


# --- Hackathon Schemas ---

class HackathonCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    start_date: datetime
    end_date: datetime
    description: Optional[str] = None
    application_deadline: Optional[datetime] = None
    max_participants: Optional[int] = Field(None, ge=1)
    waitlist_enabled: bool = False
    venue_address: Optional[str] = None
    parking_info: Optional[str] = None
    wifi_ssid: Optional[str] = None
    wifi_password: Optional[str] = None
    discord_invite_url: Optional[str] = None
    devpost_url: Optional[str] = None
    schedule: Optional[list[dict]] = None  # [{"time": "", "title": "", "description": ""}]


# --- Registration Schemas ---

class RegistrationCreate(BaseModel):
    team_name: Optional[str] = Field(None, max_length=200)
    team_members: Optional[list[str]] = None
    linkedin_url: Optional[str] = Field(None, max_length=500)
    github_url: Optional[str] = Field(None, max_length=500)
    resume_url: Optional[str] = Field(None, max_length=500)
    experience_level: Optional[str] = Field(None, max_length=50)
    t_shirt_size: Optional[str] = Field(None, max_length=10)
    phone: Optional[str] = Field(None, max_length=20)
    dietary_restrictions: Optional[str] = Field(None, max_length=500)
    what_build: Optional[str] = None
    why_participate: Optional[str] = None
    age: Optional[int] = None
    school: Optional[str] = Field(None, max_length=200)
    major: Optional[str] = Field(None, max_length=200)
    pronouns: Optional[str] = Field(None, max_length=50)
    skills: Optional[list[str]] = None
    emergency_contact_name: Optional[str] = Field(None, max_length=200)
    emergency_contact_phone: Optional[str] = Field(None, max_length=30)


class RegistrationResponse(BaseModel):
    id: UUID
    hackathon_id: UUID
    user_id: UUID
    status: str
    team_name: Optional[str] = None
    team_members: Optional[list[str]] = None
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
    skills: Optional[list[str]] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    qr_token: Optional[str] = None  # included only for accepted own registrations
    registered_at: datetime
    accepted_at: Optional[datetime] = None
    checked_in_at: Optional[datetime] = None
    # Joined fields for organizer view
    user_name: Optional[str] = None
    user_email: Optional[str] = None

    model_config = {"from_attributes": True}


class RegistrationListResponse(BaseModel):
    registrations: list[RegistrationResponse]
    total: int
    limit: int
    offset: int


# --- Judging Schemas ---

class CriterionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
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
    reason: Optional[str] = None


class ConflictOfInterestResponse(BaseModel):
    id: UUID
    judge_id: UUID
    hackathon_id: UUID
    submission_id: UUID
    reason: Optional[str] = None
    declared_at: datetime

    model_config = {"from_attributes": True}
