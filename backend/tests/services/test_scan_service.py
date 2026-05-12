"""Tests for ScanService."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_qr_token
from app.models import Hackathon, Registration, RegistrationStatus, User, UserRole
from app.services.scan_service import ScanError, ScanService


@pytest.mark.anyio
async def test_scan_qr_token_success(db_session: AsyncSession):
    """scan_qr_token must check in an accepted registration."""
    service = ScanService()
    user = User(id=str(uuid.uuid4()), email="scan@test.com", name="Scanner", role=UserRole.participant)
    hack = Hackathon(
        id=uuid.uuid4(),
        name="ScanHack",
        organizer_id=user.id,
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC) + timedelta(days=3),
    )
    reg = Registration(
        id=uuid.uuid4(),
        hackathon_id=hack.id,
        user_id=user.id,
        status=RegistrationStatus.accepted,
    )
    db_session.add_all([user, hack, reg])
    await db_session.commit()

    token = create_qr_token(str(reg.id), str(user.id), str(hack.id), hack.end_date)
    result = await service.scan_qr_token(db_session, token)

    assert result["id"] == str(reg.id)
    assert result["status"] == "checked_in"
    assert result["checked_in_at"] is not None
    assert result["user_id"] == str(user.id)

    # Verify DB state
    fetched = await db_session.execute(select(Registration).where(Registration.id == reg.id))
    row = fetched.scalar_one()
    assert row.status == RegistrationStatus.checked_in
    assert row.checked_in_at is not None


@pytest.mark.anyio
async def test_scan_qr_token_invalid_token(db_session: AsyncSession):
    """scan_qr_token must raise ScanError(401) for an invalid token."""
    service = ScanService()
    with pytest.raises(ScanError) as exc_info:
        await service.scan_qr_token(db_session, "not-a-valid-token")
    assert exc_info.value.status_code == 401
    assert exc_info.value.error_code == "invalid_token"


@pytest.mark.anyio
async def test_scan_qr_token_expired(db_session: AsyncSession):
    """scan_qr_token must raise ScanError(401) for an expired token."""
    service = ScanService()
    user = User(id=str(uuid.uuid4()), email="exp@test.com", name="Expired", role=UserRole.participant)
    hack = Hackathon(
        id=uuid.uuid4(),
        name="OldHack",
        organizer_id=user.id,
        start_date=datetime.now(UTC) - timedelta(days=10),
        end_date=datetime.now(UTC) - timedelta(days=3),
    )
    reg = Registration(
        id=uuid.uuid4(),
        hackathon_id=hack.id,
        user_id=user.id,
        status=RegistrationStatus.accepted,
    )
    db_session.add_all([user, hack, reg])
    await db_session.commit()

    token = create_qr_token(str(reg.id), str(user.id), str(hack.id), hack.end_date)
    with pytest.raises(ScanError) as exc_info:
        await service.scan_qr_token(db_session, token)
    assert exc_info.value.status_code == 401


@pytest.mark.anyio
async def test_scan_qr_token_already_checked_in(db_session: AsyncSession):
    """scan_qr_token must raise ScanError(409) when already checked in."""
    service = ScanService()
    user = User(id=str(uuid.uuid4()), email="double@test.com", name="Double", role=UserRole.participant)
    hack = Hackathon(
        id=uuid.uuid4(),
        name="DoubleHack",
        organizer_id=user.id,
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC) + timedelta(days=3),
    )
    reg = Registration(
        id=uuid.uuid4(),
        hackathon_id=hack.id,
        user_id=user.id,
        status=RegistrationStatus.checked_in,
        checked_in_at=datetime.now(UTC),
    )
    db_session.add_all([user, hack, reg])
    await db_session.commit()

    token = create_qr_token(str(reg.id), str(user.id), str(hack.id), hack.end_date)
    with pytest.raises(ScanError) as exc_info:
        await service.scan_qr_token(db_session, token)
    assert exc_info.value.status_code == 409
    assert exc_info.value.error_code == "already_checked_in"


@pytest.mark.anyio
async def test_scan_qr_token_rejected(db_session: AsyncSession):
    """scan_qr_token must raise ScanError(410) for a rejected registration."""
    service = ScanService()
    user = User(id=str(uuid.uuid4()), email="revoked@test.com", name="Revoked", role=UserRole.participant)
    hack = Hackathon(
        id=uuid.uuid4(),
        name="RevokeHack",
        organizer_id=user.id,
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC) + timedelta(days=3),
    )
    reg = Registration(
        id=uuid.uuid4(),
        hackathon_id=hack.id,
        user_id=user.id,
        status=RegistrationStatus.rejected,
    )
    db_session.add_all([user, hack, reg])
    await db_session.commit()

    token = create_qr_token(str(reg.id), str(user.id), str(hack.id), hack.end_date)
    with pytest.raises(ScanError) as exc_info:
        await service.scan_qr_token(db_session, token)
    assert exc_info.value.status_code == 410
    assert exc_info.value.error_code == "registration_revoked"


@pytest.mark.anyio
async def test_checkin_registration_success(db_session: AsyncSession):
    """checkin_registration must update status to checked_in."""
    service = ScanService()
    user = User(id=str(uuid.uuid4()), email="org@test.com", name="Org", role=UserRole.participant)
    hack = Hackathon(
        id=uuid.uuid4(),
        name="OrgHack",
        organizer_id=user.id,
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC) + timedelta(days=3),
    )
    reg = Registration(
        id=uuid.uuid4(),
        hackathon_id=hack.id,
        user_id=user.id,
        status=RegistrationStatus.accepted,
    )
    db_session.add_all([user, hack, reg])
    await db_session.commit()

    result = await service.checkin_registration(db_session, hack.id, reg.id)
    assert result["id"] == str(reg.id)
    assert result["status"] == "checked_in"
    assert result["checked_in_at"] is not None
    assert result["user_id"] == str(user.id)

    fetched = await db_session.execute(select(Registration).where(Registration.id == reg.id))
    row = fetched.scalar_one()
    assert row.status == RegistrationStatus.checked_in


@pytest.mark.anyio
async def test_checkin_registration_not_found(db_session: AsyncSession):
    """checkin_registration must raise ScanError(404) for missing registration."""
    service = ScanService()
    with pytest.raises(ScanError) as exc_info:
        await service.checkin_registration(db_session, uuid.uuid4(), uuid.uuid4())
    assert exc_info.value.status_code == 404
    assert exc_info.value.error_code == "registration_not_found"


@pytest.mark.anyio
async def test_checkin_registration_not_accepted(db_session: AsyncSession):
    """checkin_registration must raise ScanError(409) for non-accepted registration."""
    service = ScanService()
    user = User(id=str(uuid.uuid4()), email="pend@test.com", name="Pending", role=UserRole.participant)
    hack = Hackathon(
        id=uuid.uuid4(),
        name="PenHack",
        organizer_id=user.id,
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC) + timedelta(days=3),
    )
    reg = Registration(
        id=uuid.uuid4(),
        hackathon_id=hack.id,
        user_id=user.id,
        status=RegistrationStatus.pending,
    )
    db_session.add_all([user, hack, reg])
    await db_session.commit()

    with pytest.raises(ScanError) as exc_info:
        await service.checkin_registration(db_session, hack.id, reg.id)
    assert exc_info.value.status_code == 409
    assert exc_info.value.error_code == "registration_not_active"
