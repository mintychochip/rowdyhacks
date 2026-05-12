"""Prize and track prize management service.

Provides CRUD operations for hackathon prizes, including optional track
associations and currency handling.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Prize


class PrizeService:
    """CRUD operations for hackathon prizes.

    Prizes can be associated with specific tracks and support configurable
    amounts and currencies.
    """

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
        """Create a new prize for a hackathon.

        Behavior:
        1. Build a Prize instance with the provided fields.
        2. Add the prize to the async session.
        3. Commit and refresh to persist the record.

        Raises: None
        Side Effects: Inserts a new Prize row into the database.
        Dependencies: app.models.Prize.
        Consumers: POST /api/prizes, authenticated users creating prizes.
        """
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
        """List prizes for a hackathon ordered by name.

        Behavior:
        1. Query Prize rows filtered by hackathon_id.
        2. Order results by name ascending.
        3. Return the list of matching prizes.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models.Prize.
        Consumers: GET /api/prizes?hackathon_id=..., public prize listing.
        """
        result = await db.execute(select(Prize).where(Prize.hackathon_id == hackathon_id).order_by(Prize.name))
        return list(result.scalars().all())

    async def get_prize(self, db: AsyncSession, prize_id) -> Prize | None:
        """Get a single prize by its ID.

        Behavior:
        1. Query Prize by the given prize_id.
        2. Return the record if found, otherwise None.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models.Prize.
        Consumers: GET /api/prizes/{prize_id}, public prize detail view.
        """
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
        """Update prize fields selectively.

        Behavior:
        1. Load the prize by ID.
        2. Validate the prize exists.
        3. Apply any provided non-None field updates.
        4. Commit and refresh the record.

        Raises: ValueError if the prize is not found.
        Side Effects: Updates Prize row fields in the database.
        Dependencies: app.models.Prize.
        Consumers: PUT /api/prizes/{prize_id}, authenticated users updating prizes.
        """
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
        """Delete a prize from a hackathon.

        Behavior:
        1. Load the prize by ID.
        2. Validate the prize exists.
        3. Delete the record from the session and commit.

        Raises: ValueError if the prize is not found.
        Side Effects: Deletes a Prize row from the database.
        Dependencies: app.models.Prize.
        Consumers: DELETE /api/prizes/{prize_id}, authenticated users deleting prizes.
        """
        prize = await self.get_prize(db, prize_id)
        if not prize:
            raise ValueError("Prize not found")
        await db.delete(prize)
        await db.commit()

    async def award_prize(
        self,
        db: AsyncSession,
        prize_id,
        team_id,
        hackathon_id,
        awarded_by: str,
    ):
        """Award a prize to a team.

        Behavior:
        1. Verify the prize exists and belongs to the hackathon.
        2. Check if the prize is already awarded.
        3. Create and persist a PrizeAward record.

        Raises: ValueError if prize not found or already awarded.
        Side Effects: Inserts PrizeAward row.
        Dependencies: app.models.PrizeAward.
        Consumers: POST /api/prizes/{prize_id}/award/{team_id}.
        """
        from app.models import PrizeAward

        prize = await self.get_prize(db, prize_id)
        if not prize:
            raise ValueError("Prize not found")
        if prize.hackathon_id != hackathon_id:
            raise ValueError("Prize does not belong to this hackathon")

        existing = await db.execute(select(PrizeAward).where(PrizeAward.prize_id == prize_id))
        if existing.scalar_one_or_none():
            raise ValueError("Prize already awarded")

        award = PrizeAward(
            prize_id=prize_id,
            team_id=team_id,
            hackathon_id=hackathon_id,
            awarded_by=awarded_by,
        )
        db.add(award)
        await db.commit()
        await db.refresh(award)
        return award

    async def revoke_award(self, db: AsyncSession, prize_id) -> None:
        """Revoke a prize award.

        Behavior:
        1. Find the PrizeAward by prize_id.
        2. Delete it if found.

        Raises: ValueError if award not found.
        Side Effects: Deletes PrizeAward row.
        Dependencies: app.models.PrizeAward.
        Consumers: DELETE /api/prizes/{prize_id}/award.
        """
        from app.models import PrizeAward

        result = await db.execute(select(PrizeAward).where(PrizeAward.prize_id == prize_id))
        award = result.scalar_one_or_none()
        if not award:
            raise ValueError("Award not found")
        await db.delete(award)
        await db.commit()

    async def list_awarded_prizes(self, db: AsyncSession, hackathon_id) -> list:
        """List all awarded prizes for a hackathon with team details.

        Behavior:
        1. Query PrizeAward rows filtered by hackathon_id.
        2. Eager load prize and team relationships.
        3. Return the list of awards.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models.PrizeAward.
        Consumers: GET /api/hackathons/{id}/prizes/awarded.
        """
        from sqlalchemy.orm import joinedload
        from app.models import PrizeAward

        result = await db.execute(
            select(PrizeAward)
            .where(PrizeAward.hackathon_id == hackathon_id)
            .options(joinedload(PrizeAward.prize), joinedload(PrizeAward.team))
        )
        return list(result.scalars().all())
