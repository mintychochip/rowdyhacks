"""Demo and pitch scheduling service.

Manages demo time slots for hackathon submissions, including auto-assignment
of teams to slots and judge panel tracking.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DemoSlot, Submission


class DemoScheduleService:
    """CRUD and assignment operations for hackathon demo slots."""

    async def create_slot(
        self,
        db: AsyncSession,
        hackathon_id,
        start_time,
        end_time,
        room: str | None = None,
        judge_panel_id: str | None = None,
    ) -> DemoSlot:
        """Create a new demo slot for a hackathon.

        Behavior:
        1. Build a DemoSlot instance.
        2. Add and commit.

        Raises: None
        Side Effects: Inserts DemoSlot row.
        Dependencies: app.models.DemoSlot.
        """
        slot = DemoSlot(
            hackathon_id=hackathon_id,
            start_time=start_time,
            end_time=end_time,
            room=room,
            judge_panel_id=judge_panel_id,
        )
        db.add(slot)
        await db.commit()
        await db.refresh(slot)
        return slot

    async def list_slots(self, db: AsyncSession, hackathon_id) -> list[DemoSlot]:
        """List demo slots for a hackathon ordered by start time.

        Behavior:
        1. Query DemoSlot rows filtered by hackathon_id.
        2. Order by start_time.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models.DemoSlot.
        """
        result = await db.execute(
            select(DemoSlot).where(DemoSlot.hackathon_id == hackathon_id).order_by(DemoSlot.start_time)
        )
        return list(result.scalars().all())

    async def auto_assign_submissions_to_slots(
        self,
        db: AsyncSession,
        hackathon_id,
    ) -> list[DemoSlot]:
        """Auto-assign unassigned submissions to empty demo slots.

        Behavior:
        1. Fetch all empty demo slots for the hackathon.
        2. Fetch all submissions for the hackathon without an assigned slot.
        3. Assign submissions to slots one by one.
        4. Commit changes.

        Raises: None
        Side Effects: Updates DemoSlot rows.
        Dependencies: app.models.DemoSlot, app.models.Submission.
        """
        slots_result = await db.execute(
            select(DemoSlot)
            .where(
                DemoSlot.hackathon_id == hackathon_id,
                DemoSlot.submission_id.is_(None),
            )
            .order_by(DemoSlot.start_time)
        )
        slots = list(slots_result.scalars().all())

        submissions_result = await db.execute(
            select(Submission).where(
                Submission.hackathon_id == hackathon_id,
                Submission.team_id.isnot(None),
            )
        )
        submissions = list(submissions_result.scalars().all())

        for slot, submission in zip(slots, submissions, strict=False):
            slot.submission_id = submission.id

        await db.commit()
        # Refresh all modified slots
        for slot in slots:
            await db.refresh(slot)
        return slots

    async def get_my_demo_slot(
        self,
        db: AsyncSession,
        hackathon_id,
        team_id,
    ) -> DemoSlot | None:
        """Get the demo slot assigned to a specific team.

        Behavior:
        1. Find the team's submission for the hackathon.
        2. Find the demo slot assigned to that submission.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models.DemoSlot, app.models.Submission.
        """
        result = await db.execute(
            select(Submission).where(
                Submission.hackathon_id == hackathon_id,
                Submission.team_id == team_id,
            )
        )
        submission = result.scalar_one_or_none()
        if not submission:
            return None

        slot_result = await db.execute(
            select(DemoSlot).where(
                DemoSlot.hackathon_id == hackathon_id,
                DemoSlot.submission_id == submission.id,
            )
        )
        return slot_result.scalar_one_or_none()
