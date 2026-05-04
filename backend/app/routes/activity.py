"""Live activity feed routes."""

import uuid

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ActivityEvent
from app.routes.deps import get_current_user
from app.websocket import hackathon_room, manager

router = APIRouter(prefix="/api/hackathons", tags=["activity"])


def _event_to_dict(e: ActivityEvent) -> dict:
    return {
        "id": str(e.id),
        "hackathon_id": str(e.hackathon_id),
        "event_type": e.event_type,
        "title": e.title,
        "detail": e.detail,
        "actor_id": str(e.actor_id) if e.actor_id else None,
        "created_at": e.created_at.isoformat(),
    }


@router.get("/{hackathon_id}/activity")
async def list_activity(
    hackathon_id: uuid.UUID,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    event_type: str | None = Query(default=None),
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """List recent activity events for a hackathon."""
    await get_current_user(db, authorization)
    query = select(ActivityEvent).where(ActivityEvent.hackathon_id == hackathon_id)
    if event_type:
        query = query.where(ActivityEvent.event_type == event_type)
    query = query.order_by(desc(ActivityEvent.created_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    events = result.scalars().all()
    return {"events": [_event_to_dict(e) for e in events]}


async def emit_activity(
    db: AsyncSession,
    hackathon_id: uuid.UUID,
    event_type: str,
    title: str,
    detail: str | None = None,
    actor_id: uuid.UUID | None = None,
):
    """Create an activity event and broadcast via WebSocket."""
    event = ActivityEvent(
        hackathon_id=hackathon_id,
        event_type=event_type,
        title=title,
        detail=detail,
        actor_id=actor_id,
    )
    db.add(event)
    await db.flush()

    await manager.broadcast_to_room(
        hackathon_room(str(hackathon_id)),
        {
            "type": "activity",
            "event": _event_to_dict(event),
        },
    )
