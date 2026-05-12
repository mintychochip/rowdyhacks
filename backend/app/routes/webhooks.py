"""Webhook subscription and delivery routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_organizer
from app.database import get_db
from app.models import User, WebhookSubscription

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


class SubscribeRequest(BaseModel):
    """Request body for creating a webhook subscription.

    Behavior:
    1. Define the schema for a webhook subscription request.
    2. Provide url, secret, and events fields.

    Side Effects: None (schema definition).
    Dependencies: pydantic.BaseModel.
    Consumers: POST /api/webhooks/subscribe, subscription creation.
    """

    url: str
    secret: str
    events: list[str]


class SubscriptionResponse(BaseModel):
    """Response schema for a webhook subscription.

    Behavior:
    1. Define the schema for a webhook subscription response.
    2. Provide id, url, events, active, and created_at fields.

    Side Effects: None (schema definition).
    Dependencies: pydantic.BaseModel.
    Consumers: GET /api/webhooks/subscriptions, subscription listing.
    """

    id: str
    url: str
    events: list[str]
    active: bool
    created_at: str


@router.post("/subscribe", response_model=SubscriptionResponse)
async def subscribe(
    body: SubscribeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_organizer),
):
    """Create a new webhook subscription (organizer only).

    Behavior:
    1. Build a WebhookSubscription from the request body.
    2. Persist the subscription to the database.
    3. Refresh and return the created subscription.

    Side Effects: Inserts WebhookSubscription row.
    Dependencies: app.models.WebhookSubscription, app.auth.require_organizer.
    Consumers: POST /api/webhooks/subscribe, organizer dashboard.
    """
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
    current_user: User = Depends(require_organizer),
):
    """List all webhook subscriptions (organizer only).

    Behavior:
    1. Query all WebhookSubscription rows from the database.
    2. Serialize each row to a SubscriptionResponse dict.
    3. Return the full list.

    Side Effects: None (read-only).
    Dependencies: app.models.WebhookSubscription, app.auth.require_organizer.
    Consumers: GET /api/webhooks/subscriptions, organizer dashboard.
    """
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
    current_user: User = Depends(require_organizer),
):
    """Delete a webhook subscription (organizer only).

    Behavior:
    1. Load the subscription by UUID.
    2. Raise 404 if the subscription does not exist.
    3. Delete the row and commit.

    Raises: HTTPException(404) if subscription not found.
    Side Effects: Deletes WebhookSubscription row.
    Dependencies: app.models.WebhookSubscription, app.auth.require_organizer.
    Consumers: DELETE /api/webhooks/subscriptions/{subscription_id}, organizer dashboard.
    """
    from uuid import UUID

    result = await db.execute(select(WebhookSubscription).where(WebhookSubscription.id == UUID(subscription_id)))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    await db.delete(sub)
    await db.commit()
    return {"deleted": subscription_id}
