"""Volunteer and staff management routes."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import require_clerk_user
from app.database import get_db
from app.services.volunteer_service import VolunteerService

router = APIRouter(prefix="/api/hackathons", tags=["volunteers"])


def _iso_to_dt(value: str | None) -> datetime | None:
    """Convert an ISO 8601 string to a timezone-aware datetime."""
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class AddVolunteerRequest(BaseModel):
    """Request body for adding a volunteer shift."""

    volunteer_id: str
    shift_name: str
    start_time: str
    end_time: str
    location: str | None = None


@router.post("/{hackathon_id}/volunteers", status_code=201)
async def add_volunteer(
    hackathon_id: str,
    body: AddVolunteerRequest,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a volunteer shift for a hackathon (organizer).

    Behavior:
    1. Call VolunteerService.add_volunteer.
    2. Translate ValueError to HTTPException(400 or 404).
    3. Return serialized shift details.

    Raises: HTTPException(404) if user not found; HTTPException(400) if not a volunteer.
    Side Effects: Inserts VolunteerShift row.
    Dependencies: app.services.volunteer_service.VolunteerService.
    Consumers: POST /api/hackathons/{hackathon_id}/volunteers.
    """
    service = VolunteerService()
    try:
        shift = await service.add_volunteer(
            db,
            hackathon_id=UUID(hackathon_id),
            volunteer_id=body.volunteer_id,
            shift_name=body.shift_name,
            start_time=_iso_to_dt(body.start_time),
            end_time=_iso_to_dt(body.end_time),
            location=body.location,
        )
    except ValueError as exc:
        detail = str(exc)
        status = 404 if "not found" in detail else 400
        raise HTTPException(status_code=status, detail=detail)

    return {
        "id": str(shift.id),
        "hackathon_id": str(shift.hackathon_id),
        "volunteer_id": shift.volunteer_id,
        "shift_name": shift.shift_name,
        "start_time": shift.start_time.isoformat() if shift.start_time else None,
        "end_time": shift.end_time.isoformat() if shift.end_time else None,
        "location": shift.location,
        "checked_in_at": shift.checked_in_at.isoformat() if shift.checked_in_at else None,
        "created_at": shift.created_at.isoformat() if shift.created_at else None,
    }


@router.get("/{hackathon_id}/volunteers")
async def list_volunteers(
    hackathon_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List volunteer shifts for a hackathon.

    Behavior:
    1. Fetch shifts via VolunteerService.
    2. Return serialized list.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.services.volunteer_service.VolunteerService.
    Consumers: GET /api/hackathons/{hackathon_id}/volunteers.
    """
    service = VolunteerService()
    shifts = await service.list_volunteers(db, UUID(hackathon_id))
    return [
        {
            "id": str(shift.id),
            "hackathon_id": str(shift.hackathon_id),
            "volunteer_id": shift.volunteer_id,
            "shift_name": shift.shift_name,
            "start_time": shift.start_time.isoformat() if shift.start_time else None,
            "end_time": shift.end_time.isoformat() if shift.end_time else None,
            "location": shift.location,
            "checked_in_at": shift.checked_in_at.isoformat() if shift.checked_in_at else None,
            "created_at": shift.created_at.isoformat() if shift.created_at else None,
        }
        for shift in shifts
    ]


@router.post("/volunteers/{shift_id}/checkin")
async def checkin_volunteer(
    shift_id: str,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Check in a volunteer for their shift.

    Behavior:
    1. Call VolunteerService.checkin_volunteer.
    2. Translate ValueError to HTTPException(404).
    3. Return updated shift details.

    Raises: HTTPException(404) if shift not found.
    Side Effects: Updates VolunteerShift row.
    Dependencies: app.services.volunteer_service.VolunteerService.
    Consumers: POST /api/hackathons/volunteers/{shift_id}/checkin.
    """
    service = VolunteerService()
    try:
        shift = await service.checkin_volunteer(db, UUID(shift_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return {
        "id": str(shift.id),
        "hackathon_id": str(shift.hackathon_id),
        "volunteer_id": shift.volunteer_id,
        "shift_name": shift.shift_name,
        "start_time": shift.start_time.isoformat() if shift.start_time else None,
        "end_time": shift.end_time.isoformat() if shift.end_time else None,
        "location": shift.location,
        "checked_in_at": shift.checked_in_at.isoformat() if shift.checked_in_at else None,
    }


@router.get("/volunteers/{volunteer_id}/shifts")
async def list_my_shifts(
    volunteer_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List shifts for a specific volunteer.

    Behavior:
    1. Fetch shifts via VolunteerService.
    2. Return serialized list.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.services.volunteer_service.VolunteerService.
    Consumers: GET /api/hackathons/volunteers/{volunteer_id}/shifts.
    """
    service = VolunteerService()
    shifts = await service.list_my_shifts(db, volunteer_id)
    return [
        {
            "id": str(shift.id),
            "hackathon_id": str(shift.hackathon_id),
            "volunteer_id": shift.volunteer_id,
            "shift_name": shift.shift_name,
            "start_time": shift.start_time.isoformat() if shift.start_time else None,
            "end_time": shift.end_time.isoformat() if shift.end_time else None,
            "location": shift.location,
            "checked_in_at": shift.checked_in_at.isoformat() if shift.checked_in_at else None,
            "created_at": shift.created_at.isoformat() if shift.created_at else None,
        }
        for shift in shifts
    ]
