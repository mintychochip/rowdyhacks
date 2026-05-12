"""Meal management service.

Handles meal slot creation, RSVP tracking, and attendance lists.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MealRSVP, MealSlot


class MealService:
    """CRUD operations for meal slots and participant RSVPs."""

    async def create_meal_slot(
        self,
        db: AsyncSession,
        hackathon_id,
        meal_type: str,
        start_time,
        end_time,
        location: str | None = None,
        max_capacity: int | None = None,
    ) -> MealSlot:
        """Create a new meal slot for a hackathon.

        Behavior:
        1. Build a MealSlot instance.
        2. Add and commit.

        Raises: None
        Side Effects: Inserts MealSlot row.
        Dependencies: app.models.MealSlot.
        """
        slot = MealSlot(
            hackathon_id=hackathon_id,
            meal_type=meal_type,
            start_time=start_time,
            end_time=end_time,
            location=location,
            max_capacity=max_capacity,
        )
        db.add(slot)
        await db.commit()
        await db.refresh(slot)
        return slot

    async def list_meal_slots(self, db: AsyncSession, hackathon_id) -> list[MealSlot]:
        """List meal slots for a hackathon ordered by start time.

        Behavior:
        1. Query MealSlot rows filtered by hackathon_id.
        2. Order by start_time.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models.MealSlot.
        """
        result = await db.execute(
            select(MealSlot).where(MealSlot.hackathon_id == hackathon_id).order_by(MealSlot.start_time)
        )
        return list(result.scalars().all())

    async def rsvp_for_meal(
        self,
        db: AsyncSession,
        meal_slot_id,
        user_id: str,
        dietary_restrictions: str | None = None,
    ) -> MealRSVP:
        """RSVP a user for a meal slot.

        Behavior:
        1. Verify the meal slot exists.
        2. Check for existing RSVP.
        3. Check capacity if set.
        4. Create and persist MealRSVP.

        Raises: ValueError if slot not found, already RSVP'd, or at capacity.
        Side Effects: Inserts MealRSVP row.
        Dependencies: app.models.MealSlot, app.models.MealRSVP.
        """
        slot_result = await db.execute(select(MealSlot).where(MealSlot.id == meal_slot_id))
        slot = slot_result.scalar_one_or_none()
        if not slot:
            raise ValueError("Meal slot not found")

        existing = await db.execute(
            select(MealRSVP).where(
                MealRSVP.meal_slot_id == meal_slot_id,
                MealRSVP.user_id == user_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Already RSVP'd for this meal")

        if slot.max_capacity is not None:
            count_result = await db.execute(
                select(func.count(MealRSVP.id)).where(MealRSVP.meal_slot_id == meal_slot_id)
            )
            current_count = count_result.scalar() or 0
            if current_count >= slot.max_capacity:
                raise ValueError("Meal slot is at capacity")

        rsvp = MealRSVP(
            meal_slot_id=meal_slot_id,
            user_id=user_id,
            dietary_restrictions=dietary_restrictions,
        )
        db.add(rsvp)
        await db.commit()
        await db.refresh(rsvp)
        return rsvp

    async def list_attendance(self, db: AsyncSession, meal_slot_id) -> list[MealRSVP]:
        """List all RSVPs for a meal slot.

        Behavior:
        1. Query MealRSVP rows filtered by meal_slot_id.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models.MealRSVP.
        """
        result = await db.execute(select(MealRSVP).where(MealRSVP.meal_slot_id == meal_slot_id))
        return list(result.scalars().all())
