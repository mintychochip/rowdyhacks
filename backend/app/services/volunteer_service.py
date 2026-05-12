"""Volunteer and staff management service.

Handles volunteer shift assignments and check-ins at hackathons.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserRole, VolunteerShift


class VolunteerService:
    """CRUD operations for volunteer shifts and check-ins."""

    async def add_volunteer(
        self,
        db: AsyncSession,
        hackathon_id,
        volunteer_id: str,
        shift_name: str,
        start_time,
        end_time,
        location: str | None = None,
    ) -> VolunteerShift:
        """Add a volunteer shift assignment.

        Behavior:
        1. Verify the user exists and has volunteer role.
        2. Create and persist VolunteerShift.

        Raises: ValueError if user not found or not a volunteer.
        Side Effects: Inserts VolunteerShift row.
        Dependencies: app.models.VolunteerShift, app.models.User, app.models.UserRole.
        """
        user_result = await db.execute(select(User).where(User.id == volunteer_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")
        if user.role != UserRole.volunteer:
            raise ValueError("User is not a volunteer")

        shift = VolunteerShift(
            hackathon_id=hackathon_id,
            volunteer_id=volunteer_id,
            shift_name=shift_name,
            start_time=start_time,
            end_time=end_time,
            location=location,
        )
        db.add(shift)
        await db.commit()
        await db.refresh(shift)
        return shift

    async def list_volunteers(self, db: AsyncSession, hackathon_id) -> list[VolunteerShift]:
        """List volunteer shifts for a hackathon.

        Behavior:
        1. Query VolunteerShift rows filtered by hackathon_id.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models.VolunteerShift.
        """
        result = await db.execute(select(VolunteerShift).where(VolunteerShift.hackathon_id == hackathon_id))
        return list(result.scalars().all())

    async def checkin_volunteer(
        self,
        db: AsyncSession,
        shift_id,
    ) -> VolunteerShift:
        """Check in a volunteer for their shift.

        Behavior:
        1. Load the shift by ID.
        2. Set checked_in_at to now.
        3. Commit and refresh.

        Raises: ValueError if shift not found.
        Side Effects: Updates VolunteerShift row.
        Dependencies: app.models.VolunteerShift.
        """
        result = await db.execute(select(VolunteerShift).where(VolunteerShift.id == shift_id))
        shift = result.scalar_one_or_none()
        if not shift:
            raise ValueError("Shift not found")
        shift.checked_in_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(shift)
        return shift

    async def list_my_shifts(
        self,
        db: AsyncSession,
        volunteer_id: str,
    ) -> list[VolunteerShift]:
        """List all shifts for a specific volunteer.

        Behavior:
        1. Query VolunteerShift rows filtered by volunteer_id.
        2. Order by start_time.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models.VolunteerShift.
        """
        result = await db.execute(
            select(VolunteerShift)
            .where(VolunteerShift.volunteer_id == volunteer_id)
            .order_by(VolunteerShift.start_time)
        )
        return list(result.scalars().all())
