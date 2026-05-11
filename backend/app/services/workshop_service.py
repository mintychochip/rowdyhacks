"""Workshop and schedule management service."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Workshop


class WorkshopService:
    """CRUD operations for workshops within a hackathon."""

    async def create_workshop(
        self,
        db: AsyncSession,
        hackathon_id,
        title: str,
        description: str | None = None,
        start_time=None,
        end_time=None,
        location: str | None = None,
        speaker_name: str | None = None,
    ) -> Workshop:
        """Create a new workshop."""
        workshop = Workshop(
            hackathon_id=hackathon_id,
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            location=location,
            speaker_name=speaker_name,
        )
        db.add(workshop)
        await db.commit()
        await db.refresh(workshop)
        return workshop

    async def list_workshops(self, db: AsyncSession, hackathon_id) -> list[Workshop]:
        """List workshops for a hackathon ordered by start time."""
        result = await db.execute(
            select(Workshop).where(Workshop.hackathon_id == hackathon_id).order_by(Workshop.start_time)
        )
        return list(result.scalars().all())

    async def get_workshop(self, db: AsyncSession, workshop_id) -> Workshop | None:
        """Get a single workshop by ID."""
        result = await db.execute(select(Workshop).where(Workshop.id == workshop_id))
        return result.scalar_one_or_none()

    async def update_workshop(
        self,
        db: AsyncSession,
        workshop_id,
        title: str | None = None,
        description: str | None = None,
        start_time=None,
        end_time=None,
        location: str | None = None,
        speaker_name: str | None = None,
    ) -> Workshop:
        """Update workshop fields."""
        workshop = await self.get_workshop(db, workshop_id)
        if not workshop:
            raise ValueError("Workshop not found")

        if title is not None:
            workshop.title = title
        if description is not None:
            workshop.description = description
        if start_time is not None:
            workshop.start_time = start_time
        if end_time is not None:
            workshop.end_time = end_time
        if location is not None:
            workshop.location = location
        if speaker_name is not None:
            workshop.speaker_name = speaker_name

        await db.commit()
        await db.refresh(workshop)
        return workshop

    async def delete_workshop(self, db: AsyncSession, workshop_id) -> None:
        """Delete a workshop."""
        workshop = await self.get_workshop(db, workshop_id)
        if not workshop:
            raise ValueError("Workshop not found")
        await db.delete(workshop)
        await db.commit()
