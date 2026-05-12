"""Notification management routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import require_clerk_user, require_hackathon_organizer
from app.database import get_db
from app.models import NotificationType
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

hackathon_router = APIRouter(prefix="/api/hackathons", tags=["hackathons"])


class BroadcastNotificationRequest(BaseModel):
    """Request body for broadcasting a notification to hackathon participants.

    Attributes:
        title: Short headline of the notification.
        message: Body text of the notification.
        type: Severity level (info, success, warning, error). Defaults to info.
        action_url: Optional URL to open when the user clicks the action button.
        action_text: Optional label for the action button.
    """

    title: str
    message: str
    type: NotificationType = NotificationType.info
    action_url: str | None = None
    action_text: str | None = None


@router.get("")
async def list_notifications(
    hackathon_id: str | None = Query(default=None),
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """List notifications for the current user.

    Behavior:
    1. Instantiate NotificationService and list notifications for the authenticated user.
    2. Optionally filter by hackathon_id or unread_only.
    3. Return a paginated list of serialized notification dicts.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.services.notification_service.NotificationService.
    Consumers: GET /api/notifications, notification inbox UI.
    """
    service = NotificationService()
    notifications = await service.list_notifications(
        db,
        user_id=user_payload["sub"],
        hackathon_id=UUID(hackathon_id) if hackathon_id else None,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )

    return [
        {
            "id": str(n.id),
            "user_id": n.user_id,
            "hackathon_id": str(n.hackathon_id) if n.hackathon_id else None,
            "title": n.title,
            "message": n.message,
            "type": n.type.value,
            "read_at": n.read_at.isoformat() if n.read_at else None,
            "created_at": n.created_at.isoformat() if n.created_at else None,
            "action_url": n.action_url,
            "action_text": n.action_text,
        }
        for n in notifications
    ]


@router.post("/{notification_id}/read")
async def mark_as_read(
    notification_id: str,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a notification as read.

    Behavior:
    1. Instantiate NotificationService and mark the notification as read.
    2. Return 404 if the notification does not exist or is not owned by the user.
    3. Return the serialized notification with read_at set.

    Raises: HTTPException(404) if the notification is not found or not owned.
    Side Effects: Updates Notification.read_at.
    Dependencies: app.services.notification_service.NotificationService.
    Consumers: POST /api/notifications/{id}/read, notification click handler.
    """
    service = NotificationService()
    try:
        notification = await service.mark_as_read(db, UUID(notification_id), user_payload["sub"])
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return {
        "id": str(notification.id),
        "read_at": notification.read_at.isoformat() if notification.read_at else None,
    }


@router.post("/read-all")
async def mark_all_as_read(
    hackathon_id: str | None = Query(default=None),
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all notifications for the current user as read.

    Behavior:
    1. Instantiate NotificationService and mark all unread notifications as read.
    2. Optionally restrict to a specific hackathon.
    3. Return the number of notifications marked as read.

    Raises: None
    Side Effects: Updates Notification.read_at for matching rows.
    Dependencies: app.services.notification_service.NotificationService.
    Consumers: POST /api/notifications/read-all, mark-all-read button.
    """
    service = NotificationService()
    count = await service.mark_all_as_read(
        db,
        user_id=user_payload["sub"],
        hackathon_id=UUID(hackathon_id) if hackathon_id else None,
    )
    return {"marked_as_read": count}


@router.get("/unread-count")
async def get_unread_count(
    hackathon_id: str | None = Query(default=None),
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the number of unread notifications for the current user.

    Behavior:
    1. Instantiate NotificationService and count unread notifications.
    2. Optionally restrict to a specific hackathon.
    3. Return the count.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.services.notification_service.NotificationService.
    Consumers: GET /api/notifications/unread-count, notification badge.
    """
    service = NotificationService()
    count = await service.get_unread_count(
        db,
        user_id=user_payload["sub"],
        hackathon_id=UUID(hackathon_id) if hackathon_id else None,
    )
    return {"unread_count": count}


@router.delete("/{notification_id}", status_code=204)
async def delete_notification(
    notification_id: str,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a notification.

    Behavior:
    1. Instantiate NotificationService and delete the notification.
    2. Return 404 if the notification does not exist or is not owned by the user.
    3. Return empty 204 response on success.

    Raises: HTTPException(404) if the notification is not found or not owned.
    Side Effects: Deletes a Notification row.
    Dependencies: app.services.notification_service.NotificationService.
    Consumers: DELETE /api/notifications/{id}, notification dismissal.
    """
    service = NotificationService()
    try:
        await service.delete_notification(db, UUID(notification_id), user_payload["sub"])
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return None


@hackathon_router.post("/{hackathon_id}/notifications/broadcast")
async def broadcast_to_hackathon(
    hackathon_id: UUID,
    body: BroadcastNotificationRequest,
    auth: dict = Depends(require_hackathon_organizer),
    db: AsyncSession = Depends(get_db),
):
    """Broadcast a notification to all accepted registrants of a hackathon.

    Behavior:
    1. Instantiate NotificationService and broadcast to all accepted registrants.
    2. Return the number of notifications created.

    Raises: HTTPException(403) if the user is not an organizer for the hackathon.
    Side Effects: Inserts many Notification rows.
    Dependencies: app.services.notification_service.NotificationService, app.clerk_auth.require_hackathon_organizer.
    Consumers: POST /api/hackathons/{id}/notifications/broadcast, organizer broadcast panel.
    """
    service = NotificationService()
    count = await service.broadcast_to_hackathon(
        db,
        hackathon_id=hackathon_id,
        title=body.title,
        message=body.message,
        type=body.type,
        action_url=body.action_url,
        action_text=body.action_text,
    )
    return {"broadcast_count": count}
