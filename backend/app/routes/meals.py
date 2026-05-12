"""Meal management routes."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import require_clerk_user
from app.database import get_db
from app.services.meal_service import MealService

router = APIRouter(prefix="/api/hackathons", tags=["meals"])


def _iso_to_dt(value: str | None) -> datetime | None:
    """Convert an ISO 8601 string to a timezone-aware datetime."""
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class CreateMealRequest(BaseModel):
    """Request body for creating a meal slot."""

    meal_type: str
    start_time: str
    end_time: str
    location: str | None = None
    max_capacity: int | None = None


class MealRSVPRequest(BaseModel):
    """Request body for RSVPing to a meal."""

    dietary_restrictions: str | None = None


@router.post("/{hackathon_id}/meals", status_code=201)
async def create_meal(
    hackathon_id: str,
    body: CreateMealRequest,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a meal slot for a hackathon (organizer).

    Behavior:
    1. Parse start_time and end_time from ISO strings.
    2. Create the meal slot via MealService.
    3. Return serialized meal details.

    Raises: None
    Side Effects: Inserts MealSlot row.
    Dependencies: app.services.meal_service.MealService.
    Consumers: POST /api/hackathons/{hackathon_id}/meals.
    """
    service = MealService()
    meal = await service.create_meal_slot(
        db,
        hackathon_id=UUID(hackathon_id),
        meal_type=body.meal_type,
        start_time=_iso_to_dt(body.start_time),
        end_time=_iso_to_dt(body.end_time),
        location=body.location,
        max_capacity=body.max_capacity,
    )
    return {
        "id": str(meal.id),
        "hackathon_id": str(meal.hackathon_id),
        "meal_type": meal.meal_type,
        "start_time": meal.start_time.isoformat() if meal.start_time else None,
        "end_time": meal.end_time.isoformat() if meal.end_time else None,
        "location": meal.location,
        "max_capacity": meal.max_capacity,
        "created_at": meal.created_at.isoformat() if meal.created_at else None,
    }


@router.get("/{hackathon_id}/meals")
async def list_meals(
    hackathon_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List meal slots for a hackathon.

    Behavior:
    1. Fetch meal slots via MealService.
    2. Return serialized list.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.services.meal_service.MealService.
    Consumers: GET /api/hackathons/{hackathon_id}/meals.
    """
    service = MealService()
    meals = await service.list_meal_slots(db, UUID(hackathon_id))
    return [
        {
            "id": str(meal.id),
            "hackathon_id": str(meal.hackathon_id),
            "meal_type": meal.meal_type,
            "start_time": meal.start_time.isoformat() if meal.start_time else None,
            "end_time": meal.end_time.isoformat() if meal.end_time else None,
            "location": meal.location,
            "max_capacity": meal.max_capacity,
            "created_at": meal.created_at.isoformat() if meal.created_at else None,
        }
        for meal in meals
    ]


@router.post("/meals/{meal_id}/rsvp", status_code=201)
async def rsvp_for_meal(
    meal_id: str,
    body: MealRSVPRequest,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """RSVP for a meal slot.

    Behavior:
    1. Call MealService.rsvp_for_meal.
    2. Translate ValueError to HTTPException(400 or 404).
    3. Return serialized RSVP details.

    Raises: HTTPException(404) if meal not found; HTTPException(400) if already RSVP'd or at capacity.
    Side Effects: Inserts MealRSVP row.
    Dependencies: app.services.meal_service.MealService.
    Consumers: POST /api/hackathons/meals/{meal_id}/rsvp.
    """
    service = MealService()
    try:
        rsvp = await service.rsvp_for_meal(
            db,
            meal_slot_id=UUID(meal_id),
            user_id=user_payload["sub"],
            dietary_restrictions=body.dietary_restrictions,
        )
    except ValueError as exc:
        detail = str(exc)
        status = 404 if "not found" in detail else 400
        raise HTTPException(status_code=status, detail=detail)

    return {
        "id": str(rsvp.id),
        "meal_slot_id": str(rsvp.meal_slot_id),
        "user_id": rsvp.user_id,
        "dietary_restrictions": rsvp.dietary_restrictions,
        "registered_at": rsvp.registered_at.isoformat() if rsvp.registered_at else None,
    }


@router.get("/meals/{meal_id}/attendance")
async def list_meal_attendance(
    meal_id: str,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """List attendance for a meal slot (organizer).

    Behavior:
    1. Call MealService.list_attendance.
    2. Return serialized list of RSVPs.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.services.meal_service.MealService.
    Consumers: GET /api/hackathons/meals/{meal_id}/attendance.
    """
    service = MealService()
    rsvps = await service.list_attendance(db, UUID(meal_id))
    return [
        {
            "id": str(rsvp.id),
            "meal_slot_id": str(rsvp.meal_slot_id),
            "user_id": rsvp.user_id,
            "dietary_restrictions": rsvp.dietary_restrictions,
            "registered_at": rsvp.registered_at.isoformat() if rsvp.registered_at else None,
        }
        for rsvp in rsvps
    ]
