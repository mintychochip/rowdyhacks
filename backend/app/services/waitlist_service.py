"""Waitlist management service.

Encapsulates all business logic for hackathon waitlist operations,
including promotion, position queries, and capacity checks.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.email_service import send_email
from app.models import Hackathon, Registration, RegistrationStatus, User


class WaitlistService:
    """Service for managing hackathon waitlists."""

    async def promote_from_waitlist(
        self,
        hackathon_id: uuid.UUID,
        db: AsyncSession,
    ) -> Registration | None:
        """Promote the top waitlisted registration to ``offered`` status.

        Behavior:
        1. Query waitlisted registrations ordered by declined_count ASC then registered_at ASC.
        2. Lock the hackathon row to prevent race conditions.
        3. Count currently accepted participants.
        4. If capacity is reached, return None.
        5. Otherwise, promote the top waitlisted registration to ``offered`` with a 24-hour expiry.
        6. Send a spot-offered email to the user.
        7. Commit the transaction and return the promoted registration.

        Raises: None (SQLAlchemy errors propagate).
        Side Effects: Updates a Registration row; sends an email; commits the DB transaction.
        Dependencies: app.models.Registration, app.models.Hackathon, app.email_service.send_email.
        Consumers: Background job scheduler and manual admin actions.
        """
        # Get top waitlisted (lower declined_count first, then FIFO)
        top_waitlisted = await db.execute(
            select(Registration)
            .where(Registration.hackathon_id == hackathon_id)
            .where(Registration.status == RegistrationStatus.waitlisted)
            .order_by(Registration.declined_count.asc(), Registration.registered_at.asc())
            .limit(1)
        )
        reg = top_waitlisted.scalar_one_or_none()
        if not reg:
            return None

        # Check capacity with row lock
        hackathon_result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id).with_for_update())
        hackathon = hackathon_result.scalar_one()

        accepted_count = await db.execute(
            select(func.count(Registration.id))
            .where(Registration.hackathon_id == hackathon_id)
            .where(Registration.status == RegistrationStatus.accepted)
        )
        if accepted_count.scalar() >= hackathon.max_participants:
            return None  # No spot available

        # Promote to offered
        now = datetime.now(UTC)
        reg.status = RegistrationStatus.offered
        reg.offered_at = now
        reg.offer_expires_at = now + timedelta(hours=24)
        await db.flush()

        # Send offer email
        user = await db.get(User, reg.user_id)
        if user:
            await send_email(
                to_email=user.email,
                email_type="spot_offered",
                context={
                    "name": user.name,
                    "hackathon_name": hackathon.name,
                    "deadline": reg.offer_expires_at.strftime("%Y-%m-%d %H:%M UTC"),
                    "accept_url": f"/dashboard?accept_offer={reg.id}",  # Frontend route
                },
                registration_id=reg.id,
                hackathon_id=hackathon_id,
                db=db,
            )

        await db.commit()
        return reg

    async def get_waitlist_position(
        self,
        registration_id: uuid.UUID,
        hackathon_id: uuid.UUID,
        db: AsyncSession,
    ) -> int | None:
        """Get the 1-indexed position of a registration in the waitlist.

        Behavior:
        1. Query all waitlisted registrations for the hackathon, ordered by priority.
        2. Iterate the list and return the 1-based index when the registration ID matches.
        3. Return None if the registration is not waitlisted.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models.Registration, app.models.RegistrationStatus, sqlalchemy.select.
        Consumers: GET /api/registrations/waitlist-position and user dashboard.
        """
        # Get all waitlisted registrations ordered by priority
        result = await db.execute(
            select(Registration)
            .where(Registration.hackathon_id == hackathon_id)
            .where(Registration.status == RegistrationStatus.waitlisted)
            .order_by(Registration.declined_count.asc(), Registration.registered_at.asc())
        )
        waitlisted = result.scalars().all()

        for idx, reg in enumerate(waitlisted, start=1):
            if reg.id == registration_id:
                return idx
        return None

    async def auto_waitlist_if_full(
        self,
        hackathon_id: uuid.UUID,
        db: AsyncSession,
    ) -> bool:
        """Check whether a hackathon has reached its participant capacity.

        Behavior:
        1. Load the hackathon record by ID.
        2. If the hackathon has no capacity limit, return False.
        3. Count accepted registrations for the hackathon.
        4. Return True if the count is greater than or equal to max_participants.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models.Hackathon, app.models.Registration, app.models.RegistrationStatus, sqlalchemy.func.count.
        Consumers: Registration creation route to decide between accepted and waitlisted status.
        """
        hackathon = await db.get(Hackathon, hackathon_id)
        if not hackathon or not hackathon.max_participants:
            return False

        accepted_count = await db.execute(
            select(func.count(Registration.id))
            .where(Registration.hackathon_id == hackathon_id)
            .where(Registration.status == RegistrationStatus.accepted)
        )
        return accepted_count.scalar() >= hackathon.max_participants
