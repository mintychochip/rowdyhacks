"""Workshop and schedule management service.

Provides CRUD operations for hackathon workshops, including scheduling
with start/end times, speaker information, and location tracking.
Also manages participant RSVPs and attendance.
"""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Workshop, WorkshopRSVP, WorkshopRSVPStatus


class WorkshopService:
    """CRUD operations for workshops within a hackathon.

    Supports creating scheduled events, listing them in chronological order,
    updating fields, deleting workshops, and managing RSVPs.
    """

    async def create_workshop(
        self,
        db: AsyncSession,
        hackathon_id,
        title: str,
        description: str | None = None,
        start_time=None,
        end_time=None,
        location: str | None = None,
        speaker_name: str | None = None,
        max_capacity: int | None = None,
    ) -> Workshop:
        """Create a new workshop for a hackathon.

        Behavior:
        1. Build a Workshop instance with the provided fields.
        2. Add it to the database session.
        3. Commit and refresh.

        Raises: None
        Side Effects: Inserts Workshop row.
        Dependencies: app.models.Workshop.
        Consumers: Workshop creation endpoints.
        """
        workshop = Workshop(
            hackathon_id=hackathon_id,
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            location=location,
            speaker_name=speaker_name,
            max_capacity=max_capacity,
        )
        db.add(workshop)
        await db.commit()
        await db.refresh(workshop)
        return workshop

    async def list_workshops(self, db: AsyncSession, hackathon_id) -> list[Workshop]:
        """List workshops for a hackathon ordered by start time.

        Behavior:
        1. Query Workshop rows filtered by hackathon_id.
        2. Order results by start_time.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models.Workshop.
        Consumers: Workshop listing endpoints.
        """
        result = await db.execute(
            select(Workshop).where(Workshop.hackathon_id == hackathon_id).order_by(Workshop.start_time)
        )
        return list(result.scalars().all())

    async def get_workshop(self, db: AsyncSession, workshop_id) -> Workshop | None:
        """Get a single workshop by ID.

        Behavior:
        1. Query the Workshop row by ID.
        2. Return the instance or None.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models.Workshop.
        Consumers: Workshop detail and update endpoints.
        """
        result = await db.execute(select(Workshop).where(Workshop.id == workshop_id))
        return result.scalar_one_or_none()

    async def update_workshop(
        self,
        db: AsyncSession,
        workshop_id,
        title: str | None = None,
        description: str | None = None,
        start_time=None,
        end_time=None,
        location: str | None = None,
        speaker_name: str | None = None,
        max_capacity: int | None = None,
    ) -> Workshop:
        """Update workshop fields.

        Behavior:
        1. Load the workshop by ID.
        2. Raise ValueError if not found.
        3. Apply each provided (non-None) field.
        4. Commit and refresh.

        Raises: ValueError if the workshop does not exist.
        Side Effects: Updates Workshop row.
        Dependencies: WorkshopService.get_workshop.
        Consumers: Workshop update endpoints.
        """
        workshop = await self.get_workshop(db, workshop_id)
        if not workshop:
            raise ValueError("Workshop not found")

        if title is not None:
            workshop.title = title
        if description is not None:
            workshop.description = description
        if start_time is not None:
            workshop.start_time = start_time
        if end_time is not None:
            workshop.end_time = end_time
        if location is not None:
            workshop.location = location
        if speaker_name is not None:
            workshop.speaker_name = speaker_name
        if max_capacity is not None:
            workshop.max_capacity = max_capacity

        await db.commit()
        await db.refresh(workshop)
        return workshop

    async def delete_workshop(self, db: AsyncSession, workshop_id) -> None:
        """Delete a workshop.

        Behavior:
        1. Load the workshop by ID.
        2. Raise ValueError if not found.
        3. Delete the row and commit.

        Raises: ValueError if the workshop does not exist.
        Side Effects: Deletes Workshop row.
        Dependencies: WorkshopService.get_workshop.
        Consumers: Workshop deletion endpoints.
        """
        workshop = await self.get_workshop(db, workshop_id)
        if not workshop:
            raise ValueError("Workshop not found")
        await db.delete(workshop)
        await db.commit()

    # --- RSVP methods ---

    async def register_for_workshop(
        self,
        db: AsyncSession,
        workshop_id,
        user_id: str,
        hackathon_id,
    ) -> WorkshopRSVP:
        """Register a user for a workshop.

        Behavior:
        1. Verify the workshop exists.
        2. Check capacity if max_capacity is set.
        3. Check for existing non-cancelled RSVP.
        4. Create and persist a new WorkshopRSVP.

        Raises:
            ValueError if workshop not found, at capacity, or already registered.
        Side Effects: Inserts WorkshopRSVP row.
        Dependencies: WorkshopService.get_workshop.
        Consumers: POST /api/workshops/{workshop_id}/rsvp.
        """
        workshop = await self.get_workshop(db, workshop_id)
        if not workshop:
            raise ValueError("Workshop not found")

        if workshop.hackathon_id != hackathon_id:
            raise ValueError("Workshop does not belong to this hackathon")

        existing = await db.execute(
            select(WorkshopRSVP).where(
                WorkshopRSVP.workshop_id == workshop_id,
                WorkshopRSVP.user_id == user_id,
                WorkshopRSVP.status != WorkshopRSVPStatus.cancelled,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Already registered for this workshop")

        if workshop.max_capacity is not None:
            count_result = await db.execute(
                select(func.count(WorkshopRSVP.id)).where(
                    WorkshopRSVP.workshop_id == workshop_id,
                    WorkshopRSVP.status == WorkshopRSVPStatus.registered,
                )
            )
            current_count = count_result.scalar() or 0
            if current_count >= workshop.max_capacity:
                raise ValueError("Workshop is at capacity")

        rsvp = WorkshopRSVP(
            user_id=user_id,
            workshop_id=workshop_id,
            hackathon_id=hackathon_id,
            status=WorkshopRSVPStatus.registered,
        )
        db.add(rsvp)
        await db.commit()
        await db.refresh(rsvp)
        return rsvp

    async def cancel_rsvp(
        self,
        db: AsyncSession,
        workshop_id,
        user_id: str,
    ) -> WorkshopRSVP:
        """Cancel a user's RSVP for a workshop.

        Behavior:
        1. Find the active RSVP for the user and workshop.
        2. Set status to cancelled.
        3. Commit and refresh.

        Raises: ValueError if RSVP not found.
        Side Effects: Updates WorkshopRSVP row.
        Dependencies: app.models.WorkshopRSVP.
        Consumers: DELETE /api/workshops/{workshop_id}/rsvp.
        """
        result = await db.execute(
            select(WorkshopRSVP).where(
                WorkshopRSVP.workshop_id == workshop_id,
                WorkshopRSVP.user_id == user_id,
                WorkshopRSVP.status != WorkshopRSVPStatus.cancelled,
            )
        )
        rsvp = result.scalar_one_or_none()
        if not rsvp:
            raise ValueError("RSVP not found")

        rsvp.status = WorkshopRSVPStatus.cancelled
        await db.commit()
        await db.refresh(rsvp)
        return rsvp

    async def mark_attended(
        self,
        db: AsyncSession,
        workshop_id,
        user_id: str,
    ) -> WorkshopRSVP:
        """Mark a user's RSVP as attended.

        Behavior:
        1. Find the active RSVP for the user and workshop.
        2. Set status to attended and attended_at to now.
        3. Commit and refresh.

        Raises: ValueError if RSVP not found.
        Side Effects: Updates WorkshopRSVP row.
        Dependencies: app.models.WorkshopRSVP.
        Consumers: POST /api/workshops/{workshop_id}/rsvp/{user_id}/attended.
        """
        result = await db.execute(
            select(WorkshopRSVP).where(
                WorkshopRSVP.workshop_id == workshop_id,
                WorkshopRSVP.user_id == user_id,
                WorkshopRSVP.status != WorkshopRSVPStatus.cancelled,
            )
        )
        rsvp = result.scalar_one_or_none()
        if not rsvp:
            raise ValueError("RSVP not found")

        rsvp.status = WorkshopRSVPStatus.attended
        rsvp.attended_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(rsvp)
        return rsvp

    async def list_rsvps_for_workshop(
        self,
        db: AsyncSession,
        workshop_id,
    ) -> list[WorkshopRSVP]:
        """List all non-cancelled RSVPs for a workshop.

        Behavior:
        1. Query WorkshopRSVP rows filtered by workshop_id.
        2. Exclude cancelled entries.
        3. Order by registered_at.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models.WorkshopRSVP.
        Consumers: GET /api/workshops/{workshop_id}/rsvps.
        """
        result = await db.execute(
            select(WorkshopRSVP)
            .where(
                WorkshopRSVP.workshop_id == workshop_id,
                WorkshopRSVP.status != WorkshopRSVPStatus.cancelled,
            )
            .order_by(WorkshopRSVP.registered_at)
        )
        return list(result.scalars().all())

    async def list_rsvps_for_user(
        self,
        db: AsyncSession,
        user_id: str,
        hackathon_id,
    ) -> list[WorkshopRSVP]:
        """List a user's non-cancelled RSVPs for a hackathon.

        Behavior:
        1. Query WorkshopRSVP rows filtered by user_id and hackathon_id.
        2. Exclude cancelled entries.
        3. Order by registered_at.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models.WorkshopRSVP.
        Consumers: GET /api/hackathons/{hackathon_id}/my-rsvps.
        """
        result = await db.execute(
            select(WorkshopRSVP)
            .where(
                WorkshopRSVP.user_id == user_id,
                WorkshopRSVP.hackathon_id == hackathon_id,
                WorkshopRSVP.status != WorkshopRSVPStatus.cancelled,
            )
            .order_by(WorkshopRSVP.registered_at)
        )
        return list(result.scalars().all())

    async def get_workshop_capacity_status(
        self,
        db: AsyncSession,
        workshop_id,
    ) -> dict:
        """Return capacity info for a workshop.

        Behavior:
        1. Query the workshop by ID.
        2. Count active (registered + attended) RSVPs.
        3. Return max_capacity, current_count, and available spots.

        Raises: ValueError if workshop not found.
        Side Effects: None (read-only).
        Dependencies: WorkshopService.get_workshop.
        Consumers: Workshop detail views.
        """
        workshop = await self.get_workshop(db, workshop_id)
        if not workshop:
            raise ValueError("Workshop not found")

        count_result = await db.execute(
            select(func.count(WorkshopRSVP.id)).where(
                WorkshopRSVP.workshop_id == workshop_id,
                WorkshopRSVP.status.in_([WorkshopRSVPStatus.registered, WorkshopRSVPStatus.attended]),
            )
        )
        current_count = count_result.scalar() or 0
        max_capacity = workshop.max_capacity
        available = None if max_capacity is None else max(0, max_capacity - current_count)
        return {
            "max_capacity": max_capacity,
            "current_count": current_count,
            "available": available,
            "is_full": max_capacity is not None and current_count >= max_capacity,
        }
