"""Prize and track prize management routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import require_clerk_user
from app.database import get_db
from app.services.prize_service import PrizeService

router = APIRouter(prefix="/api/prizes", tags=["prizes"])


class CreatePrizeRequest(BaseModel):
    hackathon_id: str
    name: str
    description: str | None = None
    amount: str | None = None
    currency: str = "USD"
    track_id: str | None = None


class UpdatePrizeRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    amount: str | None = None
    currency: str | None = None
    track_id: str | None = None


@router.post("", status_code=201)
async def create_prize(
    body: CreatePrizeRequest,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new prize."""
    service = PrizeService()
    prize = await service.create_prize(
        db,
        hackathon_id=UUID(body.hackathon_id),
        name=body.name,
        description=body.description,
        amount=body.amount,
        currency=body.currency,
        track_id=UUID(body.track_id) if body.track_id else None,
    )
    return {
        "id": str(prize.id),
        "hackathon_id": str(prize.hackathon_id),
        "track_id": str(prize.track_id) if prize.track_id else None,
        "name": prize.name,
        "description": prize.description,
        "amount": prize.amount,
        "currency": prize.currency,
        "created_at": prize.created_at.isoformat() if prize.created_at else None,
    }


@router.get("")
async def list_prizes(
    hackathon_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """List prizes for a hackathon."""
    service = PrizeService()
    prizes = await service.list_prizes(db, UUID(hackathon_id))
    return [
        {
            "id": str(p.id),
            "hackathon_id": str(p.hackathon_id),
            "track_id": str(p.track_id) if p.track_id else None,
            "name": p.name,
            "description": p.description,
            "amount": p.amount,
            "currency": p.currency,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in prizes
    ]


@router.get("/{prize_id}")
async def get_prize(
    prize_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a single prize."""
    service = PrizeService()
    prize = await service.get_prize(db, UUID(prize_id))
    if not prize:
        raise HTTPException(status_code=404, detail="Prize not found")
    return {
        "id": str(prize.id),
        "hackathon_id": str(prize.hackathon_id),
        "track_id": str(prize.track_id) if prize.track_id else None,
        "name": prize.name,
        "description": prize.description,
        "amount": prize.amount,
        "currency": prize.currency,
        "created_at": prize.created_at.isoformat() if prize.created_at else None,
    }


@router.put("/{prize_id}")
async def update_prize(
    prize_id: str,
    body: UpdatePrizeRequest,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a prize."""
    service = PrizeService()
    try:
        prize = await service.update_prize(
            db,
            UUID(prize_id),
            name=body.name,
            description=body.description,
            amount=body.amount,
            currency=body.currency,
            track_id=UUID(body.track_id) if body.track_id else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return {
        "id": str(prize.id),
        "name": prize.name,
        "updated": True,
    }


@router.delete("/{prize_id}", status_code=204)
async def delete_prize(
    prize_id: str,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a prize."""
    service = PrizeService()
    try:
        await service.delete_prize(db, UUID(prize_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return None
