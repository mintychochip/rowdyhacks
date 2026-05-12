"""Workshop and schedule management routes."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import require_clerk_user, require_organizer
from app.database import get_db
from app.models import Hackathon, HackathonOrganizer, UserRole
from app.services.workshop_service import WorkshopService

router = APIRouter(prefix="/api/workshops", tags=["workshops"])


class CreateWorkshopRequest(BaseModel):
    """Request body for creating a workshop."""

    hackathon_id: str
    title: str
    description: str | None = None
    start_time: str
    end_time: str
    location: str | None = None
    speaker_name: str | None = None
    max_capacity: int | None = None


class UpdateWorkshopRequest(BaseModel):
    """Request body for updating a workshop."""

    title: str | None = None
    description: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    location: str | None = None
    speaker_name: str | None = None
    max_capacity: int | None = None


async def _ensure_organizer(user, hackathon: Hackathon, db: AsyncSession):
    """Verify the requesting user is the primary or co-organizer of a hackathon.

    Behavior:
    1. Return immediately if the user is the primary organizer.
    2. Query HackathonOrganizer for a matching (hackathon_id, user_id) row.
    3. Return if a co-organizer record exists.
    4. Raise 403 if neither condition is met.

    Raises: HTTPException(403) if user lacks organizer privileges.
    Side Effects: None (read-only).
    Dependencies: app.models.HackathonOrganizer, app.models.UserRole.
    Consumers: Internal helper used by workshop route guards.
    """
    if user.role == UserRole.organizer and hackathon.organizer_id == user.id:
        return
    result = await db.execute(
        select(HackathonOrganizer).where(
            and_(HackathonOrganizer.hackathon_id == hackathon.id, HackathonOrganizer.user_id == user.id)
        )
    )
    if result.scalar_one_or_none():
        return
    raise HTTPException(status_code=403, detail="Only the hackathon organizer can perform this action")


def _iso_to_dt(value: str | None) -> datetime | None:
    """Convert an ISO 8601 string to a timezone-aware datetime.

    Behavior:
    1. Return None if input is None.
    2. Replace 'Z' suffix with '+00:00' and parse via datetime.fromisoformat.
    3. Return the timezone-aware datetime object.

    Raises: None
    Side Effects: None (pure function).
    Dependencies: datetime.datetime.
    Consumers: Internal helper used by create_workshop and update_workshop.
    """
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@router.post("", status_code=201)
async def create_workshop(
    body: CreateWorkshopRequest,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new workshop (any authenticated user).

    Behavior:
    1. Parse start_time and end_time from ISO strings.
    2. Create the workshop via WorkshopService.
    3. Return serialized workshop details.

    Raises: None
    Side Effects: Inserts workshop row.
    Dependencies: app.services.workshop_service.WorkshopService.
    Consumers: POST /api/workshops, schedule management.
    """
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
        max_capacity=body.max_capacity,
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
        "max_capacity": workshop.max_capacity,
        "created_at": workshop.created_at.isoformat() if workshop.created_at else None,
    }


@router.get("")
async def list_workshops(
    hackathon_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """List workshops for a hackathon.

    Behavior:
    1. Fetch workshops for the given hackathon via WorkshopService.
    2. Return serialized list of workshop dicts.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.services.workshop_service.WorkshopService.
    Consumers: GET /api/workshops, public schedule view.
    """
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
            "max_capacity": w.max_capacity,
            "created_at": w.created_at.isoformat() if w.created_at else None,
        }
        for w in workshops
    ]


@router.get("/{workshop_id}")
async def get_workshop(
    workshop_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a single workshop by ID.

    Behavior:
    1. Fetch the workshop via WorkshopService.
    2. Return 404 if not found.
    3. Return serialized workshop details.

    Raises: HTTPException(404) if the workshop is not found.
    Side Effects: None (read-only).
    Dependencies: app.services.workshop_service.WorkshopService.
    Consumers: GET /api/workshops/{workshop_id}, schedule detail view.
    """
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
        "max_capacity": workshop.max_capacity,
        "created_at": workshop.created_at.isoformat() if workshop.created_at else None,
    }


@router.put("/{workshop_id}")
async def update_workshop(
    workshop_id: str,
    body: UpdateWorkshopRequest,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a workshop.

    Behavior:
    1. Parse optional start_time and end_time from ISO strings.
    2. Apply updates via WorkshopService; 404 if workshop not found.
    3. Return updated workshop id, title, and updated flag.

    Raises: HTTPException(404) if the workshop is not found.
    Side Effects: Mutates workshop row.
    Dependencies: app.services.workshop_service.WorkshopService.
    Consumers: PUT /api/workshops/{workshop_id}, schedule management.
    """
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
            max_capacity=body.max_capacity,
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
    """Delete a workshop.

    Behavior:
    1. Delete the workshop via WorkshopService; 404 if not found.
    2. Return empty 204 response.

    Raises: HTTPException(404) if the workshop is not found.
    Side Effects: Deletes workshop row.
    Dependencies: app.services.workshop_service.WorkshopService.
    Consumers: DELETE /api/workshops/{workshop_id}, schedule management.
    """
    service = WorkshopService()
    try:
        await service.delete_workshop(db, UUID(workshop_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return None


# --- RSVP routes ---


@router.post("/{workshop_id}/rsvp", status_code=201)
async def register_for_workshop(
    workshop_id: str,
    hackathon_id: str = Query(...),
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Register the current user for a workshop.

    Behavior:
    1. Call WorkshopService.register_for_workshop.
    2. Translate ValueError to HTTPException(400 or 404).
    3. Return serialized RSVP details.

    Raises: HTTPException(400) if already registered or at capacity; HTTPException(404) if workshop not found.
    Side Effects: Inserts WorkshopRSVP row.
    Dependencies: app.services.workshop_service.WorkshopService.
    Consumers: POST /api/workshops/{workshop_id}/rsvp.
    """
    service = WorkshopService()
    try:
        rsvp = await service.register_for_workshop(
            db,
            workshop_id=UUID(workshop_id),
            user_id=user_payload["sub"],
            hackathon_id=UUID(hackathon_id),
        )
    except ValueError as exc:
        detail = str(exc)
        status = 400 if detail in ("Already registered for this workshop", "Workshop is at capacity") else 404
        raise HTTPException(status_code=status, detail=detail)

    return {
        "id": str(rsvp.id),
        "user_id": rsvp.user_id,
        "workshop_id": str(rsvp.workshop_id),
        "hackathon_id": str(rsvp.hackathon_id),
        "status": rsvp.status.value,
        "registered_at": rsvp.registered_at.isoformat() if rsvp.registered_at else None,
        "attended_at": rsvp.attended_at.isoformat() if rsvp.attended_at else None,
    }


@router.delete("/{workshop_id}/rsvp", status_code=200)
async def cancel_rsvp(
    workshop_id: str,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel the current user's RSVP for a workshop.

    Behavior:
    1. Call WorkshopService.cancel_rsvp.
    2. Translate ValueError to HTTPException(404).
    3. Return serialized RSVP with cancelled status.

    Raises: HTTPException(404) if RSVP not found.
    Side Effects: Updates WorkshopRSVP row.
    Dependencies: app.services.workshop_service.WorkshopService.
    Consumers: DELETE /api/workshops/{workshop_id}/rsvp.
    """
    service = WorkshopService()
    try:
        rsvp = await service.cancel_rsvp(db, workshop_id=UUID(workshop_id), user_id=user_payload["sub"])
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return {
        "id": str(rsvp.id),
        "user_id": rsvp.user_id,
        "workshop_id": str(rsvp.workshop_id),
        "hackathon_id": str(rsvp.hackathon_id),
        "status": rsvp.status.value,
        "registered_at": rsvp.registered_at.isoformat() if rsvp.registered_at else None,
        "attended_at": rsvp.attended_at.isoformat() if rsvp.attended_at else None,
    }


@router.post("/{workshop_id}/rsvp/{user_id}/attended")
async def mark_attended(
    workshop_id: str,
    user_id: str,
    auth: dict = Depends(require_organizer),
    db: AsyncSession = Depends(get_db),
):
    """Mark a participant as attended (organizer only).

    Behavior:
    1. Call WorkshopService.mark_attended.
    2. Translate ValueError to HTTPException(404).
    3. Return serialized RSVP with attended status.

    Raises: HTTPException(404) if RSVP not found.
    Side Effects: Updates WorkshopRSVP row.
    Dependencies: app.services.workshop_service.WorkshopService.
    Consumers: POST /api/workshops/{workshop_id}/rsvp/{user_id}/attended.
    """
    service = WorkshopService()
    try:
        rsvp = await service.mark_attended(db, workshop_id=UUID(workshop_id), user_id=user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return {
        "id": str(rsvp.id),
        "user_id": rsvp.user_id,
        "workshop_id": str(rsvp.workshop_id),
        "hackathon_id": str(rsvp.hackathon_id),
        "status": rsvp.status.value,
        "registered_at": rsvp.registered_at.isoformat() if rsvp.registered_at else None,
        "attended_at": rsvp.attended_at.isoformat() if rsvp.attended_at else None,
    }


@router.get("/{workshop_id}/rsvps")
async def list_workshop_rsvps(
    workshop_id: str,
    auth: dict = Depends(require_organizer),
    db: AsyncSession = Depends(get_db),
):
    """List all RSVPs for a workshop (organizer only).

    Behavior:
    1. Call WorkshopService.list_rsvps_for_workshop.
    2. Return serialized list of RSVP dicts.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.services.workshop_service.WorkshopService.
    Consumers: GET /api/workshops/{workshop_id}/rsvps.
    """
    service = WorkshopService()
    rsvps = await service.list_rsvps_for_workshop(db, workshop_id=UUID(workshop_id))
    return [
        {
            "id": str(rsvp.id),
            "user_id": rsvp.user_id,
            "workshop_id": str(rsvp.workshop_id),
            "hackathon_id": str(rsvp.hackathon_id),
            "status": rsvp.status.value,
            "registered_at": rsvp.registered_at.isoformat() if rsvp.registered_at else None,
            "attended_at": rsvp.attended_at.isoformat() if rsvp.attended_at else None,
        }
        for rsvp in rsvps
    ]


# Note: this is mounted under /api/hackathons in main.py via a separate router
# For backward compatibility we also expose it here under workshops router
@router.get("/hackathons/{hackathon_id}/my-rsvps")
async def list_my_rsvps_for_hackathon(
    hackathon_id: str,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """List the current user's RSVPs for a hackathon.

    Behavior:
    1. Call WorkshopService.list_rsvps_for_user.
    2. Return serialized list of RSVP dicts.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.services.workshop_service.WorkshopService.
    Consumers: GET /api/hackathons/{hackathon_id}/my-rsvps.
    """
    service = WorkshopService()
    rsvps = await service.list_rsvps_for_user(db, user_id=user_payload["sub"], hackathon_id=UUID(hackathon_id))
    return [
        {
            "id": str(rsvp.id),
            "user_id": rsvp.user_id,
            "workshop_id": str(rsvp.workshop_id),
            "hackathon_id": str(rsvp.hackathon_id),
            "status": rsvp.status.value,
            "registered_at": rsvp.registered_at.isoformat() if rsvp.registered_at else None,
            "attended_at": rsvp.attended_at.isoformat() if rsvp.attended_at else None,
        }
        for rsvp in rsvps
    ]
