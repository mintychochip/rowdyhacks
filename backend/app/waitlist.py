"""Waitlist management logic."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Registration, RegistrationStatus, Hackathon, User
from app.email_service import send_email


async def promote_from_waitlist(
    hackathon_id: uuid.UUID,
    db: AsyncSession
) -> Optional[Registration]:
    """
    Promote the top waitlisted registration to 'offered' status.
    Orders by: declined_count ASC (fewer declines = higher priority), then registered_at ASC (FIFO).
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
    hackathon_result = await db.execute(
        select(Hackathon)
        .where(Hackathon.id == hackathon_id)
        .with_for_update()
    )
    hackathon = hackathon_result.scalar_one()

    accepted_count = await db.execute(
        select(func.count(Registration.id))
        .where(Registration.hackathon_id == hackathon_id)
        .where(Registration.status == RegistrationStatus.accepted)
    )
    if accepted_count.scalar() >= hackathon.max_participants:
        return None  # No spot available

    # Promote to offered
    now = datetime.now(timezone.utc)
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
                "accept_url": f"/dashboard?accept_offer={reg.id}"  # Frontend route
            },
            registration_id=reg.id,
            hackathon_id=hackathon_id,
            db=db
        )

    await db.commit()
    return reg


async def get_waitlist_position(
    registration_id: uuid.UUID,
    hackathon_id: uuid.UUID,
    db: AsyncSession
) -> Optional[int]:
    """Get 1-indexed position of a registration in the waitlist."""
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
    hackathon_id: uuid.UUID,
    db: AsyncSession
) -> bool:
    """Check if hackathon is full. Returns True if waitlist should be used."""
    hackathon = await db.get(Hackathon, hackathon_id)
    if not hackathon or not hackathon.max_participants:
        return False

    accepted_count = await db.execute(
        select(func.count(Registration.id))
        .where(Registration.hackathon_id == hackathon_id)
        .where(Registration.status == RegistrationStatus.accepted)
    )
    return accepted_count.scalar() >= hackathon.max_participants
