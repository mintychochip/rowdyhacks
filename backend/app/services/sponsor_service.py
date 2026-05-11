"""Sponsor management service."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Sponsor


class SponsorService:
    """CRUD operations for hackathon sponsors."""

    async def create_sponsor(
        self,
        db: AsyncSession,
        hackathon_id,
        name: str,
        tier: str = "silver",
        logo_url: str | None = None,
        website_url: str | None = None,
        description: str | None = None,
    ) -> Sponsor:
        """Create a new sponsor."""
        sponsor = Sponsor(
            hackathon_id=hackathon_id,
            name=name,
            tier=tier,
            logo_url=logo_url,
            website_url=website_url,
            description=description,
        )
        db.add(sponsor)
        await db.commit()
        await db.refresh(sponsor)
        return sponsor

    async def list_sponsors(self, db: AsyncSession, hackathon_id) -> list[Sponsor]:
        """List sponsors for a hackathon ordered by tier then name."""
        result = await db.execute(
            select(Sponsor).where(Sponsor.hackathon_id == hackathon_id).order_by(Sponsor.tier, Sponsor.name)
        )
        return list(result.scalars().all())

    async def get_sponsor(self, db: AsyncSession, sponsor_id) -> Sponsor | None:
        """Get a single sponsor by ID."""
        result = await db.execute(select(Sponsor).where(Sponsor.id == sponsor_id))
        return result.scalar_one_or_none()

    async def update_sponsor(
        self,
        db: AsyncSession,
        sponsor_id,
        name: str | None = None,
        tier: str | None = None,
        logo_url: str | None = None,
        website_url: str | None = None,
        description: str | None = None,
    ) -> Sponsor:
        """Update sponsor fields."""
        sponsor = await self.get_sponsor(db, sponsor_id)
        if not sponsor:
            raise ValueError("Sponsor not found")

        if name is not None:
            sponsor.name = name
        if tier is not None:
            sponsor.tier = tier
        if logo_url is not None:
            sponsor.logo_url = logo_url
        if website_url is not None:
            sponsor.website_url = website_url
        if description is not None:
            sponsor.description = description

        await db.commit()
        await db.refresh(sponsor)
        return sponsor

    async def delete_sponsor(self, db: AsyncSession, sponsor_id) -> None:
        """Delete a sponsor."""
        sponsor = await self.get_sponsor(db, sponsor_id)
        if not sponsor:
            raise ValueError("Sponsor not found")
        await db.delete(sponsor)
        await db.commit()
