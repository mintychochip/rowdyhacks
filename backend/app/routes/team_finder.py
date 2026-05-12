"""Team finder / hacker matching routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import require_clerk_user
from app.database import get_db
from app.services.team_finder_service import TeamFinderService

router = APIRouter(tags=["team-finder"])


class CreateTeamFinderPostRequest(BaseModel):
    """Request body for creating a team finder post."""

    post_type: str
    skills_needed: list[str] | None = None
    description: str | None = None


@router.post("/api/hackathons/{hackathon_id}/team-finder", status_code=201)
async def create_team_finder_post(
    hackathon_id: str,
    body: CreateTeamFinderPostRequest,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a team finder post for a hackathon.

    Behavior:
    1. Validate post_type is either 'looking_for_team' or 'looking_for_members'.
    2. Create the post via TeamFinderService.
    3. Return serialized post details.

    Raises: HTTPException(400) if post_type is invalid.
    Side Effects: Inserts TeamFinderPost row.
    Dependencies: app.services.team_finder_service.TeamFinderService, app.clerk_auth.require_clerk_user.
    Consumers: POST /api/hackathons/{id}/team-finder, team finder form.
    """
    service = TeamFinderService()
    try:
        post = await service.create_post(
            db,
            hackathon_id=UUID(hackathon_id),
            user_id=user_payload["sub"],
            post_type=body.post_type,
            skills_needed=body.skills_needed,
            description=body.description,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "id": str(post.id),
        "hackathon_id": str(post.hackathon_id),
        "user_id": post.user_id,
        "post_type": post.post_type,
        "skills_needed": post.skills_needed,
        "description": post.description,
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "is_active": post.is_active,
    }


@router.get("/api/hackathons/{hackathon_id}/team-finder")
async def list_team_finder_posts(
    hackathon_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List active team finder posts for a hackathon.

    Behavior:
    1. Fetch active posts via TeamFinderService.
    2. Return serialized list with owner names.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.services.team_finder_service.TeamFinderService.
    Consumers: GET /api/hackathons/{id}/team-finder, team finder page.
    """
    service = TeamFinderService()
    posts = await service.list_posts(db, UUID(hackathon_id))
    return [
        {
            "id": str(post.id),
            "hackathon_id": str(post.hackathon_id),
            "user_id": post.user_id,
            "user_name": post.user.name if post.user else None,
            "post_type": post.post_type,
            "skills_needed": post.skills_needed,
            "description": post.description,
            "created_at": post.created_at.isoformat() if post.created_at else None,
            "is_active": post.is_active,
        }
        for post in posts
    ]


@router.delete("/api/hackathons/{hackathon_id}/team-finder/{post_id}")
async def deactivate_team_finder_post(
    hackathon_id: str,
    post_id: str,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a team finder post (owner only).

    Behavior:
    1. Deactivate the post via TeamFinderService.
    2. Return 404 if the post is not found, 403 if not the owner.
    3. Return confirmation.

    Raises: HTTPException(404) if the post is not found. HTTPException(403) if the requester is not the owner.
    Side Effects: Updates TeamFinderPost.is_active to False.
    Dependencies: app.services.team_finder_service.TeamFinderService, app.clerk_auth.require_clerk_user.
    Consumers: DELETE /api/hackathons/{id}/team-finder/{post_id}.
    """
    service = TeamFinderService()
    try:
        await service.deactivate_post(db, UUID(post_id), user_payload["sub"])
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    return {"deactivated": True}
