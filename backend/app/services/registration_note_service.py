"""Service for registration review note CRUD and aggregation."""

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RegistrationReviewNote


class RegistrationNoteService:
    """Business logic for organizer review notes on registrations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_note(
        self,
        registration_id: uuid.UUID,
        organizer_id: str,
        note_text: str,
        rating: Optional[int],
    ) -> RegistrationReviewNote:
        """Create a review note."""
        note = RegistrationReviewNote(
            registration_id=registration_id,
            organizer_id=organizer_id,
            note_text=note_text,
            rating=rating,
        )
        self.db.add(note)
        await self.db.commit()
        await self.db.refresh(note)
        return note

    async def list_notes_for_registration(
        self,
        registration_id: uuid.UUID,
    ) -> list[RegistrationReviewNote]:
        """Return all notes for a registration, ordered by created_at desc."""
        result = await self.db.execute(
            select(RegistrationReviewNote)
            .where(RegistrationReviewNote.registration_id == registration_id)
            .order_by(RegistrationReviewNote.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_note(self, note_id: uuid.UUID) -> Optional[RegistrationReviewNote]:
        """Get a single note by ID."""
        result = await self.db.execute(select(RegistrationReviewNote).where(RegistrationReviewNote.id == note_id))
        return result.scalar_one_or_none()

    async def update_note(
        self,
        note: RegistrationReviewNote,
        note_text: Optional[str] = None,
        rating: Optional[int] = None,
    ) -> RegistrationReviewNote:
        """Update a note's text and/or rating."""
        if note_text is not None:
            note.note_text = note_text
        if rating is not None:
            note.rating = rating
        await self.db.commit()
        await self.db.refresh(note)
        return note

    async def delete_note(self, note: RegistrationReviewNote) -> None:
        """Delete a note."""
        await self.db.delete(note)
        await self.db.commit()

    async def get_aggregates_for_registration(
        self,
        registration_id: uuid.UUID,
    ) -> dict:
        """Return note count and average rating for a registration."""
        count_result = await self.db.execute(
            select(func.count(RegistrationReviewNote.id)).where(
                RegistrationReviewNote.registration_id == registration_id
            )
        )
        count = count_result.scalar() or 0

        avg_result = await self.db.execute(
            select(func.avg(RegistrationReviewNote.rating)).where(
                RegistrationReviewNote.registration_id == registration_id,
                RegistrationReviewNote.rating.isnot(None),
            )
        )
        avg = avg_result.scalar()

        return {
            "review_notes_count": count,
            "average_rating": round(avg, 2) if avg is not None else None,
        }
