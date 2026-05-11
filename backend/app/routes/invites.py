"""Hackathon invite code routes."""

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_organizer
from app.database import get_db
from app.models import Hackathon, HackathonInvite, UserRole

router = APIRouter(prefix="/api/hackathons", tags=["invites"])


class InviteGenerateRequest(BaseModel):
    count: int = 10
    role: UserRole = UserRole.participant
    expires_days: int | None = None


def _generate_invite_code(hackathon_slug: str) -> str:
    suffix = secrets.token_urlsafe(12).replace("-", "").replace("_", "")[:16].upper()
    return f"{hackathon_slug.upper()}-{suffix}"


@router.post("/{hackathon_id}/invites", status_code=status.HTTP_201_CREATED)
async def generate_invites(
    hackathon_id: uuid.UUID,
    body: InviteGenerateRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_organizer),
):
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hackathon not found")

    expires_at = None
    if body.expires_days:
        expires_at = datetime.now(UTC) + timedelta(days=body.expires_days)

    codes = []
    slug = hackathon.name.replace(" ", "-").lower()[:10]
    for _ in range(body.count):
        code = _generate_invite_code(slug)
        # Ensure uniqueness (retry if collision)
        while True:
            existing = await db.execute(select(HackathonInvite).where(HackathonInvite.code == code))
            if not existing.scalar_one_or_none():
                break
            code = _generate_invite_code(slug)

        invite = HackathonInvite(
            hackathon_id=hackathon_id,
            code=code,
            role=body.role,
            uses_remaining=1,
            expires_at=expires_at,
            created_by=user.id,
        )
        db.add(invite)
        codes.append(code)

    await db.commit()
    return {"codes": codes, "count": len(codes)}


@router.get("/{hackathon_id}/invites")
async def list_invites(
    hackathon_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_organizer),
):
    result = await db.execute(select(HackathonInvite).where(HackathonInvite.hackathon_id == hackathon_id))
    invites = result.scalars().all()
    return [
        {
            "code": i.code,
            "role": i.role.value,
            "uses_remaining": i.uses_remaining,
            "expires_at": i.expires_at.isoformat() if i.expires_at else None,
            "created_at": i.created_at.isoformat(),
        }
        for i in invites
    ]


@router.delete("/invites/{code}")
async def revoke_invite(
    code: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_organizer),
):
    result = await db.execute(select(HackathonInvite).where(HackathonInvite.code == code))
    invite = result.scalar_one_or_none()
    if not invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")
    invite.uses_remaining = 0
    await db.commit()
    return {"message": f"Invite {code} revoked"}
