"""Team formation and matching routes."""

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import TeamPost, TeamRequest
from app.routes.deps import get_current_user

router = APIRouter(prefix="/api/hackathons", tags=["teams"])


class TeamPostCreate(BaseModel):
    title: str
    description: str | None = None
    looking_for: list[str] | None = None
    offering: list[str] | None = None
    max_members: int = 4


class TeamRequestCreate(BaseModel):
    message: str | None = None


def _post_to_dict(p: TeamPost) -> dict:
    return {
        "id": str(p.id),
        "hackathon_id": str(p.hackathon_id),
        "user_id": str(p.user_id),
        "user_name": p.user.name if p.user else None,
        "title": p.title,
        "description": p.description,
        "looking_for": p.looking_for or [],
        "offering": p.offering or [],
        "max_members": p.max_members,
        "is_open": p.is_open,
        "created_at": p.created_at.isoformat(),
    }


@router.get("/{hackathon_id}/teams")
async def list_team_posts(
    hackathon_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """List open team posts for a hackathon."""
    result = await db.execute(
        select(TeamPost)
        .where(TeamPost.hackathon_id == hackathon_id, TeamPost.is_open.is_(True))
        .options(selectinload(TeamPost.user))
        .order_by(TeamPost.created_at.desc())
    )
    posts = result.scalars().all()
    return {"posts": [_post_to_dict(p) for p in posts]}


@router.post("/{hackathon_id}/teams", status_code=201)
async def create_team_post(
    hackathon_id: uuid.UUID,
    body: TeamPostCreate,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Create a team-finding post."""
    user = await get_current_user(db, authorization)
    post = TeamPost(
        hackathon_id=hackathon_id,
        user_id=user.id,
        title=body.title,
        description=body.description,
        looking_for=body.looking_for,
        offering=body.offering,
        max_members=body.max_members,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post, ["user"])
    return _post_to_dict(post)


@router.delete("/{hackathon_id}/teams/{post_id}")
async def close_team_post(
    hackathon_id: uuid.UUID,
    post_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Close a team post (owner only)."""
    user = await get_current_user(db, authorization)
    result = await db.execute(select(TeamPost).where(TeamPost.id == post_id, TeamPost.hackathon_id == hackathon_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Team post not found")
    if post.user_id != user.id:
        raise HTTPException(status_code=403, detail="Only the post owner can close it")
    post.is_open = False
    await db.commit()
    return {"ok": True}


@router.post("/{hackathon_id}/teams/{post_id}/requests", status_code=201)
async def request_to_join(
    hackathon_id: uuid.UUID,
    post_id: uuid.UUID,
    body: TeamRequestCreate,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Request to join a team."""
    user = await get_current_user(db, authorization)
    result = await db.execute(select(TeamPost).where(TeamPost.id == post_id, TeamPost.hackathon_id == hackathon_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Team post not found")
    if not post.is_open:
        raise HTTPException(status_code=400, detail="This team post is no longer open")

    # Check duplicate
    existing = await db.execute(
        select(TeamRequest).where(TeamRequest.team_post_id == post_id, TeamRequest.user_id == user.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="You have already requested to join this team")

    req = TeamRequest(
        team_post_id=post_id,
        user_id=user.id,
        message=body.message,
    )
    db.add(req)
    await db.commit()
    await db.refresh(req, ["user"])
    return {
        "id": str(req.id),
        "user_name": req.user.name if req.user else None,
        "message": req.message,
        "status": req.status,
        "created_at": req.created_at.isoformat(),
    }


@router.get("/{hackathon_id}/teams/{post_id}/requests")
async def list_team_requests(
    hackathon_id: uuid.UUID,
    post_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """List requests for a team post (post owner only)."""
    user = await get_current_user(db, authorization)
    result = await db.execute(select(TeamPost).where(TeamPost.id == post_id, TeamPost.hackathon_id == hackathon_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Team post not found")
    if post.user_id != user.id:
        raise HTTPException(status_code=403, detail="Only the post owner can view requests")

    result = await db.execute(
        select(TeamRequest)
        .where(TeamRequest.team_post_id == post_id)
        .options(selectinload(TeamRequest.user))
        .order_by(TeamRequest.created_at.desc())
    )
    requests = result.scalars().all()
    return {
        "requests": [
            {
                "id": str(r.id),
                "user_name": r.user.name if r.user else None,
                "message": r.message,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
            }
            for r in requests
        ]
    }


@router.patch("/{hackathon_id}/teams/{post_id}/requests/{request_id}")
async def respond_to_request(
    hackathon_id: uuid.UUID,
    post_id: uuid.UUID,
    request_id: uuid.UUID,
    body: dict,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Accept or reject a team join request (post owner only)."""
    user = await get_current_user(db, authorization)
    result = await db.execute(select(TeamPost).where(TeamPost.id == post_id, TeamPost.hackathon_id == hackathon_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Team post not found")
    if post.user_id != user.id:
        raise HTTPException(status_code=403, detail="Only the post owner can respond to requests")

    new_status = body.get("status")
    if new_status not in ("accepted", "rejected"):
        raise HTTPException(status_code=422, detail="status must be 'accepted' or 'rejected'")

    result = await db.execute(select(TeamRequest).where(TeamRequest.id == request_id))
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    req.status = new_status
    await db.commit()
    return {"id": str(req.id), "status": req.status}
