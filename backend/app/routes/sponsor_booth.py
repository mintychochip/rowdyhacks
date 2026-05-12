"""Sponsor booth management routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import require_clerk_user
from app.database import get_db
from app.services.sponsor_booth_service import SponsorBoothService

router = APIRouter(prefix="/api/hackathons", tags=["sponsor-booths"])


class AssignBoothRequest(BaseModel):
    """Request body for assigning a sponsor booth."""

    sponsor_id: str
    booth_number: str | None = None


@router.post("/{hackathon_id}/sponsor-booths", status_code=201)
async def assign_booth(
    hackathon_id: str,
    body: AssignBoothRequest,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Assign a booth to a sponsor (organizer).

    Behavior:
    1. Call SponsorBoothService.assign_booth.
    2. Translate ValueError to HTTPException(400).
    3. Return serialized booth details.

    Raises: HTTPException(400) if booth already assigned.
    Side Effects: Inserts SponsorBooth row.
    Dependencies: app.services.sponsor_booth_service.SponsorBoothService.
    Consumers: POST /api/hackathons/{hackathon_id}/sponsor-booths.
    """
    service = SponsorBoothService()
    try:
        booth = await service.assign_booth(
            db,
            hackathon_id=UUID(hackathon_id),
            sponsor_id=UUID(body.sponsor_id),
            booth_number=body.booth_number,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "id": str(booth.id),
        "hackathon_id": str(booth.hackathon_id),
        "sponsor_id": str(booth.sponsor_id),
        "booth_number": booth.booth_number,
        "lead_scan_count": booth.lead_scan_count,
        "created_at": booth.created_at.isoformat() if booth.created_at else None,
    }


@router.get("/{hackathon_id}/sponsor-booths")
async def list_booths(
    hackathon_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List sponsor booths for a hackathon.

    Behavior:
    1. Fetch booths via SponsorBoothService.
    2. Return serialized list.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.services.sponsor_booth_service.SponsorBoothService.
    Consumers: GET /api/hackathons/{hackathon_id}/sponsor-booths.
    """
    service = SponsorBoothService()
    booths = await service.list_booths(db, UUID(hackathon_id))
    return [
        {
            "id": str(booth.id),
            "hackathon_id": str(booth.hackathon_id),
            "sponsor_id": str(booth.sponsor_id),
            "booth_number": booth.booth_number,
            "lead_scan_count": booth.lead_scan_count,
            "created_at": booth.created_at.isoformat() if booth.created_at else None,
        }
        for booth in booths
    ]


@router.post("/sponsor-booths/{booth_id}/scan-lead")
async def scan_lead(
    booth_id: str,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Scan a lead at a sponsor booth.

    Behavior:
    1. Call SponsorBoothService.scan_lead.
    2. Translate ValueError to HTTPException(404).
    3. Return updated booth with new scan count.

    Raises: HTTPException(404) if booth not found.
    Side Effects: Updates SponsorBooth row.
    Dependencies: app.services.sponsor_booth_service.SponsorBoothService.
    Consumers: POST /api/hackathons/sponsor-booths/{booth_id}/scan-lead.
    """
    service = SponsorBoothService()
    try:
        booth = await service.scan_lead(db, UUID(booth_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return {
        "id": str(booth.id),
        "hackathon_id": str(booth.hackathon_id),
        "sponsor_id": str(booth.sponsor_id),
        "booth_number": booth.booth_number,
        "lead_scan_count": booth.lead_scan_count,
    }
