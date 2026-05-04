"""Notification preferences routes."""

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import NotificationPreference
from app.routes.deps import get_current_user

router = APIRouter(prefix="/api", tags=["notifications"])


class NotificationPrefsUpdate(BaseModel):
    channel: str | None = None
    registration_updates: bool | None = None
    announcements: bool | None = None
    judging_updates: bool | None = None
    team_requests: bool | None = None
    mentor_requests: bool | None = None


def _pref_to_dict(p: NotificationPreference) -> dict:
    return {
        "id": str(p.id),
        "channel": p.channel,
        "registration_updates": p.registration_updates,
        "announcements": p.announcements,
        "judging_updates": p.judging_updates,
        "team_requests": p.team_requests,
        "mentor_requests": p.mentor_requests,
    }


@router.get("/me/notifications")
async def get_notification_prefs(
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's notification preferences."""
    user = await get_current_user(db, authorization)
    result = await db.execute(select(NotificationPreference).where(NotificationPreference.user_id == user.id))
    pref = result.scalar_one_or_none()
    if not pref:
        pref = NotificationPreference(user_id=user.id)
        db.add(pref)
        await db.commit()
        await db.refresh(pref)
    return _pref_to_dict(pref)


@router.patch("/me/notifications")
async def update_notification_prefs(
    body: NotificationPrefsUpdate,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's notification preferences."""
    user = await get_current_user(db, authorization)
    result = await db.execute(select(NotificationPreference).where(NotificationPreference.user_id == user.id))
    pref = result.scalar_one_or_none()
    if not pref:
        pref = NotificationPreference(user_id=user.id)
        db.add(pref)
        await db.flush()

    if body.channel is not None:
        if body.channel not in ("email", "discord", "none"):
            from fastapi import HTTPException

            raise HTTPException(status_code=422, detail="channel must be 'email', 'discord', or 'none'")
        pref.channel = body.channel
    if body.registration_updates is not None:
        pref.registration_updates = body.registration_updates
    if body.announcements is not None:
        pref.announcements = body.announcements
    if body.judging_updates is not None:
        pref.judging_updates = body.judging_updates
    if body.team_requests is not None:
        pref.team_requests = body.team_requests
    if body.mentor_requests is not None:
        pref.mentor_requests = body.mentor_requests

    await db.commit()
    await db.refresh(pref)
    return _pref_to_dict(pref)
