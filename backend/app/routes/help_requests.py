"""Mentorship help queue routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import require_clerk_user
from app.database import get_db
from app.services.help_request_service import HelpRequestService

router = APIRouter(prefix="/api/help-requests", tags=["help-requests"])


class CreateHelpRequestRequest(BaseModel):
    hackathon_id: str
    title: str
    description: str | None = None


class UpdateHelpRequestRequest(BaseModel):
    title: str | None = None
    description: str | None = None


@router.post("", status_code=201)
async def create_help_request(
    body: CreateHelpRequestRequest,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new help request."""
    service = HelpRequestService()
    req = await service.create_help_request(
        db,
        hackathon_id=UUID(body.hackathon_id),
        requester_id=user_payload["sub"],
        title=body.title,
        description=body.description,
    )
    return {
        "id": str(req.id),
        "hackathon_id": str(req.hackathon_id),
        "requester_id": req.requester_id,
        "title": req.title,
        "description": req.description,
        "status": req.status,
        "created_at": req.created_at.isoformat() if req.created_at else None,
    }


@router.get("")
async def list_open_help_requests(
    hackathon_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """List open help requests for a hackathon."""
    service = HelpRequestService()
    requests = await service.list_open_requests(db, UUID(hackathon_id))
    return [
        {
            "id": str(r.id),
            "hackathon_id": str(r.hackathon_id),
            "requester_id": r.requester_id,
            "title": r.title,
            "description": r.description,
            "status": r.status,
            "mentor_id": r.mentor_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in requests
    ]


@router.get("/{request_id}")
async def get_help_request(
    request_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a single help request."""
    service = HelpRequestService()
    req = await service.get_help_request(db, UUID(request_id))
    if not req:
        raise HTTPException(status_code=404, detail="Help request not found")
    return {
        "id": str(req.id),
        "hackathon_id": str(req.hackathon_id),
        "requester_id": req.requester_id,
        "title": req.title,
        "description": req.description,
        "status": req.status,
        "mentor_id": req.mentor_id,
        "created_at": req.created_at.isoformat() if req.created_at else None,
        "claimed_at": req.claimed_at.isoformat() if req.claimed_at else None,
        "resolved_at": req.resolved_at.isoformat() if req.resolved_at else None,
    }


@router.post("/{request_id}/claim")
async def claim_help_request(
    request_id: str,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Claim an open help request."""
    service = HelpRequestService()
    try:
        req = await service.claim_help_request(db, UUID(request_id), user_payload["sub"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {
        "id": str(req.id),
        "status": req.status,
        "mentor_id": req.mentor_id,
        "claimed": True,
    }


@router.post("/{request_id}/resolve")
async def resolve_help_request(
    request_id: str,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a help request as resolved."""
    service = HelpRequestService()
    try:
        req = await service.resolve_help_request(db, UUID(request_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {
        "id": str(req.id),
        "status": req.status,
        "resolved": True,
    }


@router.delete("/{request_id}", status_code=204)
async def delete_help_request(
    request_id: str,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a help request."""
    service = HelpRequestService()
    try:
        await service.delete_help_request(db, UUID(request_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return None
