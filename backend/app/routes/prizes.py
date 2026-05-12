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
    """Request body for creating a prize.

    Attributes:
        hackathon_id: UUID of the hackathon this prize belongs to.
        name: Display name of the prize.
        description: Optional description of the prize.
        amount: Optional prize amount string (e.g. "500").
        currency: Currency code (default "USD").
        track_id: Optional UUID of the associated track.
    """

    hackathon_id: str
    name: str
    description: str | None = None
    amount: str | None = None
    currency: str = "USD"
    track_id: str | None = None


class UpdatePrizeRequest(BaseModel):
    """Request body for updating a prize.

    Attributes:
        name: Optional new display name.
        description: Optional new description.
        amount: Optional new prize amount.
        currency: Optional new currency code.
        track_id: Optional new associated track UUID.
    """

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
    """Create a new prize.

    Behavior:
    1. Create the prize via PrizeService using the provided payload fields.
    2. Return serialized prize details.

    Raises: None
    Side Effects: Inserts prize row.
    Dependencies: app.services.prize_service.PrizeService, app.clerk_auth.require_clerk_user.
    Consumers: POST /api/prizes, prize management.
    """
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
    """List prizes for a hackathon.

    Behavior:
    1. Fetch prizes for the hackathon via PrizeService.
    2. Return serialized list of prize dicts.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.services.prize_service.PrizeService.
    Consumers: GET /api/prizes, public prize listing.
    """
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
    """Get a single prize by ID.

    Behavior:
    1. Fetch the prize via PrizeService.
    2. Return 404 if not found.
    3. Return serialized prize details.

    Raises: HTTPException(404) if the prize is not found.
    Side Effects: None (read-only).
    Dependencies: app.services.prize_service.PrizeService.
    Consumers: GET /api/prizes/{prize_id}, prize detail view.
    """
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
    """Update a prize.

    Behavior:
    1. Apply updates via PrizeService; 404 if prize not found.
    2. Return updated prize id, name, and updated flag.

    Raises: HTTPException(404) if the prize is not found.
    Side Effects: Mutates prize row.
    Dependencies: app.services.prize_service.PrizeService.
    Consumers: PUT /api/prizes/{prize_id}, prize management.
    """
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
    """Delete a prize.

    Behavior:
    1. Delete the prize via PrizeService; 404 if not found.
    2. Return empty 204 response.

    Raises: HTTPException(404) if the prize is not found.
    Side Effects: Deletes prize row.
    Dependencies: app.services.prize_service.PrizeService.
    Consumers: DELETE /api/prizes/{prize_id}, prize management.
    """
    service = PrizeService()
    try:
        await service.delete_prize(db, UUID(prize_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return None


@router.post("/{prize_id}/award/{team_id}", status_code=201)
async def award_prize(
    prize_id: str,
    team_id: str,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Award a prize to a team.

    Behavior:
    1. Call PrizeService.award_prize.
    2. Translate ValueError to HTTPException(400 or 404).
    3. Return serialized award details.

    Raises: HTTPException(404) if prize not found; HTTPException(400) if already awarded or hackathon mismatch.
    Side Effects: Inserts PrizeAward row.
    Dependencies: app.services.prize_service.PrizeService.
    Consumers: POST /api/prizes/{prize_id}/award/{team_id}.
    """
    service = PrizeService()
    prize = await service.get_prize(db, UUID(prize_id))
    if not prize:
        raise HTTPException(status_code=404, detail="Prize not found")
    try:
        award = await service.award_prize(
            db,
            prize_id=UUID(prize_id),
            team_id=UUID(team_id),
            hackathon_id=prize.hackathon_id,
            awarded_by=user_payload["sub"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "id": str(award.id),
        "prize_id": str(award.prize_id),
        "team_id": str(award.team_id),
        "hackathon_id": str(award.hackathon_id),
        "awarded_at": award.awarded_at.isoformat() if award.awarded_at else None,
        "awarded_by": award.awarded_by,
    }


@router.delete("/{prize_id}/award", status_code=204)
async def revoke_award(
    prize_id: str,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a prize award.

    Behavior:
    1. Call PrizeService.revoke_award.
    2. Translate ValueError to HTTPException(404).
    3. Return empty 204 response.

    Raises: HTTPException(404) if award not found.
    Side Effects: Deletes PrizeAward row.
    Dependencies: app.services.prize_service.PrizeService.
    Consumers: DELETE /api/prizes/{prize_id}/award.
    """
    service = PrizeService()
    try:
        await service.revoke_award(db, UUID(prize_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return None
