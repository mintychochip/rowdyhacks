"""In-app notification service with read tracking and broadcast capabilities.

Provides CRUD operations for user-scoped notifications, including bulk
mark-read, unread counts, and organizer broadcasts to hackathon participants.
"""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification, NotificationType, Registration, RegistrationStatus


class NotificationService:
    """Service for creating, reading, and broadcasting in-app notifications.

    Notifications are always scoped to a specific user. Broadcast helpers
    create individual rows for every target user so that read tracking is
    per-user and deletions are isolated.
    """

    async def create_notification(
        self,
        db: AsyncSession,
        user_id: str,
        title: str,
        message: str,
        type: NotificationType = NotificationType.info,
        hackathon_id=None,
        action_url: str | None = None,
        action_text: str | None = None,
    ) -> Notification:
        """Create a single notification for a user.

        Behavior:
        1. Build a Notification instance with the provided fields.
        2. Add it to the session, commit, and refresh.
        3. Return the persisted notification.

        Raises: None
        Side Effects: Inserts a Notification row.
        Dependencies: app.models.Notification.
        Consumers: POST /api/notifications (internal), broadcast helpers.
        """
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=type,
            hackathon_id=hackathon_id,
            action_url=action_url,
            action_text=action_text,
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        return notification

    async def mark_as_read(self, db: AsyncSession, notification_id, user_id: str) -> Notification:
        """Mark a specific notification as read, verifying ownership.

        Behavior:
        1. Load the notification by ID.
        2. Raise ValueError if it does not exist or belongs to another user.
        3. Set read_at to the current UTC time if not already set.
        4. Commit and refresh.

        Raises: ValueError if the notification is not found or not owned by the user.
        Side Effects: Updates Notification.read_at.
        Dependencies: app.models.Notification.
        Consumers: POST /api/notifications/{id}/read.
        """
        result = await db.execute(select(Notification).where(Notification.id == notification_id))
        notification = result.scalar_one_or_none()
        if not notification:
            raise ValueError("Notification not found")
        if notification.user_id != user_id:
            raise ValueError("Notification not found")

        if notification.read_at is None:
            notification.read_at = datetime.now(UTC)
            await db.commit()
            await db.refresh(notification)

        return notification

    async def mark_all_as_read(self, db: AsyncSession, user_id: str, hackathon_id=None) -> int:
        """Mark all unread notifications for a user as read.

        Behavior:
        1. Update all Notification rows for the user where read_at is None.
        2. Optionally restrict to a specific hackathon when hackathon_id is provided.
        3. Return the number of rows updated.

        Raises: None
        Side Effects: Updates Notification.read_at for matching rows.
        Dependencies: app.models.Notification, sqlalchemy.select.
        Consumers: POST /api/notifications/read-all.
        """
        from sqlalchemy import update

        stmt = (
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
            .values(read_at=datetime.now(UTC))
            .execution_options(synchronize_session="fetch")
        )
        if hackathon_id is not None:
            stmt = stmt.where(Notification.hackathon_id == hackathon_id)

        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

    async def get_unread_count(self, db: AsyncSession, user_id: str, hackathon_id=None) -> int:
        """Count unread notifications for a user.

        Behavior:
        1. Execute a SELECT count(*) for notifications where read_at is None.
        2. Optionally filter by hackathon_id.
        3. Return the count.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models.Notification, sqlalchemy.func.count.
        Consumers: GET /api/notifications/unread-count.
        """
        stmt = select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
        )
        if hackathon_id is not None:
            stmt = stmt.where(Notification.hackathon_id == hackathon_id)

        result = await db.execute(stmt)
        return result.scalar_one() or 0

    async def list_notifications(
        self,
        db: AsyncSession,
        user_id: str,
        hackathon_id=None,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Notification]:
        """List notifications for a user with optional filters and pagination.

        Behavior:
        1. Build a SELECT for Notification rows filtered by user_id.
        2. Optionally restrict by hackathon_id or unread_only.
        3. Order by created_at descending (newest first).
        4. Apply limit and offset for pagination.
        5. Return the list of notifications.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models.Notification, sqlalchemy.select.
        Consumers: GET /api/notifications.
        """
        stmt = select(Notification).where(Notification.user_id == user_id)
        if hackathon_id is not None:
            stmt = stmt.where(Notification.hackathon_id == hackathon_id)
        if unread_only:
            stmt = stmt.where(Notification.read_at.is_(None))

        stmt = stmt.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def delete_notification(self, db: AsyncSession, notification_id, user_id: str) -> None:
        """Delete a notification, verifying ownership.

        Behavior:
        1. Load the notification by ID.
        2. Raise ValueError if it does not exist or belongs to another user.
        3. Delete the row and commit.

        Raises: ValueError if the notification is not found or not owned by the user.
        Side Effects: Deletes a Notification row.
        Dependencies: app.models.Notification.
        Consumers: DELETE /api/notifications/{id}.
        """
        result = await db.execute(select(Notification).where(Notification.id == notification_id))
        notification = result.scalar_one_or_none()
        if not notification:
            raise ValueError("Notification not found")
        if notification.user_id != user_id:
            raise ValueError("Notification not found")

        await db.delete(notification)
        await db.commit()

    async def broadcast_to_hackathon(
        self,
        db: AsyncSession,
        hackathon_id,
        title: str,
        message: str,
        type: NotificationType = NotificationType.info,
        action_url: str | None = None,
        action_text: str | None = None,
    ) -> int:
        """Create a notification for every accepted registrant of a hackathon.

        Behavior:
        1. Query all accepted Registration rows for the hackathon.
        2. For each registrant, create a Notification row.
        3. Commit once in bulk.
        4. Return the number of notifications created.

        Raises: None
        Side Effects: Inserts many Notification rows.
        Dependencies: app.models.Notification, app.models.Registration, app.models.RegistrationStatus.
        Consumers: POST /api/hackathons/{id}/notifications/broadcast.
        """
        result = await db.execute(
            select(Registration.user_id).where(
                Registration.hackathon_id == hackathon_id,
                Registration.status == RegistrationStatus.accepted,
            )
        )
        user_ids = [row[0] for row in result.all()]

        for uid in user_ids:
            db.add(
                Notification(
                    user_id=uid,
                    hackathon_id=hackathon_id,
                    title=title,
                    message=message,
                    type=type,
                    action_url=action_url,
                    action_text=action_text,
                )
            )

        await db.commit()
        return len(user_ids)

    async def broadcast_to_registrants(
        self,
        db: AsyncSession,
        hackathon_id,
        title: str,
        message: str,
        type: NotificationType = NotificationType.info,
        action_url: str | None = None,
        action_text: str | None = None,
    ) -> int:
        """Alias for broadcast_to_hackathon that targets accepted registrants.

        Behavior:
        1. Delegate directly to broadcast_to_hackathon.

        Raises: None
        Side Effects: Same as broadcast_to_hackathon.
        Dependencies: NotificationService.broadcast_to_hackathon.
        Consumers: Organizer broadcast UI.
        """
        return await self.broadcast_to_hackathon(
            db,
            hackathon_id,
            title,
            message,
            type,
            action_url,
            action_text,
        )
