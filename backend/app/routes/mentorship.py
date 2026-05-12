"""Mentorship pairing routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import require_clerk_user
from app.database import get_db
from app.services.mentorship_service import MentorshipService

router = APIRouter(tags=["mentorship"])


class CreateMentorshipRequest(BaseModel):
    """Request body for creating a mentorship request."""

    topic: str


@router.post("/api/hackathons/{hackathon_id}/mentorship/request", status_code=201)
async def request_mentor(
    hackathon_id: str,
    body: CreateMentorshipRequest,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Request a mentor for a hackathon.

    Behavior:
    1. Create the mentorship request via MentorshipService.
    2. Return serialized request details.

    Raises: None
    Side Effects: Inserts MentorshipRequest row.
    Dependencies: app.services.mentorship_service.MentorshipService, app.clerk_auth.require_clerk_user.
    Consumers: POST /api/hackathons/{id}/mentorship/request.
    """
    service = MentorshipService()
    request = await service.create_request(
        db,
        hackathon_id=UUID(hackathon_id),
        requester_id=user_payload["sub"],
        topic=body.topic,
    )

    return {
        "id": str(request.id),
        "hackathon_id": str(request.hackathon_id),
        "requester_id": request.requester_id,
        "topic": request.topic,
        "status": request.status,
        "created_at": request.created_at.isoformat() if request.created_at else None,
        "scheduled_at": request.scheduled_at.isoformat() if request.scheduled_at else None,
    }


@router.get("/api/hackathons/{hackathon_id}/mentorship/requests")
async def list_mentorship_requests(
    hackathon_id: str,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """List mentorship requests for the current user at a hackathon.

    Behavior:
    1. Fetch requests where the user is the requester or mentor via MentorshipService.
    2. Return serialized list with requester and mentor names.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.services.mentorship_service.MentorshipService.
    Consumers: GET /api/hackathons/{id}/mentorship/requests.
    """
    service = MentorshipService()
    requests = await service.list_my_requests(db, UUID(hackathon_id), user_payload["sub"])
    return [
        {
            "id": str(req.id),
            "hackathon_id": str(req.hackathon_id),
            "requester_id": req.requester_id,
            "requester_name": req.requester.name if req.requester else None,
            "mentor_id": req.mentor_id,
            "mentor_name": req.mentor.name if req.mentor else None,
            "topic": req.topic,
            "status": req.status,
            "created_at": req.created_at.isoformat() if req.created_at else None,
            "scheduled_at": req.scheduled_at.isoformat() if req.scheduled_at else None,
        }
        for req in requests
    ]


@router.post("/api/mentorship/{request_id}/accept")
async def accept_mentorship_request(
    request_id: str,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Accept a pending mentorship request.

    Behavior:
    1. Accept the request via MentorshipService.
    2. Return 404 if the request is not found, 400 if not pending.
    3. Return updated request details.

    Raises: HTTPException(404) if the request is not found. HTTPException(400) if the request is not pending.
    Side Effects: Updates MentorshipRequest status and mentor_id.
    Dependencies: app.services.mentorship_service.MentorshipService.
    Consumers: POST /api/mentorship/{id}/accept.
    """
    service = MentorshipService()
    try:
        request = await service.accept_request(db, UUID(request_id), user_payload["sub"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "id": str(request.id),
        "status": request.status,
        "mentor_id": request.mentor_id,
        "updated": True,
    }


@router.post("/api/mentorship/{request_id}/complete")
async def complete_mentorship_request(
    request_id: str,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a mentorship request as completed.

    Behavior:
    1. Complete the request via MentorshipService.
    2. Return 404 if the request is not found, 403 if unauthorized, 400 if not accepted.
    3. Return updated request details.

    Raises: HTTPException(404) if not found. HTTPException(403) if unauthorized. HTTPException(400) if not accepted.
    Side Effects: Updates MentorshipRequest status to completed.
    Dependencies: app.services.mentorship_service.MentorshipService.
    Consumers: POST /api/mentorship/{id}/complete.
    """
    service = MentorshipService()
    try:
        request = await service.complete_request(db, UUID(request_id), user_payload["sub"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    return {
        "id": str(request.id),
        "status": request.status,
        "updated": True,
    }
