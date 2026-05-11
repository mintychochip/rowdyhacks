"""Prize and track prize management service."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Prize


class PrizeService:
    """CRUD operations for hackathon prizes."""

    async def create_prize(
        self,
        db: AsyncSession,
        hackathon_id,
        name: str,
        description: str | None = None,
        amount: str | None = None,
        currency: str = "USD",
        track_id=None,
    ) -> Prize:
        """Create a new prize."""
        prize = Prize(
            hackathon_id=hackathon_id,
            name=name,
            description=description,
            amount=amount,
            currency=currency,
            track_id=track_id,
        )
        db.add(prize)
        await db.commit()
        await db.refresh(prize)
        return prize

    async def list_prizes(self, db: AsyncSession, hackathon_id) -> list[Prize]:
        """List prizes for a hackathon."""
        result = await db.execute(select(Prize).where(Prize.hackathon_id == hackathon_id).order_by(Prize.name))
        return list(result.scalars().all())

    async def get_prize(self, db: AsyncSession, prize_id) -> Prize | None:
        """Get a single prize by ID."""
        result = await db.execute(select(Prize).where(Prize.id == prize_id))
        return result.scalar_one_or_none()

    async def update_prize(
        self,
        db: AsyncSession,
        prize_id,
        name: str | None = None,
        description: str | None = None,
        amount: str | None = None,
        currency: str | None = None,
        track_id=None,
    ) -> Prize:
        """Update prize fields."""
        prize = await self.get_prize(db, prize_id)
        if not prize:
            raise ValueError("Prize not found")

        if name is not None:
            prize.name = name
        if description is not None:
            prize.description = description
        if amount is not None:
            prize.amount = amount
        if currency is not None:
            prize.currency = currency
        if track_id is not None:
            prize.track_id = track_id

        await db.commit()
        await db.refresh(prize)
        return prize

    async def delete_prize(self, db: AsyncSession, prize_id) -> None:
        """Delete a prize."""
        prize = await self.get_prize(db, prize_id)
        if not prize:
            raise ValueError("Prize not found")
        await db.delete(prize)
        await db.commit()
