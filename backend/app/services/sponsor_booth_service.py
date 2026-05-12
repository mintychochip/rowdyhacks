"""Sponsor booth management service.

Handles booth assignments and lead scanning at hackathons.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SponsorBooth


class SponsorBoothService:
    """CRUD operations for sponsor booth assignments and lead scanning."""

    async def assign_booth(
        self,
        db: AsyncSession,
        hackathon_id,
        sponsor_id,
        booth_number: str | None = None,
    ) -> SponsorBooth:
        """Assign a booth to a sponsor.

        Behavior:
        1. Check for existing booth assignment.
        2. Create and persist SponsorBooth.

        Raises: ValueError if booth already assigned.
        Side Effects: Inserts SponsorBooth row.
        Dependencies: app.models.SponsorBooth.
        """
        existing = await db.execute(
            select(SponsorBooth).where(
                SponsorBooth.hackathon_id == hackathon_id,
                SponsorBooth.sponsor_id == sponsor_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Booth already assigned to this sponsor")

        booth = SponsorBooth(
            hackathon_id=hackathon_id,
            sponsor_id=sponsor_id,
            booth_number=booth_number,
        )
        db.add(booth)
        await db.commit()
        await db.refresh(booth)
        return booth

    async def list_booths(self, db: AsyncSession, hackathon_id) -> list[SponsorBooth]:
        """List sponsor booths for a hackathon.

        Behavior:
        1. Query SponsorBooth rows filtered by hackathon_id.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models.SponsorBooth.
        """
        result = await db.execute(select(SponsorBooth).where(SponsorBooth.hackathon_id == hackathon_id))
        return list(result.scalars().all())

    async def scan_lead(self, db: AsyncSession, booth_id) -> SponsorBooth:
        """Increment lead scan count for a booth.

        Behavior:
        1. Load the booth by ID.
        2. Increment lead_scan_count.
        3. Commit and refresh.

        Raises: ValueError if booth not found.
        Side Effects: Updates SponsorBooth row.
        Dependencies: app.models.SponsorBooth.
        """
        result = await db.execute(select(SponsorBooth).where(SponsorBooth.id == booth_id))
        booth = result.scalar_one_or_none()
        if not booth:
            raise ValueError("Booth not found")
        booth.lead_scan_count += 1
        await db.commit()
        await db.refresh(booth)
        return booth
