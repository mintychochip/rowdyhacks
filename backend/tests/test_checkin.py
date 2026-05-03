import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.auth import create_qr_token, hash_password
from app.models import Hackathon, Registration, RegistrationStatus, User, UserRole


@pytest.mark.asyncio
async def test_scan_checks_in_accepted_registration(db_session, client):
    user = User(
        id=uuid.uuid4(),
        email="scan@test.com",
        name="Scannie",
        password_hash=hash_password("pw"),
        role=UserRole.participant,
    )
    org = User(
        id=uuid.uuid4(),
        email="checkinorg@test.com",
        name="Organizer",
        password_hash=hash_password("pw"),
        role=UserRole.organizer,
    )
    hack = Hackathon(
        id=uuid.uuid4(),
        name="ScanHack",
        organizer_id=org.id,
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC) + timedelta(days=3),
    )
    reg = Registration(id=uuid.uuid4(), hackathon_id=hack.id, user_id=user.id, status=RegistrationStatus.accepted)
    for obj in [org, user, hack, reg]:
        db_session.add(obj)
    await db_session.commit()

    qr_token = create_qr_token(str(reg.id), str(user.id), str(hack.id), hack.end_date)
    response = await client.post(f"/api/checkin/scan?token={qr_token}")
    assert response.status_code == 200
    assert response.json()["status"] == "checked_in"


@pytest.mark.asyncio
async def test_scan_rejects_expired_token(db_session, client):
    user = User(
        id=uuid.uuid4(),
        email="exp@test.com",
        name="Expired",
        password_hash=hash_password("pw"),
        role=UserRole.participant,
    )
    hack = Hackathon(
        id=uuid.uuid4(),
        name="OldHack",
        organizer_id=user.id,
        start_date=datetime.now(UTC) - timedelta(days=10),
        end_date=datetime.now(UTC) - timedelta(days=3),
    )
    reg = Registration(id=uuid.uuid4(), hackathon_id=hack.id, user_id=user.id, status=RegistrationStatus.accepted)
    for obj in [user, hack, reg]:
        db_session.add(obj)
    await db_session.commit()

    qr_token = create_qr_token(str(reg.id), str(user.id), str(hack.id), hack.end_date)
    response = await client.post(f"/api/checkin/scan?token={qr_token}")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_scan_rejects_double_checkin(db_session, client):
    user = User(
        id=uuid.uuid4(),
        email="double@test.com",
        name="Double",
        password_hash=hash_password("pw"),
        role=UserRole.participant,
    )
    hack = Hackathon(
        id=uuid.uuid4(),
        name="DoubleHack",
        organizer_id=user.id,
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC) + timedelta(days=3),
    )
    reg = Registration(id=uuid.uuid4(), hackathon_id=hack.id, user_id=user.id, status=RegistrationStatus.checked_in)
    for obj in [user, hack, reg]:
        db_session.add(obj)
    await db_session.commit()

    qr_token = create_qr_token(str(reg.id), str(user.id), str(hack.id), hack.end_date)
    response = await client.post(f"/api/checkin/scan?token={qr_token}")
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_scan_rejects_revoked_registration(db_session, client):
    """After accept then reject, scanning should return 410 registration_revoked."""
    user = User(
        id=uuid.uuid4(),
        email="revoked@test.com",
        name="Revoked",
        password_hash=hash_password("pw"),
        role=UserRole.participant,
    )
    org = User(
        id=uuid.uuid4(),
        email="revorg@test.com",
        name="RevOrg",
        password_hash=hash_password("pw"),
        role=UserRole.organizer,
    )
    hack = Hackathon(
        id=uuid.uuid4(),
        name="RevokeHack",
        organizer_id=org.id,
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC) + timedelta(days=3),
    )
    reg = Registration(id=uuid.uuid4(), hackathon_id=hack.id, user_id=user.id, status=RegistrationStatus.rejected)
    for obj in [org, user, hack, reg]:
        db_session.add(obj)
    await db_session.commit()

    qr_token = create_qr_token(str(reg.id), str(user.id), str(hack.id), hack.end_date)
    response = await client.post(f"/api/checkin/scan?token={qr_token}")
    assert response.status_code == 410
