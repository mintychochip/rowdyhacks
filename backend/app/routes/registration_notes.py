"""Routes for registration review notes (organizer-only)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import require_hackathon_organizer
from app.database import get_db
from app.schemas import RegistrationReviewNoteCreate, RegistrationReviewNoteUpdate
from app.services.registration_note_service import RegistrationNoteService

router = APIRouter(prefix="/api/hackathons", tags=["registration-notes"])


@router.post("/{hackathon_id}/registrations/{registration_id}/notes", status_code=201)
async def create_note(
    hackathon_id: uuid.UUID,
    registration_id: uuid.UUID,
    body: RegistrationReviewNoteCreate,
    auth: dict = Depends(require_hackathon_organizer),
    db: AsyncSession = Depends(get_db),
):
    """Add a review note to a registration. Organizer only."""
    from sqlalchemy import and_, select
    from app.models import Registration

    # Verify registration belongs to this hackathon
    reg_result = await db.execute(
        select(Registration).where(and_(Registration.id == registration_id, Registration.hackathon_id == hackathon_id))
    )
    reg = reg_result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")

    service = RegistrationNoteService(db)
    note = await service.create_note(
        registration_id=registration_id,
        organizer_id=auth["user"].id,
        note_text=body.note_text,
        rating=body.rating,
    )

    return {
        "id": str(note.id),
        "registration_id": str(note.registration_id),
        "organizer_id": note.organizer_id,
        "organizer_name": auth["user"].name,
        "note_text": note.note_text,
        "rating": note.rating,
        "created_at": note.created_at.isoformat(),
    }


@router.get("/{hackathon_id}/registrations/{registration_id}/notes")
async def list_notes(
    hackathon_id: uuid.UUID,
    registration_id: uuid.UUID,
    auth: dict = Depends(require_hackathon_organizer),
    db: AsyncSession = Depends(get_db),
):
    """List review notes for a registration. Organizer only."""
    from sqlalchemy import and_, select
    from app.models import Registration, User

    reg_result = await db.execute(
        select(Registration).where(and_(Registration.id == registration_id, Registration.hackathon_id == hackathon_id))
    )
    reg = reg_result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")

    service = RegistrationNoteService(db)
    notes = await service.list_notes_for_registration(registration_id)

    # Load organizers for names
    organizer_ids = [n.organizer_id for n in notes]
    users_result = await db.execute(select(User).where(User.id.in_(organizer_ids)))
    users = {u.id: u for u in users_result.scalars().all()}

    return {
        "notes": [
            {
                "id": str(n.id),
                "organizer_id": n.organizer_id,
                "organizer_name": users.get(n.organizer_id).name if users.get(n.organizer_id) else None,
                "organizer_email": users.get(n.organizer_id).email if users.get(n.organizer_id) else None,
                "note_text": n.note_text,
                "rating": n.rating,
                "created_at": n.created_at.isoformat(),
                "updated_at": n.updated_at.isoformat(),
            }
            for n in notes
        ]
    }


@router.put("/{hackathon_id}/registrations/{registration_id}/notes/{note_id}")
async def update_note(
    hackathon_id: uuid.UUID,
    registration_id: uuid.UUID,
    note_id: uuid.UUID,
    body: RegistrationReviewNoteUpdate,
    auth: dict = Depends(require_hackathon_organizer),
    db: AsyncSession = Depends(get_db),
):
    """Update a review note. Only the original author can edit."""
    from sqlalchemy import and_, select
    from app.models import Registration

    reg_result = await db.execute(
        select(Registration).where(and_(Registration.id == registration_id, Registration.hackathon_id == hackathon_id))
    )
    reg = reg_result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")

    service = RegistrationNoteService(db)
    note = await service.get_note(note_id)
    if not note or note.registration_id != registration_id:
        raise HTTPException(status_code=404, detail="Note not found")

    if note.organizer_id != auth["user"].id:
        raise HTTPException(status_code=403, detail="Only the note author can edit this note")

    note = await service.update_note(
        note,
        note_text=body.note_text,
        rating=body.rating,
    )

    return {
        "id": str(note.id),
        "note_text": note.note_text,
        "rating": note.rating,
        "updated_at": note.updated_at.isoformat(),
    }


@router.delete("/{hackathon_id}/registrations/{registration_id}/notes/{note_id}", status_code=204)
async def delete_note(
    hackathon_id: uuid.UUID,
    registration_id: uuid.UUID,
    note_id: uuid.UUID,
    auth: dict = Depends(require_hackathon_organizer),
    db: AsyncSession = Depends(get_db),
):
    """Delete a review note. Only the original author can delete."""
    from sqlalchemy import and_, select
    from app.models import Registration

    reg_result = await db.execute(
        select(Registration).where(and_(Registration.id == registration_id, Registration.hackathon_id == hackathon_id))
    )
    reg = reg_result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")

    service = RegistrationNoteService(db)
    note = await service.get_note(note_id)
    if not note or note.registration_id != registration_id:
        raise HTTPException(status_code=404, detail="Note not found")

    if note.organizer_id != auth["user"].id:
        raise HTTPException(status_code=403, detail="Only the note author can delete this note")

    await service.delete_note(note)
    return None
