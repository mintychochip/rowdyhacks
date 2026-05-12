"""Tests for EmailBlastService."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Hackathon, Registration, RegistrationStatus, Track, User, UserRole
from app.services.email_blast_service import EmailBlastService


@pytest_asyncio.fixture
async def hackathon_with_registrations(db_session: AsyncSession):
    """Create a hackathon with users in various registration statuses (unique per test)."""
    from datetime import UTC, datetime

    uid = uuid.uuid4().hex[:8]
    organizer = User(
        id=f"org-{uid}",
        email=f"org-{uid}@example.com",
        name="Organizer",
        role=UserRole.organizer,
    )
    db_session.add(organizer)

    hackathon = Hackathon(
        name=f"Blast Hack {uid}",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id=organizer.id,
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)

    users = []
    statuses = [
        RegistrationStatus.accepted,
        RegistrationStatus.accepted,
        RegistrationStatus.waitlisted,
        RegistrationStatus.waitlisted,
        RegistrationStatus.checked_in,
        RegistrationStatus.rejected,
    ]
    for i, status in enumerate(statuses):
        user = User(
            id=f"user-{uid}-{i}",
            email=f"user-{uid}-{i}@example.com",
            name=f"User {i}",
            role=UserRole.participant,
        )
        db_session.add(user)
        users.append(user)

        reg = Registration(
            hackathon_id=hackathon.id,
            user_id=user.id,
            status=status,
        )
        db_session.add(reg)

    await db_session.commit()
    return hackathon, users


@pytest_asyncio.fixture
async def hackathon_with_track_registrations(db_session: AsyncSession):
    """Create a hackathon with a track and accepted registrations tied to it (unique per test)."""
    from datetime import UTC, datetime

    uid = uuid.uuid4().hex[:8]
    organizer = User(
        id=f"org-track-{uid}",
        email=f"org-track-{uid}@example.com",
        name="Track Organizer",
        role=UserRole.organizer,
    )
    db_session.add(organizer)

    hackathon = Hackathon(
        name=f"Track Hack {uid}",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id=organizer.id,
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)

    track = Track(
        hackathon_id=hackathon.id,
        name="AI Track",
        description="AI projects",
        challenge="Use ML",
        icon="🤖",
        color="#10b981",
        prize="Track Prize",
        track_type="themed",
        criteria=["Innovation"],
        resources=[],
    )
    db_session.add(track)
    await db_session.commit()
    await db_session.refresh(track)

    users = []
    for i in range(3):
        user = User(
            id=f"track-user-{uid}-{i}",
            email=f"track-user-{uid}-{i}@example.com",
            name=f"Track User {i}",
            role=UserRole.participant,
        )
        db_session.add(user)
        users.append(user)

        reg = Registration(
            hackathon_id=hackathon.id,
            user_id=user.id,
            status=RegistrationStatus.accepted,
            track_id=track.id,
        )
        db_session.add(reg)

    # One accepted user without track
    other_user = User(
        id=f"other-user-{uid}",
        email=f"other-user-{uid}@example.com",
        name="Other User",
        role=UserRole.participant,
    )
    db_session.add(other_user)
    reg_other = Registration(
        hackathon_id=hackathon.id,
        user_id=other_user.id,
        status=RegistrationStatus.accepted,
    )
    db_session.add(reg_other)

    await db_session.commit()
    return hackathon, track, users


@pytest.mark.anyio
async def test_send_bulk_email(db_session: AsyncSession, hackathon_with_registrations):
    """send_bulk_email must email all accepted registrants."""
    hackathon, _ = hackathon_with_registrations
    service = EmailBlastService()

    with patch("app.services.email_blast_service.send_email_with_retry", new_callable=AsyncMock, return_value=True):
        summary = await service.send_bulk_email(db_session, hackathon.id, "Hello", "World", "org-123")

    assert summary["cohort"] == "accepted"
    assert summary["sent"] == 2
    assert summary["failed"] == 0


@pytest.mark.anyio
async def test_send_to_waitlist(db_session: AsyncSession, hackathon_with_registrations):
    """send_to_waitlist must email all waitlisted registrants."""
    hackathon, _ = hackathon_with_registrations
    service = EmailBlastService()

    with patch("app.services.email_blast_service.send_email_with_retry", new_callable=AsyncMock, return_value=True):
        summary = await service.send_to_waitlist(db_session, hackathon.id, "Waitlist Update", "Info", "org-123")

    assert summary["cohort"] == "waitlist"
    assert summary["sent"] == 2
    assert summary["failed"] == 0


@pytest.mark.anyio
async def test_send_to_checked_in(db_session: AsyncSession, hackathon_with_registrations):
    """send_to_checked_in must email all checked-in registrants."""
    hackathon, _ = hackathon_with_registrations
    service = EmailBlastService()

    with patch("app.services.email_blast_service.send_email_with_retry", new_callable=AsyncMock, return_value=True):
        summary = await service.send_to_checked_in(db_session, hackathon.id, "Check-in Note", "Details", "org-123")

    assert summary["cohort"] == "checked_in"
    assert summary["sent"] == 1
    assert summary["failed"] == 0


@pytest.mark.anyio
async def test_send_to_track(db_session: AsyncSession, hackathon_with_track_registrations):
    """send_to_track must email accepted registrants in a specific track."""
    hackathon, track, _ = hackathon_with_track_registrations
    service = EmailBlastService()

    with patch("app.services.email_blast_service.send_email_with_retry", new_callable=AsyncMock, return_value=True):
        summary = await service.send_to_track(db_session, hackathon.id, track.id, "Track Note", "Details", "org-123")

    assert summary["cohort"] == "track"
    assert summary["sent"] == 3
    assert summary["failed"] == 0


@pytest.mark.anyio
async def test_send_bulk_email_with_failures(db_session: AsyncSession, hackathon_with_registrations):
    """send_bulk_email must count failures when email delivery fails."""
    hackathon, _ = hackathon_with_registrations
    service = EmailBlastService()

    with patch("app.services.email_blast_service.send_email_with_retry", new_callable=AsyncMock, return_value=False):
        summary = await service.send_bulk_email(db_session, hackathon.id, "Hello", "World", "org-123")

    assert summary["sent"] == 0
    assert summary["failed"] == 2
