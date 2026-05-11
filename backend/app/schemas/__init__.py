"""Pydantic schemas — minimal stub for transition to self-hosted auth."""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str


class SubmitRequest(BaseModel):
    devpost_url: str
    github_url: Optional[str] = None


class HackathonCreate(BaseModel):
    name: str
    start_date: datetime
    end_date: datetime
    description: Optional[str] = None
    max_participants: Optional[int] = None


class AnnouncementCreate(BaseModel):
    title: str
    content: str
    priority: Optional[str] = "normal"


class AnnouncementResponse(BaseModel):
    id: str
    title: str
    content: str
    priority: str
    sent_at: datetime


class ConflictOfInterestCreate(BaseModel):
    submission_id: str
    reason: Optional[str] = None


class ConflictOfInterestResponse(BaseModel):
    id: str
    judge_id: str
    hackathon_id: str
    submission_id: str
    reason: Optional[str] = None
    declared_at: datetime


class JudgingSessionCreate(BaseModel):
    hackathon_id: str
    start_time: datetime
    end_time: datetime
    per_project_seconds: Optional[int] = 300


class SubmitScoreRequest(BaseModel):
    assignment_id: str
    criterion_id: str
    score: int


class RegistrationCreate(BaseModel):
    hackathon_id: str
    team_name: Optional[str] = None
    team_members: Optional[List[Dict[str, Any]]] = None
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
    special_needs: Optional[str] = None
    school_company: Optional[str] = None
    graduation_year: Optional[int] = None
