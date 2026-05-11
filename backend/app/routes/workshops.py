"""Workshop and schedule management routes."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import require_clerk_user
from app.database import get_db
from app.services.workshop_service import WorkshopService

router = APIRouter(prefix="/api/workshops", tags=["workshops"])


class CreateWorkshopRequest(BaseModel):
    hackathon_id: str
    title: str
    description: str | None = None
    start_time: str
    end_time: str
    location: str | None = None
    speaker_name: str | None = None


class UpdateWorkshopRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    location: str | None = None
    speaker_name: str | None = None


def _iso_to_dt(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@router.post("", status_code=201)
async def create_workshop(
    body: CreateWorkshopRequest,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new workshop (any authenticated user)."""
    service = WorkshopService()
    workshop = await service.create_workshop(
        db,
        hackathon_id=UUID(body.hackathon_id),
        title=body.title,
        description=body.description,
        start_time=_iso_to_dt(body.start_time),
        end_time=_iso_to_dt(body.end_time),
        location=body.location,
        speaker_name=body.speaker_name,
    )
    return {
        "id": str(workshop.id),
        "hackathon_id": str(workshop.hackathon_id),
        "title": workshop.title,
        "description": workshop.description,
        "start_time": workshop.start_time.isoformat() if workshop.start_time else None,
        "end_time": workshop.end_time.isoformat() if workshop.end_time else None,
        "location": workshop.location,
        "speaker_name": workshop.speaker_name,
        "created_at": workshop.created_at.isoformat() if workshop.created_at else None,
    }


@router.get("")
async def list_workshops(
    hackathon_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """List workshops for a hackathon."""
    service = WorkshopService()
    workshops = await service.list_workshops(db, UUID(hackathon_id))
    return [
        {
            "id": str(w.id),
            "hackathon_id": str(w.hackathon_id),
            "title": w.title,
            "description": w.description,
            "start_time": w.start_time.isoformat() if w.start_time else None,
            "end_time": w.end_time.isoformat() if w.end_time else None,
            "location": w.location,
            "speaker_name": w.speaker_name,
            "created_at": w.created_at.isoformat() if w.created_at else None,
        }
        for w in workshops
    ]


@router.get("/{workshop_id}")
async def get_workshop(
    workshop_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a single workshop."""
    service = WorkshopService()
    workshop = await service.get_workshop(db, UUID(workshop_id))
    if not workshop:
        raise HTTPException(status_code=404, detail="Workshop not found")
    return {
        "id": str(workshop.id),
        "hackathon_id": str(workshop.hackathon_id),
        "title": workshop.title,
        "description": workshop.description,
        "start_time": workshop.start_time.isoformat() if workshop.start_time else None,
        "end_time": workshop.end_time.isoformat() if workshop.end_time else None,
        "location": workshop.location,
        "speaker_name": workshop.speaker_name,
        "created_at": workshop.created_at.isoformat() if workshop.created_at else None,
    }


@router.put("/{workshop_id}")
async def update_workshop(
    workshop_id: str,
    body: UpdateWorkshopRequest,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a workshop."""
    service = WorkshopService()
    try:
        workshop = await service.update_workshop(
            db,
            UUID(workshop_id),
            title=body.title,
            description=body.description,
            start_time=_iso_to_dt(body.start_time) if body.start_time else None,
            end_time=_iso_to_dt(body.end_time) if body.end_time else None,
            location=body.location,
            speaker_name=body.speaker_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return {
        "id": str(workshop.id),
        "title": workshop.title,
        "updated": True,
    }


@router.delete("/{workshop_id}", status_code=204)
async def delete_workshop(
    workshop_id: str,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a workshop."""
    service = WorkshopService()
    try:
        await service.delete_workshop(db, UUID(workshop_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return None
