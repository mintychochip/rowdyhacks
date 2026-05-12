"""Announcement management service.

Provides CRUD operations for hackathon announcements, including event
publishing when new announcements are created.
"""

import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Announcement


class AnnouncementService:
    """Service for creating and listing hackathon announcements."""

    async def create_announcement(
        self,
        db: AsyncSession,
        hackathon_id: uuid.UUID,
        sent_by: str,
        title: str,
        content: str,
        priority: str = "normal",
    ) -> Announcement:
        """Create an announcement and publish a notification event.

        Behavior:
        1. Build an Announcement record from the provided fields.
        2. Persist and refresh the record.
        3. Publish an ``announcement.published`` event.
        4. Return the created Announcement.

        Raises: None.
        Side Effects: Inserts Announcement row; publishes event.
        Dependencies: app.models.Announcement, app.services.event_service.publish_event.
        """
        announcement = Announcement(
            hackathon_id=hackathon_id,
            title=title,
            content=content,
            priority=priority,
            sent_by=sent_by,
        )
        db.add(announcement)
        await db.commit()
        await db.refresh(announcement)

        from app.services.event_service import publish_event

        await publish_event(
            db,
            "announcement.published",
            {
                "announcement_id": str(announcement.id),
                "hackathon_id": str(hackathon_id),
                "title": announcement.title,
            },
        )

        return announcement

    async def list_announcements(
        self,
        db: AsyncSession,
        hackathon_id: uuid.UUID,
        is_organizer: bool,
    ) -> list[Announcement]:
        """List announcements for a hackathon with role-based filtering.

        Behavior:
        1. Build a query filtered by hackathon_id.
        2. Exclude draft announcements for non-organizers.
        3. Order by sent_at descending and return.

        Raises: None.
        Side Effects: None (read-only).
        Dependencies: app.models.Announcement, sqlalchemy.select.
        """
        query = select(Announcement).where(Announcement.hackathon_id == hackathon_id)

        if not is_organizer:
            query = query.where(Announcement.priority != "draft")

        query = query.order_by(desc(Announcement.sent_at))

        result = await db.execute(query)
        return result.scalars().all()
