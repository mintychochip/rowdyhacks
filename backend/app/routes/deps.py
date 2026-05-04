"""Shared route dependencies for authentication and authorization."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import decode_token
from app.models import Hackathon, HackathonOrganizer, User, UserRole


def get_current_user_payload(authorization: str | None) -> dict:
    """Extract and validate the current user from Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization.removeprefix("Bearer ")
    try:
        return decode_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(db: AsyncSession, authorization: str | None) -> User:
    """Get the current authenticated user from the database."""
    payload = get_current_user_payload(authorization)
    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def require_organizer(user: User, hackathon: Hackathon, db: AsyncSession):
    """Verify user is the organizer or a co-organizer of the hackathon."""
    if user.role == UserRole.organizer and hackathon.organizer_id == user.id:
        return
    result = await db.execute(
        select(HackathonOrganizer).where(
            HackathonOrganizer.hackathon_id == hackathon.id,
            HackathonOrganizer.user_id == user.id,
        )
    )
    if result.scalar_one_or_none():
        return
    raise HTTPException(status_code=403, detail="Only the hackathon organizer can perform this action")
