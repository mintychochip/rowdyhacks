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
    """Request body for creating a new team within a hackathon."""

    hackathon_id: str
    name: str


class JoinTeamRequest(BaseModel):
    """Request body for joining an existing team by its join code."""

    join_code: str


class UpdateTeamRequest(BaseModel):
    """Request body for updating a team's name."""

    name: str


@router.post("", status_code=201)
async def create_team(
    body: CreateTeamRequest,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new team for a hackathon (requires accepted registration).

    Behavior:
    1. Instantiate TeamService and attempt to create a team via the service.
    2. Catch ValueError and translate to HTTPException(400).
    3. Return the serialized team with id, name, join_code, captain_id, hackathon_id, and created_at.

    Raises: HTTPException(400) if the user cannot create a team (no accepted registration or team already exists).
    Side Effects: Inserts Team row via TeamService.
    Dependencies: app.services.team_service.TeamService.
    Consumers: POST /api/teams, team creation form.
    """
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
    """Join a team by its join code.

    Behavior:
    1. Instantiate TeamService and attempt to join the team by code.
    2. Catch ValueError and translate to HTTPException(400).
    3. Return the serialized team with id, name, and joined flag.

    Raises: HTTPException(400) if the join code is invalid or the user is already on the team.
    Side Effects: Mutates team membership via TeamService.
    Dependencies: app.services.team_service.TeamService.
    Consumers: POST /api/teams/{team_id}/join, team join form.
    """
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
    """Get team details with member list.

    Behavior:
    1. Instantiate TeamService and fetch the team by UUID.
    2. Return 404 if the team is not found.
    3. Build the members list from the team's member relationships.
    4. Return the serialized team with id, name, join_code, captain_id, hackathon_id, created_at, and members.

    Raises: HTTPException(404) if the team does not exist.
    Side Effects: None (read-only).
    Dependencies: app.services.team_service.TeamService.
    Consumers: GET /api/teams/{team_id}, team detail page.
    """
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
    """Update team name (captain only).

    Behavior:
    1. Instantiate TeamService and attempt to update the team name.
    2. Catch ValueError as 404 and PermissionError as 403.
    3. Return the serialized team with id, name, and updated flag.

    Raises: HTTPException(404) if the team is not found. HTTPException(403) if the requesting user is not the captain.
    Side Effects: Mutates Team.name via TeamService.
    Dependencies: app.services.team_service.TeamService.
    Consumers: PUT /api/teams/{team_id}, team settings form.
    """
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
    """Remove a member from the team (captain only).

    Behavior:
    1. Instantiate TeamService and attempt to remove the member.
    2. Catch ValueError as 400 and PermissionError as 403.
    3. Return a confirmation dict with the removed user_id.

    Raises: HTTPException(400) if the operation is invalid (e.g. removing self). HTTPException(403) if the requesting user is not the captain.
    Side Effects: Deletes team membership via TeamService.
    Dependencies: app.services.team_service.TeamService.
    Consumers: DELETE /api/teams/{team_id}/members/{user_id}, team management panel.
    """
    from uuid import UUID

    service = TeamService()
    try:
        await service.remove_member(db, UUID(team_id), user_payload["sub"], user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    return {"removed": user_id}
