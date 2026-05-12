"""Participant profile routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import require_clerk_user
from app.database import get_db
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/api/users", tags=["profiles"])
public_router = APIRouter(tags=["profiles"])


class UpdateProfileRequest(BaseModel):
    """Request body for updating a user's public profile."""

    bio: str | None = None
    skills: list | None = None
    links: dict | None = None
    availability: str | None = None
    looking_for_team: bool | None = None


@router.get("/me/profile")
async def get_my_profile(
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's public profile.

    Behavior:
    1. Load the user profile via ProfileService.
    2. Return 404 if the user is not found.
    3. Return serialized profile fields.

    Raises: HTTPException(404) if the user is not found.
    Side Effects: None (read-only).
    Dependencies: app.services.profile_service.ProfileService, app.clerk_auth.require_clerk_user.
    Consumers: GET /api/users/me/profile, profile page.
    """
    service = ProfileService()
    user = await service.get_profile(db, user_payload["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "bio": user.bio,
        "skills": user.skills,
        "links": user.links,
        "availability": user.availability,
        "looking_for_team": user.looking_for_team,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@public_router.get("/api/hackathons/{hackathon_id}/participants")
async def list_participants(
    hackathon_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List public participant profiles for a hackathon.

    Behavior:
    1. Fetch accepted registrations via ProfileService.
    2. Return serialized list of public profile fields.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.services.profile_service.ProfileService.
    Consumers: GET /api/hackathons/{id}/participants, participant directory.
    """
    from uuid import UUID

    service = ProfileService()
    users = await service.list_participants(db, UUID(hackathon_id))
    return [
        {
            "id": user.id,
            "name": user.name,
            "bio": user.bio,
            "skills": user.skills,
            "links": user.links,
            "availability": user.availability,
            "looking_for_team": user.looking_for_team,
        }
        for user in users
    ]


@router.put("/me/profile")
async def update_my_profile(
    body: UpdateProfileRequest,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's public profile.

    Behavior:
    1. Apply updates via ProfileService.
    2. Return 404 if the user is not found.
    3. Return serialized updated profile fields.

    Raises: HTTPException(404) if the user is not found.
    Side Effects: Mutates User profile fields.
    Dependencies: app.services.profile_service.ProfileService, app.clerk_auth.require_clerk_user.
    Consumers: PUT /api/users/me/profile, profile edit form.
    """
    service = ProfileService()
    try:
        user = await service.update_profile(
            db,
            user_id=user_payload["sub"],
            bio=body.bio,
            skills=body.skills,
            links=body.links,
            availability=body.availability,
            looking_for_team=body.looking_for_team,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "bio": user.bio,
        "skills": user.skills,
        "links": user.links,
        "availability": user.availability,
        "looking_for_team": user.looking_for_team,
        "updated": True,
    }
