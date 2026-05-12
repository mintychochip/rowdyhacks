"""Tests for RegistrationService."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Hackathon, Registration, RegistrationStatus, User, UserRole
from app.services.registration_service import RegistrationService


@pytest_asyncio.fixture
async def hackathon_and_organizer(db_session: AsyncSession):
    """Create a hackathon and an organizer user."""
    uid = uuid.uuid4().hex[:8]
    user = User(
        id=f"org-{uid}",
        email=f"org-{uid}@example.com",
        name="Test Organizer",
        role=UserRole.organizer,
    )
    db_session.add(user)

    hackathon = Hackathon(
        name="Test Hack",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id=user.id,
        max_participants=10,
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)

    return hackathon, user


@pytest_asyncio.fixture
async def participant(db_session: AsyncSession):
    """Create a participant user."""
    uid = uuid.uuid4().hex[:8]
    user = User(
        id=f"part-{uid}",
        email=f"part-{uid}@example.com",
        name="Test Participant",
        role=UserRole.participant,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def pending_registration(db_session: AsyncSession, hackathon_and_organizer, participant):
    """Create a pending registration for the participant."""
    hackathon, _ = hackathon_and_organizer
    reg = Registration(
        hackathon_id=hackathon.id,
        user_id=participant.id,
        status=RegistrationStatus.pending,
        registered_at=datetime.now(UTC),
    )
    db_session.add(reg)
    await db_session.commit()
    await db_session.refresh(reg)
    return reg


@pytest.mark.anyio
async def test_create_registration(db_session: AsyncSession, hackathon_and_organizer, participant):
    """create_registration must create a pending registration when capacity available."""
    hackathon, _ = hackathon_and_organizer
    service = RegistrationService()

    with patch("app.waitlist.auto_waitlist_if_full", return_value=False):
        reg = await service.create_registration(db_session, hackathon.id, participant.id, None)

    assert reg.status == RegistrationStatus.pending
    assert reg.hackathon_id == hackathon.id
    assert reg.user_id == participant.id


@pytest.mark.anyio
async def test_create_registration_duplicate(db_session: AsyncSession, pending_registration):
    """create_registration must raise 409 for duplicate registration."""
    reg = pending_registration
    service = RegistrationService()

    with pytest.raises(HTTPException, match="Already registered"):
        await service.create_registration(db_session, reg.hackathon_id, reg.user_id, None)


@pytest.mark.anyio
async def test_list_registrations_for_hackathon(
    db_session: AsyncSession, hackathon_and_organizer, pending_registration
):
    """list_registrations_for_hackathon must return registrations with pagination."""
    hackathon, _ = hackathon_and_organizer
    service = RegistrationService()

    result = await service.list_registrations_for_hackathon(db_session, hackathon.id)
    assert result["total"] == 1
    assert len(result["registrations"]) == 1
    assert result["registrations"][0]["status"] == "pending"


@pytest.mark.anyio
async def test_list_registrations_for_user(db_session: AsyncSession, pending_registration):
    """list_registrations_for_user must return the user's registrations."""
    reg = pending_registration
    service = RegistrationService()

    result = await service.list_registrations_for_user(db_session, reg.user_id)
    assert result["total"] == 1
    assert len(result["registrations"]) == 1
    assert result["registrations"][0]["user_id"] == reg.user_id


@pytest.mark.anyio
async def test_get_registration(db_session: AsyncSession, pending_registration):
    """get_registration must return the registration by id."""
    reg = pending_registration
    service = RegistrationService()

    found = await service.get_registration(db_session, reg.id)
    assert found.id == reg.id


@pytest.mark.anyio
async def test_get_registration_not_found(db_session: AsyncSession):
    """get_registration must raise 404 for missing registration."""
    service = RegistrationService()

    with pytest.raises(HTTPException, match="Registration not found"):
        await service.get_registration(db_session, uuid.uuid4())


@pytest.mark.anyio
async def test_accept_registration(db_session: AsyncSession, pending_registration):
    """accept_registration must update status to accepted."""
    reg = pending_registration
    service = RegistrationService()

    updated = await service.accept_registration(db_session, reg.hackathon_id, reg.id)
    assert updated.status == RegistrationStatus.accepted
    assert updated.accepted_at is not None


@pytest.mark.anyio
async def test_accept_registration_not_pending(db_session: AsyncSession, hackathon_and_organizer, participant):
    """accept_registration must raise 409 for non-pending/non-waitlisted registration."""
    hackathon, _ = hackathon_and_organizer
    service = RegistrationService()

    reg = Registration(
        hackathon_id=hackathon.id,
        user_id=participant.id,
        status=RegistrationStatus.rejected,
    )
    db_session.add(reg)
    await db_session.commit()

    with pytest.raises(HTTPException, match="Cannot accept"):
        await service.accept_registration(db_session, hackathon.id, reg.id)


@pytest.mark.anyio
async def test_reject_registration(db_session: AsyncSession, pending_registration):
    """reject_registration must update status to rejected."""
    reg = pending_registration
    service = RegistrationService()

    with patch("app.services.registration_service.promote_from_waitlist", new_callable=AsyncMock):
        updated = await service.reject_registration(db_session, reg.hackathon_id, reg.id, promote_waitlist=True)

    assert updated.status == RegistrationStatus.rejected
    assert updated.qr_token is None


@pytest.mark.anyio
async def test_checkin_registration(db_session: AsyncSession, hackathon_and_organizer, participant):
    """checkin_registration must update status to checked_in."""
    hackathon, _ = hackathon_and_organizer
    service = RegistrationService()

    reg = Registration(
        hackathon_id=hackathon.id,
        user_id=participant.id,
        status=RegistrationStatus.accepted,
        accepted_at=datetime.now(UTC),
    )
    db_session.add(reg)
    await db_session.commit()

    updated = await service.checkin_registration(db_session, hackathon.id, reg.id)
    assert updated.status == RegistrationStatus.checked_in
    assert updated.checked_in_at is not None


@pytest.mark.anyio
async def test_checkin_non_accepted(db_session: AsyncSession, pending_registration):
    """checkin_registration must raise 409 for non-accepted registration."""
    reg = pending_registration
    service = RegistrationService()

    with pytest.raises(HTTPException, match="Cannot check in"):
        await service.checkin_registration(db_session, reg.hackathon_id, reg.id)


@pytest.mark.anyio
async def test_waitlist_registration(db_session: AsyncSession, pending_registration):
    """waitlist_registration must move pending to waitlisted."""
    reg = pending_registration
    service = RegistrationService()

    updated = await service.waitlist_registration(db_session, reg.hackathon_id, reg.id)
    assert updated.status == RegistrationStatus.waitlisted


@pytest.mark.anyio
async def test_unwaitlist_registration(db_session: AsyncSession, hackathon_and_organizer, participant):
    """unwaitlist_registration must move waitlisted to pending and reset declined_count."""
    hackathon, _ = hackathon_and_organizer
    service = RegistrationService()

    reg = Registration(
        hackathon_id=hackathon.id,
        user_id=participant.id,
        status=RegistrationStatus.waitlisted,
        declined_count=2,
    )
    db_session.add(reg)
    await db_session.commit()

    updated = await service.unwaitlist_registration(db_session, hackathon.id, reg.id)
    assert updated.status == RegistrationStatus.pending
    assert updated.declined_count == 0


@pytest.mark.anyio
async def test_manual_promote_waitlist(db_session: AsyncSession, hackathon_and_organizer):
    """manual_promote_waitlist must delegate to promote_from_waitlist."""
    hackathon, _ = hackathon_and_organizer
    service = RegistrationService()

    fake_reg = type(
        "FakeReg", (), {"id": uuid.uuid4(), "status": RegistrationStatus.offered, "offer_expires_at": datetime.now(UTC)}
    )()
    with patch(
        "app.services.registration_service.promote_from_waitlist", new_callable=AsyncMock, return_value=fake_reg
    ):
        promoted = await service.manual_promote_waitlist(db_session, hackathon.id)

    assert promoted.status == RegistrationStatus.offered


@pytest.mark.anyio
async def test_manual_promote_waitlist_no_one(db_session: AsyncSession, hackathon_and_organizer):
    """manual_promote_waitlist must raise 409 when no one to promote."""
    hackathon, _ = hackathon_and_organizer
    service = RegistrationService()

    with patch("app.services.registration_service.promote_from_waitlist", return_value=None):
        with pytest.raises(HTTPException, match="No one to promote"):
            await service.manual_promote_waitlist(db_session, hackathon.id)


@pytest.mark.anyio
async def test_list_waitlist(db_session: AsyncSession, hackathon_and_organizer, participant):
    """list_waitlist must return waitlisted registrations with positions."""
    hackathon, _ = hackathon_and_organizer
    service = RegistrationService()

    reg = Registration(
        hackathon_id=hackathon.id,
        user_id=participant.id,
        status=RegistrationStatus.waitlisted,
        registered_at=datetime.now(UTC),
    )
    db_session.add(reg)
    await db_session.commit()

    result = await service.list_waitlist(db_session, hackathon.id)
    assert result["total"] == 1
    assert result["waitlist"][0]["position"] == 1
    assert result["waitlist"][0]["user_name"] == participant.name


@pytest.mark.anyio
async def test_bulk_accept(db_session: AsyncSession, hackathon_and_organizer, participant):
    """bulk_accept must accept pending registrations."""
    hackathon, _ = hackathon_and_organizer
    service = RegistrationService()

    reg = Registration(
        hackathon_id=hackathon.id,
        user_id=participant.id,
        status=RegistrationStatus.pending,
    )
    db_session.add(reg)
    await db_session.commit()

    result = await service.bulk_accept(db_session, hackathon.id, [reg.id])
    assert result["accepted"] == 1
    assert result["waitlisted"] == 0


@pytest.mark.anyio
async def test_bulk_reject(db_session: AsyncSession, pending_registration):
    """bulk_reject must reject pending registrations."""
    reg = pending_registration
    service = RegistrationService()

    result = await service.bulk_reject(db_session, reg.hackathon_id, [reg.id])
    assert result["rejected"] == 1


@pytest.mark.anyio
async def test_bulk_waitlist(db_session: AsyncSession, hackathon_and_organizer, participant):
    """bulk_waitlist must move pending registrations to waitlist."""
    hackathon, _ = hackathon_and_organizer
    hackathon.waitlist_enabled = True
    await db_session.commit()

    service = RegistrationService()
    reg = Registration(
        hackathon_id=hackathon.id,
        user_id=participant.id,
        status=RegistrationStatus.pending,
    )
    db_session.add(reg)
    await db_session.commit()

    result = await service.bulk_waitlist(db_session, hackathon.id, [reg.id])
    assert result["waitlisted"] == 1


@pytest.mark.anyio
async def test_export_registrations_csv(db_session: AsyncSession, hackathon_and_organizer, participant):
    """export_registrations_csv must return CSV bytes and a filename."""
    hackathon, _ = hackathon_and_organizer
    service = RegistrationService()

    reg = Registration(
        hackathon_id=hackathon.id,
        user_id=participant.id,
        status=RegistrationStatus.accepted,
        registered_at=datetime.now(UTC),
    )
    db_session.add(reg)
    await db_session.commit()

    bytes_io, filename = await service.export_registrations_csv(db_session, hackathon.id)
    content = bytes_io.read().decode()
    assert "ID,Status,Registered At" in content
    assert participant.name in content
    assert str(hackathon.id) in filename


@pytest.mark.anyio
async def test_registration_to_response(db_session: AsyncSession, pending_registration, participant):
    """registration_to_response must serialize all expected fields."""
    reg = pending_registration
    response = RegistrationService.registration_to_response(reg, participant)

    assert response["id"] == str(reg.id)
    assert response["status"] == "pending"
    assert response["user_name"] == participant.name
    assert response["user_email"] == participant.email
    assert response["user_role"] == participant.role.value
