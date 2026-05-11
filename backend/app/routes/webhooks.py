"""Webhook subscription and delivery routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import require_organizer
from app.database import get_db
from app.models import WebhookSubscription

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


class SubscribeRequest(BaseModel):
    url: str
    secret: str
    events: list[str]


class SubscriptionResponse(BaseModel):
    id: str
    url: str
    events: list[str]
    active: bool
    created_at: str


@router.post("/subscribe", response_model=SubscriptionResponse)
async def subscribe(
    body: SubscribeRequest,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_organizer),
):
    """Create a new webhook subscription (organizer only)."""
    sub = WebhookSubscription(
        url=body.url,
        secret=body.secret,
        events=body.events,
        active=True,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return {
        "id": str(sub.id),
        "url": sub.url,
        "events": sub.events or [],
        "active": sub.active,
        "created_at": sub.created_at.isoformat() if sub.created_at else "",
    }


@router.get("/subscriptions", response_model=list[SubscriptionResponse])
async def list_subscriptions(
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_organizer),
):
    """List all webhook subscriptions (organizer only)."""
    result = await db.execute(select(WebhookSubscription))
    subs = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "url": s.url,
            "events": s.events or [],
            "active": s.active,
            "created_at": s.created_at.isoformat() if s.created_at else "",
        }
        for s in subs
    ]


@router.delete("/subscriptions/{subscription_id}")
async def delete_subscription(
    subscription_id: str,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_organizer),
):
    """Delete a webhook subscription (organizer only)."""
    from uuid import UUID

    result = await db.execute(select(WebhookSubscription).where(WebhookSubscription.id == UUID(subscription_id)))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    await db.delete(sub)
    await db.commit()
    return {"deleted": subscription_id}
