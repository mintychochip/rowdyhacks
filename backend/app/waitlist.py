"""Waitlist management logic.

This module re-exports waitlist functions for backward compatibility.
All implementation lives in WaitlistService inside app.services.waitlist_service.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Registration
from app.services.waitlist_service import WaitlistService

_service = WaitlistService()


async def promote_from_waitlist(hackathon_id: uuid.UUID, db: AsyncSession) -> Registration | None:
    """Promote the top waitlisted registration to ``offered`` status.

    Backward-compatible wrapper around WaitlistService.promote_from_waitlist.
    """
    return await _service.promote_from_waitlist(hackathon_id, db)


async def get_waitlist_position(registration_id: uuid.UUID, hackathon_id: uuid.UUID, db: AsyncSession) -> int | None:
    """Get the 1-indexed position of a registration in the waitlist.

    Backward-compatible wrapper around WaitlistService.get_waitlist_position.
    """
    return await _service.get_waitlist_position(registration_id, hackathon_id, db)


async def auto_waitlist_if_full(hackathon_id: uuid.UUID, db: AsyncSession) -> bool:
    """Check whether a hackathon has reached its participant capacity.

    Backward-compatible wrapper around WaitlistService.auto_waitlist_if_full.
    """
    return await _service.auto_waitlist_if_full(hackathon_id, db)
