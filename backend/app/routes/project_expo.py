"""Project expo and public voting routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import require_clerk_user, require_hackathon_organizer
from app.database import get_db
from app.services.project_expo_service import ProjectExpoService

router = APIRouter(tags=["project-expo"])


@router.get("/api/hackathons/{hackathon_id}/project-expo")
async def list_project_expo_submissions(
    hackathon_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List all submissions with public details for a hackathon.

    Behavior:
    1. Fetch submissions via ProjectExpoService.
    2. Return serialized list of public submission details.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.services.project_expo_service.ProjectExpoService.
    Consumers: GET /api/hackathons/{id}/project-expo, project expo page.
    """
    service = ProjectExpoService()
    submissions = await service.list_submissions(db, UUID(hackathon_id))
    return [
        {
            "id": str(sub.id),
            "project_title": sub.project_title,
            "project_description": sub.project_description,
            "devpost_url": sub.devpost_url,
            "github_url": sub.github_url,
            "team_members": sub.team_members,
            "claimed_tech": sub.claimed_tech,
            "created_at": sub.created_at.isoformat() if sub.created_at else None,
        }
        for sub in submissions
    ]


@router.post("/api/hackathons/{hackathon_id}/project-expo/{submission_id}/vote", status_code=201)
async def cast_project_expo_vote(
    hackathon_id: str,
    submission_id: str,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Cast a people's choice vote for a submission.

    Behavior:
    1. Cast the vote via ProjectExpoService.
    2. Return 400 if the user has already voted in this hackathon.
    3. Return confirmation.

    Raises: HTTPException(400) if the user has already voted.
    Side Effects: Inserts PublicVote row.
    Dependencies: app.services.project_expo_service.ProjectExpoService.
    Consumers: POST /api/hackathons/{id}/project-expo/{submission_id}/vote.
    """
    service = ProjectExpoService()
    try:
        vote = await service.cast_vote(
            db,
            hackathon_id=UUID(hackathon_id),
            submission_id=UUID(submission_id),
            voter_id=user_payload["sub"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "id": str(vote.id),
        "hackathon_id": str(vote.hackathon_id),
        "submission_id": str(vote.submission_id),
        "voter_id": vote.voter_id,
        "created_at": vote.created_at.isoformat() if vote.created_at else None,
    }


@router.get("/api/hackathons/{hackathon_id}/project-expo/results")
async def get_project_expo_results(
    hackathon_id: str,
    org: dict = Depends(require_hackathon_organizer),
    db: AsyncSession = Depends(get_db),
):
    """Get vote counts per submission for a hackathon (organizer only).

    Behavior:
    1. Fetch results via ProjectExpoService.
    2. Return serialized vote tally.

    Raises: HTTPException(403) if the user is not an organizer.
    Side Effects: None (read-only).
    Dependencies: app.services.project_expo_service.ProjectExpoService.
    Consumers: GET /api/hackathons/{id}/project-expo/results, organizer dashboard.
    """
    service = ProjectExpoService()
    results = await service.get_results(db, UUID(hackathon_id))
    return {"hackathon_id": hackathon_id, "results": results}
