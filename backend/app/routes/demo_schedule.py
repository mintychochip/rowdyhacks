"""Demo and pitch scheduling routes."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import require_clerk_user
from app.database import get_db
from app.services.demo_schedule_service import DemoScheduleService

router = APIRouter(prefix="/api/hackathons", tags=["demo-schedule"])


def _iso_to_dt(value: str | None) -> datetime | None:
    """Convert an ISO 8601 string to a timezone-aware datetime."""
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class CreateDemoSlotRequest(BaseModel):
    """Request body for creating a demo slot."""

    start_time: str
    end_time: str
    room: str | None = None
    judge_panel_id: str | None = None


@router.post("/{hackathon_id}/demo-slots", status_code=201)
async def create_demo_slot(
    hackathon_id: str,
    body: CreateDemoSlotRequest,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a demo slot for a hackathon (organizer).

    Behavior:
    1. Parse start_time and end_time from ISO strings.
    2. Create the slot via DemoScheduleService.
    3. Return serialized slot details.

    Raises: None
    Side Effects: Inserts DemoSlot row.
    Dependencies: app.services.demo_schedule_service.DemoScheduleService.
    Consumers: POST /api/hackathons/{hackathon_id}/demo-slots.
    """
    service = DemoScheduleService()
    slot = await service.create_slot(
        db,
        hackathon_id=UUID(hackathon_id),
        start_time=_iso_to_dt(body.start_time),
        end_time=_iso_to_dt(body.end_time),
        room=body.room,
        judge_panel_id=body.judge_panel_id,
    )
    return {
        "id": str(slot.id),
        "hackathon_id": str(slot.hackathon_id),
        "start_time": slot.start_time.isoformat() if slot.start_time else None,
        "end_time": slot.end_time.isoformat() if slot.end_time else None,
        "room": slot.room,
        "judge_panel_id": slot.judge_panel_id,
        "status": slot.status,
        "created_at": slot.created_at.isoformat() if slot.created_at else None,
    }


@router.get("/{hackathon_id}/demo-slots")
async def list_demo_slots(
    hackathon_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List demo slots for a hackathon.

    Behavior:
    1. Fetch slots via DemoScheduleService.
    2. Return serialized list.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.services.demo_schedule_service.DemoScheduleService.
    Consumers: GET /api/hackathons/{hackathon_id}/demo-slots.
    """
    service = DemoScheduleService()
    slots = await service.list_slots(db, UUID(hackathon_id))
    return [
        {
            "id": str(slot.id),
            "hackathon_id": str(slot.hackathon_id),
            "submission_id": str(slot.submission_id) if slot.submission_id else None,
            "start_time": slot.start_time.isoformat() if slot.start_time else None,
            "end_time": slot.end_time.isoformat() if slot.end_time else None,
            "room": slot.room,
            "judge_panel_id": slot.judge_panel_id,
            "status": slot.status,
            "created_at": slot.created_at.isoformat() if slot.created_at else None,
        }
        for slot in slots
    ]


@router.post("/{hackathon_id}/demo-slots/assign")
async def auto_assign_demo_slots(
    hackathon_id: str,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Auto-assign submissions to empty demo slots.

    Behavior:
    1. Call DemoScheduleService.auto_assign_submissions_to_slots.
    2. Return updated slot list.

    Raises: None
    Side Effects: Updates DemoSlot rows.
    Dependencies: app.services.demo_schedule_service.DemoScheduleService.
    Consumers: POST /api/hackathons/{hackathon_id}/demo-slots/assign.
    """
    service = DemoScheduleService()
    slots = await service.auto_assign_submissions_to_slots(db, UUID(hackathon_id))
    return [
        {
            "id": str(slot.id),
            "hackathon_id": str(slot.hackathon_id),
            "submission_id": str(slot.submission_id) if slot.submission_id else None,
            "start_time": slot.start_time.isoformat() if slot.start_time else None,
            "end_time": slot.end_time.isoformat() if slot.end_time else None,
            "room": slot.room,
            "judge_panel_id": slot.judge_panel_id,
            "status": slot.status,
        }
        for slot in slots
    ]


@router.get("/{hackathon_id}/my-demo-slot")
async def get_my_demo_slot(
    hackathon_id: str,
    team_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Get the demo slot assigned to my team.

    Behavior:
    1. Call DemoScheduleService.get_my_demo_slot.
    2. Return 404 if no slot found.
    3. Return serialized slot details.

    Raises: HTTPException(404) if no demo slot is assigned.
    Side Effects: None (read-only).
    Dependencies: app.services.demo_schedule_service.DemoScheduleService.
    Consumers: GET /api/hackathons/{hackathon_id}/my-demo-slot.
    """
    service = DemoScheduleService()
    slot = await service.get_my_demo_slot(db, UUID(hackathon_id), UUID(team_id))
    if not slot:
        raise HTTPException(status_code=404, detail="No demo slot assigned")
    return {
        "id": str(slot.id),
        "hackathon_id": str(slot.hackathon_id),
        "submission_id": str(slot.submission_id) if slot.submission_id else None,
        "start_time": slot.start_time.isoformat() if slot.start_time else None,
        "end_time": slot.end_time.isoformat() if slot.end_time else None,
        "room": slot.room,
        "judge_panel_id": slot.judge_panel_id,
        "status": slot.status,
        "created_at": slot.created_at.isoformat() if slot.created_at else None,
    }
