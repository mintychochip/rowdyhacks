"""Tests for RegistrationNoteService."""

import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Hackathon,
    Registration,
    RegistrationStatus,
    User,
    UserRole,
)
from app.services.registration_note_service import RegistrationNoteService


@pytest_asyncio.fixture
async def hackathon_and_registration(db_session: AsyncSession):
    """Create a hackathon with a registration."""
    uid = uuid.uuid4().hex[:8]
    org = User(
        id=f"org-{uid}",
        email=f"org-{uid}@example.com",
        name="Test Organizer",
        role=UserRole.organizer,
    )
    participant = User(
        id=f"part-{uid}",
        email=f"part-{uid}@example.com",
        name="Test Participant",
        role=UserRole.participant,
    )
    db_session.add(org)
    db_session.add(participant)

    hackathon = Hackathon(
        name="Test Hack",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id="org-1",
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)

    reg = Registration(
        hackathon_id=hackathon.id,
        user_id="part-1",
        status=RegistrationStatus.pending,
    )
    db_session.add(reg)
    await db_session.commit()
    await db_session.refresh(reg)

    return hackathon, reg


@pytest.mark.anyio
async def test_create_note(db_session: AsyncSession, hackathon_and_registration):
    _, reg = hackathon_and_registration
    service = RegistrationNoteService(db_session)

    note = await service.create_note(
        registration_id=reg.id,
        organizer_id="org-1",
        note_text="Strong applicant",
        rating=5,
    )
    assert note.registration_id == reg.id
    assert note.organizer_id == "org-1"
    assert note.note_text == "Strong applicant"
    assert note.rating == 5


@pytest.mark.anyio
async def test_list_notes_for_registration(db_session: AsyncSession, hackathon_and_registration):
    _, reg = hackathon_and_registration
    service = RegistrationNoteService(db_session)

    await service.create_note(reg.id, "org-1", "Note 1", 4)
    await service.create_note(reg.id, "org-2", "Note 2", 3)

    notes = await service.list_notes_for_registration(reg.id)
    assert len(notes) == 2
    assert notes[0].note_text == "Note 2"  # descending order
    assert notes[1].note_text == "Note 1"


@pytest.mark.anyio
async def test_get_note(db_session: AsyncSession, hackathon_and_registration):
    _, reg = hackathon_and_registration
    service = RegistrationNoteService(db_session)

    created = await service.create_note(reg.id, "org-1", "Note text", 2)
    fetched = await service.get_note(created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.note_text == "Note text"

    missing = await service.get_note(uuid.uuid4())
    assert missing is None


@pytest.mark.anyio
async def test_update_note(db_session: AsyncSession, hackathon_and_registration):
    _, reg = hackathon_and_registration
    service = RegistrationNoteService(db_session)

    created = await service.create_note(reg.id, "org-1", "Original", 2)
    updated = await service.update_note(created, note_text="Updated", rating=4)
    assert updated.note_text == "Updated"
    assert updated.rating == 4


@pytest.mark.anyio
async def test_delete_note(db_session: AsyncSession, hackathon_and_registration):
    _, reg = hackathon_and_registration
    service = RegistrationNoteService(db_session)

    created = await service.create_note(reg.id, "org-1", "To delete", 1)
    await service.delete_note(created)

    fetched = await service.get_note(created.id)
    assert fetched is None


@pytest.mark.anyio
async def test_get_aggregates_for_registration(db_session: AsyncSession, hackathon_and_registration):
    _, reg = hackathon_and_registration
    service = RegistrationNoteService(db_session)

    aggregates = await service.get_aggregates_for_registration(reg.id)
    assert aggregates["review_notes_count"] == 0
    assert aggregates["average_rating"] is None

    await service.create_note(reg.id, "org-1", "Note 1", 4)
    await service.create_note(reg.id, "org-2", "Note 2", 2)

    aggregates = await service.get_aggregates_for_registration(reg.id)
    assert aggregates["review_notes_count"] == 2
    assert aggregates["average_rating"] == 3.0


@pytest.mark.anyio
async def test_get_aggregates_ignores_null_ratings(db_session: AsyncSession, hackathon_and_registration):
    _, reg = hackathon_and_registration
    service = RegistrationNoteService(db_session)

    await service.create_note(reg.id, "org-1", "No rating", None)
    await service.create_note(reg.id, "org-2", "Rated", 5)

    aggregates = await service.get_aggregates_for_registration(reg.id)
    assert aggregates["review_notes_count"] == 2
    assert aggregates["average_rating"] == 5.0
