"""Sponsor management routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import require_clerk_user
from app.database import get_db
from app.services.sponsor_service import SponsorService

router = APIRouter(prefix="/api/sponsors", tags=["sponsors"])


class CreateSponsorRequest(BaseModel):
    """Request body for creating a sponsor.

    Attributes:
        hackathon_id: UUID of the hackathon this sponsor supports.
        name: Display name of the sponsor.
        tier: Sponsorship tier (default "silver").
        logo_url: Optional URL to the sponsor's logo.
        website_url: Optional URL to the sponsor's website.
        description: Optional description or tagline.
    """

    hackathon_id: str
    name: str
    tier: str = "silver"
    logo_url: str | None = None
    website_url: str | None = None
    description: str | None = None


class UpdateSponsorRequest(BaseModel):
    """Request body for updating a sponsor.

    Attributes:
        name: Optional new display name.
        tier: Optional new sponsorship tier.
        logo_url: Optional new logo URL.
        website_url: Optional new website URL.
        description: Optional new description.
    """

    name: str | None = None
    tier: str | None = None
    logo_url: str | None = None
    website_url: str | None = None
    description: str | None = None


@router.post("", status_code=201)
async def create_sponsor(
    body: CreateSponsorRequest,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new sponsor.

    Behavior:
    1. Create the sponsor via SponsorService using the provided payload fields.
    2. Return serialized sponsor details.

    Raises: None
    Side Effects: Inserts sponsor row.
    Dependencies: app.services.sponsor_service.SponsorService, app.clerk_auth.require_clerk_user.
    Consumers: POST /api/sponsors, sponsor management.
    """
    service = SponsorService()
    sponsor = await service.create_sponsor(
        db,
        hackathon_id=UUID(body.hackathon_id),
        name=body.name,
        tier=body.tier,
        logo_url=body.logo_url,
        website_url=body.website_url,
        description=body.description,
    )
    return {
        "id": str(sponsor.id),
        "hackathon_id": str(sponsor.hackathon_id),
        "name": sponsor.name,
        "tier": sponsor.tier,
        "logo_url": sponsor.logo_url,
        "website_url": sponsor.website_url,
        "description": sponsor.description,
        "created_at": sponsor.created_at.isoformat() if sponsor.created_at else None,
    }


@router.get("")
async def list_sponsors(
    hackathon_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """List sponsors for a hackathon.

    Behavior:
    1. Fetch sponsors for the hackathon via SponsorService.
    2. Return serialized list of sponsor dicts.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.services.sponsor_service.SponsorService.
    Consumers: GET /api/sponsors, public sponsor listing.
    """
    service = SponsorService()
    sponsors = await service.list_sponsors(db, UUID(hackathon_id))
    return [
        {
            "id": str(s.id),
            "hackathon_id": str(s.hackathon_id),
            "name": s.name,
            "tier": s.tier,
            "logo_url": s.logo_url,
            "website_url": s.website_url,
            "description": s.description,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in sponsors
    ]


@router.get("/{sponsor_id}")
async def get_sponsor(
    sponsor_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a single sponsor by ID.

    Behavior:
    1. Fetch the sponsor via SponsorService.
    2. Return 404 if not found.
    3. Return serialized sponsor details.

    Raises: HTTPException(404) if the sponsor is not found.
    Side Effects: None (read-only).
    Dependencies: app.services.sponsor_service.SponsorService.
    Consumers: GET /api/sponsors/{sponsor_id}, sponsor detail view.
    """
    service = SponsorService()
    sponsor = await service.get_sponsor(db, UUID(sponsor_id))
    if not sponsor:
        raise HTTPException(status_code=404, detail="Sponsor not found")
    return {
        "id": str(sponsor.id),
        "hackathon_id": str(sponsor.hackathon_id),
        "name": sponsor.name,
        "tier": sponsor.tier,
        "logo_url": sponsor.logo_url,
        "website_url": sponsor.website_url,
        "description": sponsor.description,
        "created_at": sponsor.created_at.isoformat() if sponsor.created_at else None,
    }


@router.put("/{sponsor_id}")
async def update_sponsor(
    sponsor_id: str,
    body: UpdateSponsorRequest,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a sponsor.

    Behavior:
    1. Apply updates via SponsorService; 404 if sponsor not found.
    2. Return updated sponsor id, name, and updated flag.

    Raises: HTTPException(404) if the sponsor is not found.
    Side Effects: Mutates sponsor row.
    Dependencies: app.services.sponsor_service.SponsorService.
    Consumers: PUT /api/sponsors/{sponsor_id}, sponsor management.
    """
    service = SponsorService()
    try:
        sponsor = await service.update_sponsor(
            db,
            UUID(sponsor_id),
            name=body.name,
            tier=body.tier,
            logo_url=body.logo_url,
            website_url=body.website_url,
            description=body.description,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return {
        "id": str(sponsor.id),
        "name": sponsor.name,
        "updated": True,
    }


@router.delete("/{sponsor_id}", status_code=204)
async def delete_sponsor(
    sponsor_id: str,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a sponsor.

    Behavior:
    1. Delete the sponsor via SponsorService; 404 if not found.
    2. Return empty 204 response.

    Raises: HTTPException(404) if the sponsor is not found.
    Side Effects: Deletes sponsor row.
    Dependencies: app.services.sponsor_service.SponsorService.
    Consumers: DELETE /api/sponsors/{sponsor_id}, sponsor management.
    """
    service = SponsorService()
    try:
        await service.delete_sponsor(db, UUID(sponsor_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return None
