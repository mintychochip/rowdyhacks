"""Tests for organizer registration management routes."""

import csv
from datetime import UTC, datetime
from io import StringIO
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import require_clerk_user_with_db, require_organizer
from app.database import get_db
from app.main import app
from app.models import (
    Hackathon,
    HackathonOrganizer,
    Registration,
    RegistrationStatus,
    User,
    UserRole,
)
from app.routes.registrations_organizer import router as registrations_org_router


async def _override_require_organizer():
    return {
        "sub": "test-organizer-id",
        "email": "organizer@test.com",
        "user": type(
            "FakeUser",
            (),
            {
                "role": UserRole.organizer,
                "id": "test-organizer-id",
                "email": "organizer@test.com",
                "name": "Test Organizer",
            },
        )(),
        "payload": {},
    }


async def _override_require_clerk_user_with_db_organizer():
    fake_user = type(
        "FakeUser",
        (),
        {
            "role": UserRole.organizer,
            "id": "test-organizer-id",
            "email": "organizer@test.com",
            "name": "Test Organizer",
        },
    )()
    return {
        "user": fake_user,
        "sub": "test-organizer-id",
        "email": "organizer@test.com",
        "payload": {},
    }


app_reg_org = FastAPI()
app_reg_org.include_router(registrations_org_router)


@pytest_asyncio.fixture
async def org_reg_client(engine):
    """AsyncClient backed by a minimal app with only the registrations_organizer router."""
    async_session_maker = __import__("sqlalchemy.ext.asyncio", fromlist=["async_sessionmaker"]).async_sessionmaker

    async def override_get_db():
        async with async_session_maker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
            yield session

    app_reg_org.dependency_overrides[get_db] = override_get_db
    app_reg_org.dependency_overrides[require_organizer] = _override_require_organizer
    transport = ASGITransport(app=app_reg_org)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app_reg_org.dependency_overrides.clear()


@pytest_asyncio.fixture
async def clean_db(db_session: AsyncSession):
    """Wipe registration-related tables to give each test a clean slate."""
    await db_session.execute(delete(Registration))
    await db_session.execute(delete(HackathonOrganizer))
    await db_session.execute(delete(Hackathon))
    await db_session.execute(delete(User))
    await db_session.commit()
    return db_session


@pytest_asyncio.fixture
async def owned_hackathon(clean_db: AsyncSession):
    """Create a hackathon owned by the test organizer with sample registrations."""
    db_session = clean_db

    organizer = User(
        id="test-organizer-id",
        email="organizer@test.com",
        name="Test Organizer",
        role=UserRole.organizer,
    )
    db_session.add(organizer)

    hackathon = Hackathon(
        name="Test Hackathon",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id="test-organizer-id",
        max_participants=100,
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)

    # Pending registrations
    for i in range(3):
        user = User(
            id=f"participant-{i}",
            email=f"participant-{i}@test.com",
            name=f"Participant {i}",
            role=UserRole.participant,
        )
        db_session.add(user)
        reg = Registration(
            hackathon_id=hackathon.id,
            user_id=user.id,
            status=RegistrationStatus.pending,
            registered_at=datetime.now(UTC),
        )
        db_session.add(reg)

    # Accepted registration
    accepted_user = User(
        id="accepted-user",
        email="accepted@test.com",
        name="Accepted User",
        role=UserRole.participant,
    )
    db_session.add(accepted_user)
    accepted_reg = Registration(
        hackathon_id=hackathon.id,
        user_id=accepted_user.id,
        status=RegistrationStatus.accepted,
        registered_at=datetime.now(UTC),
        accepted_at=datetime.now(UTC),
    )
    db_session.add(accepted_reg)

    # Waitlisted registration
    waitlisted_user = User(
        id="waitlisted-user",
        email="waitlisted@test.com",
        name="Waitlisted User",
        role=UserRole.participant,
    )
    db_session.add(waitlisted_user)
    waitlisted_reg = Registration(
        hackathon_id=hackathon.id,
        user_id=waitlisted_user.id,
        status=RegistrationStatus.waitlisted,
        registered_at=datetime.now(UTC),
        declined_count=0,
    )
    db_session.add(waitlisted_reg)

    await db_session.commit()
    return hackathon


@pytest_asyncio.fixture
async def other_hackathon(clean_db: AsyncSession):
    """Create a hackathon owned by a different user."""
    db_session = clean_db

    other_org = User(
        id="other-organizer-id",
        email="other@example.com",
        name="Other Organizer",
        role=UserRole.organizer,
    )
    db_session.add(other_org)

    hackathon = Hackathon(
        name="Other Hackathon",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id="other-organizer-id",
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)

    participant = User(
        id="other-participant",
        email="other-participant@example.com",
        name="Other Participant",
        role=UserRole.participant,
    )
    db_session.add(participant)
    reg = Registration(
        hackathon_id=hackathon.id,
        user_id=participant.id,
        status=RegistrationStatus.pending,
    )
    db_session.add(reg)
    await db_session.commit()

    return hackathon, reg


@pytest_asyncio.fixture
async def coorganized_hackathon(clean_db: AsyncSession):
    """Create a hackathon where test-organizer-id is a co-organizer."""
    db_session = clean_db

    primary = User(
        id="primary-organizer-id",
        email="primary@example.com",
        name="Primary Organizer",
        role=UserRole.organizer,
    )
    db_session.add(primary)

    hackathon = Hackathon(
        name="Co-org Hackathon",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id="primary-organizer-id",
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)

    co_org = HackathonOrganizer(
        hackathon_id=hackathon.id,
        user_id="test-organizer-id",
        added_by="primary-organizer-id",
    )
    db_session.add(co_org)

    participant = User(
        id="coorg-participant",
        email="coorg-participant@example.com",
        name="Coorg Participant",
        role=UserRole.participant,
    )
    db_session.add(participant)
    reg = Registration(
        hackathon_id=hackathon.id,
        user_id=participant.id,
        status=RegistrationStatus.pending,
    )
    db_session.add(reg)
    await db_session.commit()

    return hackathon, reg


# ---------------------------------------------------------------------------
# LIST REGISTRATIONS
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_registrations(org_reg_client, owned_hackathon):
    hackathon = owned_hackathon
    resp = await org_reg_client.get(f"/api/hackathons/{hackathon.id}/registrations")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["registrations"]) == 5
    assert data["limit"] == 20
    assert data["offset"] == 0


@pytest.mark.asyncio
async def test_list_registrations_status_filter(org_reg_client, owned_hackathon):
    hackathon = owned_hackathon
    resp = await org_reg_client.get(f"/api/hackathons/{hackathon.id}/registrations?status=pending")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert all(r["status"] == "pending" for r in data["registrations"])


@pytest.mark.asyncio
async def test_list_registrations_pagination(org_reg_client, owned_hackathon):
    hackathon = owned_hackathon
    resp = await org_reg_client.get(f"/api/hackathons/{hackathon.id}/registrations?limit=2&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["registrations"]) == 2
    assert data["total"] == 5


@pytest.mark.asyncio
async def test_list_registrations_offset(org_reg_client, owned_hackathon):
    hackathon = owned_hackathon
    resp = await org_reg_client.get(f"/api/hackathons/{hackathon.id}/registrations?limit=2&offset=2")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["registrations"]) == 2
    assert data["offset"] == 2


# ---------------------------------------------------------------------------
# ACCEPT
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_accept_registration(org_reg_client, owned_hackathon, db_session):
    hackathon = owned_hackathon
    result = await db_session.execute(
        select(Registration).where(
            Registration.hackathon_id == hackathon.id,
            Registration.status == RegistrationStatus.pending,
        )
    )
    reg = result.scalars().first()

    with patch("app.services.event_service.publish_event", new_callable=AsyncMock):
        resp = await org_reg_client.post(f"/api/hackathons/{hackathon.id}/registrations/{reg.id}/accept")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "accepted"
        assert "qr_token" in data
        assert data["accepted_at"] is not None


@pytest.mark.asyncio
async def test_accept_non_pending_registration(org_reg_client, owned_hackathon, db_session):
    hackathon = owned_hackathon
    result = await db_session.execute(
        select(Registration).where(
            Registration.hackathon_id == hackathon.id,
            Registration.status == RegistrationStatus.accepted,
        )
    )
    reg = result.scalars().first()

    with patch("app.services.event_service.publish_event", new_callable=AsyncMock):
        resp = await org_reg_client.post(f"/api/hackathons/{hackathon.id}/registrations/{reg.id}/accept")
        assert resp.status_code == 409
        assert "Cannot accept" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_accept_registration_not_found(org_reg_client, owned_hackathon):
    hackathon = owned_hackathon
    fake_reg_id = "12345678-1234-1234-1234-123456789abc"

    with patch("app.services.event_service.publish_event", new_callable=AsyncMock):
        resp = await org_reg_client.post(f"/api/hackathons/{hackathon.id}/registrations/{fake_reg_id}/accept")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Registration not found"


@pytest.mark.asyncio
async def test_accept_registration_wrong_hackathon(org_reg_client, owned_hackathon, other_hackathon):
    owned_h = owned_hackathon
    other_h, other_reg = other_hackathon

    with patch("app.services.event_service.publish_event", new_callable=AsyncMock):
        resp = await org_reg_client.post(f"/api/hackathons/{owned_h.id}/registrations/{other_reg.id}/accept")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Registration not found"


# ---------------------------------------------------------------------------
# REJECT
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reject_pending_registration(org_reg_client, owned_hackathon, db_session):
    hackathon = owned_hackathon
    result = await db_session.execute(
        select(Registration).where(
            Registration.hackathon_id == hackathon.id,
            Registration.status == RegistrationStatus.pending,
        )
    )
    reg = result.scalars().first()

    resp = await org_reg_client.post(f"/api/hackathons/{hackathon.id}/registrations/{reg.id}/reject")
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_reject_accepted_registration_triggers_waitlist_promotion(org_reg_client, owned_hackathon, db_session):
    hackathon = owned_hackathon
    result = await db_session.execute(
        select(Registration).where(
            Registration.hackathon_id == hackathon.id,
            Registration.status == RegistrationStatus.accepted,
        )
    )
    reg = result.scalars().first()

    with patch("app.services.registration_service.promote_from_waitlist", new_callable=AsyncMock):
        resp = await org_reg_client.post(f"/api/hackathons/{hackathon.id}/registrations/{reg.id}/reject")
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_reject_non_rejectable_registration(org_reg_client, owned_hackathon, db_session):
    hackathon = owned_hackathon
    user = User(
        id="checked-in-user",
        email="checkedin@test.com",
        name="Checked In User",
        role=UserRole.participant,
    )
    db_session.add(user)
    reg = Registration(
        hackathon_id=hackathon.id,
        user_id=user.id,
        status=RegistrationStatus.checked_in,
        registered_at=datetime.now(UTC),
        checked_in_at=datetime.now(UTC),
    )
    db_session.add(reg)
    await db_session.commit()

    resp = await org_reg_client.post(f"/api/hackathons/{hackathon.id}/registrations/{reg.id}/reject")
    assert resp.status_code == 409
    assert "Cannot reject" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# CHECK-IN
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_checkin_registration(org_reg_client, owned_hackathon, db_session):
    hackathon = owned_hackathon
    result = await db_session.execute(
        select(Registration).where(
            Registration.hackathon_id == hackathon.id,
            Registration.status == RegistrationStatus.accepted,
        )
    )
    reg = result.scalars().first()

    with patch("app.services.event_service.publish_event", new_callable=AsyncMock):
        resp = await org_reg_client.post(f"/api/hackathons/{hackathon.id}/registrations/{reg.id}/checkin")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "checked_in"
        assert data["checked_in_at"] is not None


@pytest.mark.asyncio
async def test_checkin_non_accepted_registration(org_reg_client, owned_hackathon, db_session):
    hackathon = owned_hackathon
    result = await db_session.execute(
        select(Registration).where(
            Registration.hackathon_id == hackathon.id,
            Registration.status == RegistrationStatus.pending,
        )
    )
    reg = result.scalars().first()

    resp = await org_reg_client.post(f"/api/hackathons/{hackathon.id}/registrations/{reg.id}/checkin")
    assert resp.status_code == 409
    assert "Cannot check in" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# WAITLIST
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_move_to_waitlist(org_reg_client, owned_hackathon, db_session):
    hackathon = owned_hackathon
    result = await db_session.execute(
        select(Registration).where(
            Registration.hackathon_id == hackathon.id,
            Registration.status == RegistrationStatus.pending,
        )
    )
    reg = result.scalars().first()

    resp = await org_reg_client.post(f"/api/hackathons/{hackathon.id}/registrations/{reg.id}/waitlist")
    assert resp.status_code == 200
    assert resp.json()["status"] == "waitlisted"


@pytest.mark.asyncio
async def test_move_non_pending_to_waitlist(org_reg_client, owned_hackathon, db_session):
    hackathon = owned_hackathon
    result = await db_session.execute(
        select(Registration).where(
            Registration.hackathon_id == hackathon.id,
            Registration.status == RegistrationStatus.accepted,
        )
    )
    reg = result.scalars().first()

    resp = await org_reg_client.post(f"/api/hackathons/{hackathon.id}/registrations/{reg.id}/waitlist")
    assert resp.status_code == 409
    assert "Cannot waitlist" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_remove_from_waitlist(org_reg_client, owned_hackathon, db_session):
    hackathon = owned_hackathon
    result = await db_session.execute(
        select(Registration).where(
            Registration.hackathon_id == hackathon.id,
            Registration.status == RegistrationStatus.waitlisted,
        )
    )
    reg = result.scalars().first()

    resp = await org_reg_client.post(f"/api/hackathons/{hackathon.id}/registrations/{reg.id}/unwaitlist")
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"
    assert resp.json()["id"] == str(reg.id)


@pytest.mark.asyncio
async def test_unwaitlist_non_waitlisted(org_reg_client, owned_hackathon, db_session):
    hackathon = owned_hackathon
    result = await db_session.execute(
        select(Registration).where(
            Registration.hackathon_id == hackathon.id,
            Registration.status == RegistrationStatus.pending,
        )
    )
    reg = result.scalars().first()

    resp = await org_reg_client.post(f"/api/hackathons/{hackathon.id}/registrations/{reg.id}/unwaitlist")
    assert resp.status_code == 409
    assert "Cannot unwaitlist" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# MANUAL PROMOTE
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_manual_promote_waitlist(org_reg_client, owned_hackathon, db_session):
    hackathon = owned_hackathon

    with patch("app.services.registration_service.promote_from_waitlist", new_callable=AsyncMock) as mock_promote:
        mock_promote.return_value = type(
            "FakeReg",
            (),
            {
                "id": "promoted-id",
                "status": RegistrationStatus.offered,
                "offer_expires_at": datetime.now(UTC),
            },
        )()
        resp = await org_reg_client.post(f"/api/hackathons/{hackathon.id}/waitlist/promote")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "offered"
        assert "offer_expires_at" in data


@pytest.mark.asyncio
async def test_manual_promote_no_one_available(org_reg_client, owned_hackathon, db_session):
    hackathon = owned_hackathon

    with patch("app.services.registration_service.promote_from_waitlist", return_value=None):
        resp = await org_reg_client.post(f"/api/hackathons/{hackathon.id}/waitlist/promote")
        assert resp.status_code == 409
        assert "No one to promote" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# LIST WAITLIST
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_waitlist(org_reg_client, owned_hackathon):
    hackathon = owned_hackathon
    resp = await org_reg_client.get(f"/api/hackathons/{hackathon.id}/waitlist")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["waitlist"]) == 1
    assert data["waitlist"][0]["position"] == 1
    assert data["waitlist"][0]["declined_count"] == 0


@pytest.mark.asyncio
async def test_list_waitlist_pagination(org_reg_client, owned_hackathon):
    hackathon = owned_hackathon
    resp = await org_reg_client.get(f"/api/hackathons/{hackathon.id}/waitlist?limit=1&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["waitlist"]) == 1


# ---------------------------------------------------------------------------
# DIETARY REPORT
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dietary_report(org_reg_client, owned_hackathon, db_session):
    hackathon = owned_hackathon
    # Update the accepted registration with dietary restrictions
    result = await db_session.execute(
        select(Registration).where(
            Registration.hackathon_id == hackathon.id,
            Registration.status == RegistrationStatus.accepted,
        )
    )
    reg = result.scalars().first()
    reg.dietary_restrictions = "Vegan"
    await db_session.commit()

    resp = await org_reg_client.get(f"/api/hackathons/{hackathon.id}/registrations/dietary-report")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["summary"]["Vegan"] == 1
    assert len(data["participants"]) == 1
    assert data["participants"][0]["dietary_restrictions"] == "Vegan"


@pytest.mark.asyncio
async def test_dietary_report_aggregates_none(org_reg_client, owned_hackathon, db_session):
    hackathon = owned_hackathon
    # The accepted registration has no dietary restrictions set
    resp = await org_reg_client.get(f"/api/hackathons/{hackathon.id}/registrations/dietary-report")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["summary"]["None"] == 1


@pytest.mark.asyncio
async def test_dietary_report_non_organizer(org_reg_client, other_hackathon):
    hackathon, _ = other_hackathon
    resp = await org_reg_client.get(f"/api/hackathons/{hackathon.id}/registrations/dietary-report")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# EMERGENCY CONTACTS
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_emergency_contacts(org_reg_client, owned_hackathon, db_session):
    hackathon = owned_hackathon
    result = await db_session.execute(
        select(Registration).where(
            Registration.hackathon_id == hackathon.id,
            Registration.status == RegistrationStatus.accepted,
        )
    )
    reg = result.scalars().first()
    reg.phone = "555-1234"
    reg.emergency_contact_name = "Emergency Contact"
    reg.emergency_contact_phone = "555-5678"
    await db_session.commit()

    resp = await org_reg_client.get(f"/api/hackathons/{hackathon.id}/registrations/emergency-contacts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["contacts"]) == 1
    contact = data["contacts"][0]
    assert contact["phone"] == "555-1234"
    assert contact["emergency_contact_name"] == "Emergency Contact"
    assert contact["emergency_contact_phone"] == "555-5678"


@pytest.mark.asyncio
async def test_emergency_contacts_non_organizer(org_reg_client, other_hackathon):
    hackathon, _ = other_hackathon
    resp = await org_reg_client.get(f"/api/hackathons/{hackathon.id}/registrations/emergency-contacts")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PERMISSION CHECKS
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_non_organizer_gets_404(org_reg_client, other_hackathon):
    hackathon, _ = other_hackathon
    resp = await org_reg_client.get(f"/api/hackathons/{hackathon.id}/registrations")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Hackathon not found"


@pytest.mark.asyncio
async def test_coorganizer_can_access(org_reg_client, coorganized_hackathon):
    hackathon, reg = coorganized_hackathon
    resp = await org_reg_client.get(f"/api/hackathons/{hackathon.id}/registrations")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["registrations"][0]["id"] == str(reg.id)


@pytest.mark.asyncio
async def test_non_organizer_post_actions_return_404(org_reg_client, other_hackathon):
    hackathon, reg = other_hackathon
    resp = await org_reg_client.post(f"/api/hackathons/{hackathon.id}/registrations/{reg.id}/accept")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# CSV EXPORT (lives in hackathons.py but is part of organizer registration flow)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_registrations_csv(client, owned_hackathon):
    hackathon = owned_hackathon
    original = app.dependency_overrides.get(require_clerk_user_with_db)
    app.dependency_overrides[require_clerk_user_with_db] = _override_require_clerk_user_with_db_organizer
    try:
        resp = await client.get(f"/api/hackathons/{hackathon.id}/registrations/export")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")
        content = resp.content.decode("utf-8")
        reader = csv.reader(StringIO(content))
        rows = list(reader)
        assert len(rows) > 1
        assert rows[0][0] == "ID"
        # header + 5 registrations
        assert len(rows) == 6
    finally:
        if original is None:
            app.dependency_overrides.pop(require_clerk_user_with_db, None)
        else:
            app.dependency_overrides[require_clerk_user_with_db] = original


@pytest.mark.asyncio
async def test_export_registrations_csv_forbidden(client, owned_hackathon):
    hackathon = owned_hackathon
    # Default auth via client fixture is a participant, so _ensure_organizer should 403.
    resp = await client.get(f"/api/hackathons/{hackathon.id}/registrations/export")
    assert resp.status_code == 403
