"""Mentor matching routes."""

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import MentorProfile, MentorRequest
from app.routes.deps import get_current_user

router = APIRouter(prefix="/api/hackathons", tags=["mentors"])


class MentorProfileCreate(BaseModel):
    name: str
    expertise: list[str] | None = None
    bio: str | None = None
    max_sessions: int = 5


class MentorRequestCreate(BaseModel):
    topic: str
    description: str | None = None


def _mentor_to_dict(m: MentorProfile) -> dict:
    return {
        "id": str(m.id),
        "hackathon_id": str(m.hackathon_id),
        "user_id": str(m.user_id),
        "name": m.name,
        "expertise": m.expertise or [],
        "bio": m.bio,
        "max_sessions": m.max_sessions,
        "is_available": m.is_available,
        "created_at": m.created_at.isoformat(),
    }


@router.get("/{hackathon_id}/mentors")
async def list_mentors(
    hackathon_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """List available mentors for a hackathon."""
    result = await db.execute(
        select(MentorProfile)
        .where(MentorProfile.hackathon_id == hackathon_id, MentorProfile.is_available.is_(True))
        .options(selectinload(MentorProfile.user))
        .order_by(MentorProfile.created_at.desc())
    )
    mentors = result.scalars().all()
    return {"mentors": [_mentor_to_dict(m) for m in mentors]}


@router.post("/{hackathon_id}/mentors", status_code=201)
async def register_mentor(
    hackathon_id: uuid.UUID,
    body: MentorProfileCreate,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Register as a mentor for a hackathon."""
    user = await get_current_user(db, authorization)
    existing = await db.execute(
        select(MentorProfile).where(
            MentorProfile.hackathon_id == hackathon_id,
            MentorProfile.user_id == user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="You are already registered as a mentor")

    mentor = MentorProfile(
        hackathon_id=hackathon_id,
        user_id=user.id,
        name=body.name,
        expertise=body.expertise,
        bio=body.bio,
        max_sessions=body.max_sessions,
    )
    db.add(mentor)
    await db.commit()
    await db.refresh(mentor, ["user"])
    return _mentor_to_dict(mentor)


@router.post("/{hackathon_id}/mentors/{mentor_id}/requests", status_code=201)
async def request_mentor(
    hackathon_id: uuid.UUID,
    mentor_id: uuid.UUID,
    body: MentorRequestCreate,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Request help from a mentor."""
    user = await get_current_user(db, authorization)
    result = await db.execute(
        select(MentorProfile).where(
            MentorProfile.id == mentor_id,
            MentorProfile.hackathon_id == hackathon_id,
        )
    )
    mentor = result.scalar_one_or_none()
    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor not found")
    if not mentor.is_available:
        raise HTTPException(status_code=400, detail="Mentor is not currently available")

    # Check pending request limit
    pending = await db.execute(
        select(MentorRequest).where(
            MentorRequest.mentor_id == mentor_id,
            MentorRequest.status == "pending",
        )
    )
    if len(pending.scalars().all()) >= mentor.max_sessions:
        raise HTTPException(status_code=400, detail="Mentor has reached max pending sessions")

    req = MentorRequest(
        mentor_id=mentor_id,
        hackathon_id=hackathon_id,
        user_id=user.id,
        topic=body.topic,
        description=body.description,
    )
    db.add(req)
    await db.commit()
    await db.refresh(req, ["user", "mentor"])
    return {
        "id": str(req.id),
        "mentor_name": req.mentor.name if req.mentor else None,
        "topic": req.topic,
        "description": req.description,
        "status": req.status,
        "created_at": req.created_at.isoformat(),
    }


@router.get("/{hackathon_id}/mentors/{mentor_id}/requests")
async def list_mentor_requests(
    hackathon_id: uuid.UUID,
    mentor_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """List requests for a mentor (mentor only)."""
    user = await get_current_user(db, authorization)
    result = await db.execute(
        select(MentorProfile).where(
            MentorProfile.id == mentor_id,
            MentorProfile.hackathon_id == hackathon_id,
        )
    )
    mentor = result.scalar_one_or_none()
    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor not found")
    if mentor.user_id != user.id:
        raise HTTPException(status_code=403, detail="Only the mentor can view their requests")

    result = await db.execute(
        select(MentorRequest)
        .where(MentorRequest.mentor_id == mentor_id)
        .options(selectinload(MentorRequest.user))
        .order_by(MentorRequest.created_at.desc())
    )
    requests = result.scalars().all()
    return {
        "requests": [
            {
                "id": str(r.id),
                "user_name": r.user.name if r.user else None,
                "topic": r.topic,
                "description": r.description,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
            }
            for r in requests
        ]
    }


@router.patch("/{hackathon_id}/mentors/{mentor_id}/requests/{request_id}")
async def update_mentor_request(
    hackathon_id: uuid.UUID,
    mentor_id: uuid.UUID,
    request_id: uuid.UUID,
    body: dict,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Update a mentor request status (mentor only)."""
    user = await get_current_user(db, authorization)
    result = await db.execute(
        select(MentorProfile).where(
            MentorProfile.id == mentor_id,
            MentorProfile.hackathon_id == hackathon_id,
        )
    )
    mentor = result.scalar_one_or_none()
    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor not found")
    if mentor.user_id != user.id:
        raise HTTPException(status_code=403, detail="Only the mentor can update requests")

    new_status = body.get("status")
    if new_status not in ("accepted", "completed", "cancelled"):
        raise HTTPException(status_code=422, detail="status must be 'accepted', 'completed', or 'cancelled'")

    result = await db.execute(select(MentorRequest).where(MentorRequest.id == request_id))
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    req.status = new_status
    await db.commit()
    return {"id": str(req.id), "status": req.status}
