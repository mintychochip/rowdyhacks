"""Team management routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import require_clerk_user
from app.database import get_db
from app.services.team_service import TeamService

router = APIRouter(prefix="/api/teams", tags=["teams"])


class CreateTeamRequest(BaseModel):
    hackathon_id: str
    name: str


class JoinTeamRequest(BaseModel):
    join_code: str


class UpdateTeamRequest(BaseModel):
    name: str


@router.post("", status_code=201)
async def create_team(
    body: CreateTeamRequest,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new team for a hackathon (requires accepted registration)."""
    service = TeamService()
    try:
        team = await service.create_team(
            db,
            hackathon_id=uuid.UUID(body.hackathon_id),
            name=body.name,
            captain_id=user_payload["sub"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "id": str(team.id),
        "name": team.name,
        "join_code": team.join_code,
        "captain_id": team.captain_id,
        "hackathon_id": str(team.hackathon_id),
        "created_at": team.created_at.isoformat() if team.created_at else None,
    }


@router.post("/{team_id}/join")
async def join_team(
    team_id: str,
    body: JoinTeamRequest,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Join a team by its join code."""
    service = TeamService()
    try:
        team = await service.join_team_by_code(db, body.join_code, user_payload["sub"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "id": str(team.id),
        "name": team.name,
        "joined": True,
    }


@router.get("/{team_id}")
async def get_team(
    team_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get team details with member list."""
    from uuid import UUID

    service = TeamService()
    team = await service.get_team(db, UUID(team_id))
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    members = []
    for m in team.members:
        members.append(
            {
                "user_id": m.user_id,
                "joined_at": m.joined_at.isoformat() if m.joined_at else None,
            }
        )

    return {
        "id": str(team.id),
        "name": team.name,
        "join_code": team.join_code,
        "captain_id": team.captain_id,
        "hackathon_id": str(team.hackathon_id),
        "created_at": team.created_at.isoformat() if team.created_at else None,
        "members": members,
    }


@router.put("/{team_id}")
async def update_team(
    team_id: str,
    body: UpdateTeamRequest,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Update team name (captain only)."""
    from uuid import UUID

    service = TeamService()
    try:
        team = await service.update_team(db, UUID(team_id), user_payload["sub"], name=body.name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    return {
        "id": str(team.id),
        "name": team.name,
        "updated": True,
    }


@router.delete("/{team_id}/members/{user_id}")
async def remove_team_member(
    team_id: str,
    user_id: str,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a member from the team (captain only)."""
    from uuid import UUID

    service = TeamService()
    try:
        await service.remove_member(db, UUID(team_id), user_payload["sub"], user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    return {"removed": user_id}
