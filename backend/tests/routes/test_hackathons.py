"""Tests for hackathon routes."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.clerk_auth import require_clerk_user_with_db
from app.database import get_db
from app.main import app
from app.models import (
    Announcement,
    ConflictOfInterest,
    Hackathon,
    HackathonOrganizer,
    Registration,
    RegistrationStatus,
    Submission,
    SubmissionStatus,
    User,
    UserRole,
    Verdict,
)


# --- Helpers ---


async def _clean_tables(db: AsyncSession):
    """Remove all rows from tables managed by these tests."""
    await db.execute(delete(ConflictOfInterest))
    await db.execute(delete(Announcement))
    await db.execute(delete(HackathonOrganizer))
    await db.execute(delete(Registration))
    await db.execute(delete(Submission))
    await db.execute(delete(Hackathon))
    await db.execute(delete(User))
    await db.commit()


async def _create_user(db: AsyncSession, email: str, name: str, role: UserRole) -> User:
    user = User(email=email, name=name, role=role)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _create_hackathon(db: AsyncSession, name: str, organizer_id: str | None = None) -> Hackathon:
    now = datetime.now(UTC)
    h = Hackathon(
        name=name,
        start_date=now,
        end_date=now + timedelta(days=1),
        organizer_id=organizer_id,
    )
    db.add(h)
    await db.commit()
    await db.refresh(h)
    return h


async def _create_registration(
    db: AsyncSession, hackathon_id: uuid.UUID, user_id: str, status: RegistrationStatus = RegistrationStatus.accepted
) -> Registration:
    reg = Registration(hackathon_id=hackathon_id, user_id=user_id, status=status)
    db.add(reg)
    await db.commit()
    await db.refresh(reg)
    return reg


async def _create_submission(db: AsyncSession, hackathon_id: uuid.UUID, title: str, url: str) -> Submission:
    s = Submission(
        devpost_url=url,
        project_title=title,
        hackathon_id=hackathon_id,
        status=SubmissionStatus.completed,
        risk_score=20,
        verdict=Verdict.clean,
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def _create_announcement(
    db: AsyncSession,
    hackathon_id: uuid.UUID,
    title: str,
    content: str,
    sent_by: str,
    priority: str = "normal",
) -> Announcement:
    a = Announcement(hackathon_id=hackathon_id, title=title, content=content, priority=priority, sent_by=sent_by)
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return a


async def _create_coi(
    db: AsyncSession, hackathon_id: uuid.UUID, judge_id: str, submission_id: uuid.UUID, reason: str = "conflict"
) -> ConflictOfInterest:
    coi = ConflictOfInterest(hackathon_id=hackathon_id, judge_id=judge_id, submission_id=submission_id, reason=reason)
    db.add(coi)
    await db.commit()
    await db.refresh(coi)
    return coi


# --- Fixtures ---


@pytest_asyncio.fixture
async def organizer_client(engine):
    """Async client authenticated as an organizer."""
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with async_session_maker() as session:
            yield session

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

    async def override_auth():
        return {
            "user": fake_user,
            "sub": "test-organizer-id",
            "email": "organizer@test.com",
            "payload": {},
        }

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_clerk_user_with_db] = override_auth
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def judge_client(engine):
    """Async client authenticated as a judge."""
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with async_session_maker() as session:
            yield session

    fake_user = type(
        "FakeUser",
        (),
        {
            "role": UserRole.judge,
            "id": "test-judge-id",
            "email": "judge@test.com",
            "name": "Test Judge",
        },
    )()

    async def override_auth():
        return {
            "user": fake_user,
            "sub": "test-judge-id",
            "email": "judge@test.com",
            "payload": {},
        }

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_clerk_user_with_db] = override_auth
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# --- Create Hackathon ---


@pytest.mark.asyncio
async def test_create_hackathon_as_organizer(organizer_client: AsyncClient, db_session: AsyncSession):
    await _clean_tables(db_session)
    now = datetime.now(UTC)
    resp = await organizer_client.post(
        "/api/hackathons",
        json={
            "name": "Test Hackathon",
            "start_date": now.isoformat(),
            "end_date": (now + timedelta(days=1)).isoformat(),
            "description": "A test hackathon",
            "max_participants": 100,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Hackathon"
    assert data["max_participants"] == 100


@pytest.mark.asyncio
async def test_create_hackathon_one_per_portal(organizer_client: AsyncClient, db_session: AsyncSession):
    await _clean_tables(db_session)
    now = datetime.now(UTC)
    # Create first hackathon
    resp1 = await organizer_client.post(
        "/api/hackathons",
        json={
            "name": "First Hackathon",
            "start_date": now.isoformat(),
            "end_date": (now + timedelta(days=1)).isoformat(),
        },
    )
    assert resp1.status_code == 201

    # Try second — should fail
    resp2 = await organizer_client.post(
        "/api/hackathons",
        json={
            "name": "Second Hackathon",
            "start_date": now.isoformat(),
            "end_date": (now + timedelta(days=1)).isoformat(),
        },
    )
    assert resp2.status_code == 400
    assert "already exists" in resp2.json()["detail"]


@pytest.mark.asyncio
async def test_create_hackathon_as_participant(client: AsyncClient, db_session: AsyncSession):
    await _clean_tables(db_session)
    now = datetime.now(UTC)
    resp = await client.post(
        "/api/hackathons",
        json={
            "name": "Test Hackathon",
            "start_date": now.isoformat(),
            "end_date": (now + timedelta(days=1)).isoformat(),
        },
    )
    assert resp.status_code == 403


# --- List Hackathons ---


@pytest.mark.asyncio
async def test_list_hackathons(client: AsyncClient, db_session: AsyncSession):
    await _clean_tables(db_session)
    user = await _create_user(db_session, "org@test.com", "Org", UserRole.organizer)
    h1 = await _create_hackathon(db_session, "Hack A", organizer_id=user.id)
    h2 = await _create_hackathon(db_session, "Hack B", organizer_id=user.id)

    resp = await client.get("/api/hackathons")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    names = {h["name"] for h in data}
    assert names == {"Hack A", "Hack B"}


# --- Get Single Hackathon ---


@pytest.mark.asyncio
async def test_get_hackathon(client: AsyncClient, db_session: AsyncSession):
    await _clean_tables(db_session)
    user = await _create_user(db_session, "org@test.com", "Org", UserRole.organizer)
    h = await _create_hackathon(db_session, "Target Hack", organizer_id=user.id)

    resp = await client.get(f"/api/hackathons/{h.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Target Hack"
    assert data["organizer_id"] == str(user.id)


@pytest.mark.asyncio
async def test_get_hackathon_not_found(client: AsyncClient, db_session: AsyncSession):
    await _clean_tables(db_session)
    resp = await client.get(f"/api/hackathons/{uuid.uuid4()}")
    assert resp.status_code == 404


# --- Update Hackathon ---


@pytest.mark.asyncio
async def test_update_hackathon(organizer_client: AsyncClient, db_session: AsyncSession):
    await _clean_tables(db_session)
    h = await _create_hackathon(db_session, "Old Name", organizer_id="test-organizer-id")

    resp = await organizer_client.put(
        f"/api/hackathons/{h.id}",
        json={"description": "Updated description", "venue_address": "123 Main St"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "description" in data["updated"]
    assert "venue_address" in data["updated"]


@pytest.mark.asyncio
async def test_update_hackathon_not_organizer(client: AsyncClient, db_session: AsyncSession):
    await _clean_tables(db_session)
    user = await _create_user(db_session, "org@test.com", "Org", UserRole.organizer)
    h = await _create_hackathon(db_session, "Target", organizer_id=user.id)

    resp = await client.put(f"/api/hackathons/{h.id}", json={"description": "Should fail"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_hackathon_not_found(organizer_client: AsyncClient, db_session: AsyncSession):
    await _clean_tables(db_session)
    resp = await organizer_client.put(f"/api/hackathons/{uuid.uuid4()}", json={"description": "Nope"})
    assert resp.status_code == 404


# --- Announcements ---


@pytest.mark.asyncio
async def test_create_announcement(organizer_client: AsyncClient, db_session: AsyncSession):
    await _clean_tables(db_session)
    h = await _create_hackathon(db_session, "Target", organizer_id="test-organizer-id")

    resp = await organizer_client.post(
        f"/api/hackathons/{h.id}/announcements",
        json={"title": "Hello", "content": "World", "priority": "high"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Hello"
    assert data["content"] == "World"
    assert data["priority"] == "high"


@pytest.mark.asyncio
async def test_list_announcements_as_organizer(organizer_client: AsyncClient, db_session: AsyncSession):
    await _clean_tables(db_session)
    h = await _create_hackathon(db_session, "Target", organizer_id="test-organizer-id")
    await _create_announcement(db_session, h.id, "Public", "Body", "test-organizer-id", "normal")
    await _create_announcement(db_session, h.id, "Draft", "Secret", "test-organizer-id", "draft")

    resp = await organizer_client.get(f"/api/hackathons/{h.id}/announcements")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    titles = {a["title"] for a in data}
    assert titles == {"Public", "Draft"}


@pytest.mark.asyncio
async def test_list_announcements_as_participant(client: AsyncClient, db_session: AsyncSession):
    await _clean_tables(db_session)
    user = await _create_user(db_session, "org@test.com", "Org", UserRole.organizer)
    participant = await _create_user(db_session, "part@test.com", "Participant", UserRole.participant)
    h = await _create_hackathon(db_session, "Target", organizer_id=user.id)
    # Create registration for the test participant (sub="test-user-id")
    await _create_registration(db_session, h.id, "test-user-id", RegistrationStatus.accepted)
    await _create_announcement(db_session, h.id, "Public", "Body", user.id, "normal")
    await _create_announcement(db_session, h.id, "Draft", "Secret", user.id, "draft")

    resp = await client.get(f"/api/hackathons/{h.id}/announcements")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Public"


@pytest.mark.asyncio
async def test_list_announcements_unauthorized(client: AsyncClient, db_session: AsyncSession):
    await _clean_tables(db_session)
    user = await _create_user(db_session, "org@test.com", "Org", UserRole.organizer)
    h = await _create_hackathon(db_session, "Target", organizer_id=user.id)
    await _create_announcement(db_session, h.id, "Public", "Body", user.id, "normal")

    resp = await client.get(f"/api/hackathons/{h.id}/announcements")
    assert resp.status_code == 403


# --- Conflict of Interest ---


@pytest.mark.asyncio
async def test_declare_conflict_of_interest(judge_client: AsyncClient, db_session: AsyncSession):
    await _clean_tables(db_session)
    h = await _create_hackathon(db_session, "Target", organizer_id="test-organizer-id")
    sub = await _create_submission(db_session, h.id, "Project Alpha", "https://devpost.com/alpha")

    resp = await judge_client.post(
        f"/api/hackathons/{h.id}/conflicts-of-interest",
        json={"submission_id": str(sub.id), "reason": "I know the team"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["submission_id"] == str(sub.id)
    assert data["reason"] == "I know the team"


@pytest.mark.asyncio
async def test_declare_coi_duplicate(judge_client: AsyncClient, db_session: AsyncSession):
    await _clean_tables(db_session)
    h = await _create_hackathon(db_session, "Target", organizer_id="test-organizer-id")
    sub = await _create_submission(db_session, h.id, "Project Alpha", "https://devpost.com/alpha")

    resp1 = await judge_client.post(
        f"/api/hackathons/{h.id}/conflicts-of-interest",
        json={"submission_id": str(sub.id), "reason": "First"},
    )
    assert resp1.status_code == 201

    resp2 = await judge_client.post(
        f"/api/hackathons/{h.id}/conflicts-of-interest",
        json={"submission_id": str(sub.id), "reason": "Second"},
    )
    assert resp2.status_code == 409
    assert "already declared" in resp2.json()["detail"]


@pytest.mark.asyncio
async def test_declare_coi_as_participant(client: AsyncClient, db_session: AsyncSession):
    await _clean_tables(db_session)
    h = await _create_hackathon(db_session, "Target", organizer_id="test-organizer-id")
    sub = await _create_submission(db_session, h.id, "Project Alpha", "https://devpost.com/alpha")

    resp = await client.post(
        f"/api/hackathons/{h.id}/conflicts-of-interest",
        json={"submission_id": str(sub.id), "reason": "Should fail"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_conflicts_of_interest(organizer_client: AsyncClient, db_session: AsyncSession):
    await _clean_tables(db_session)
    h = await _create_hackathon(db_session, "Target", organizer_id="test-organizer-id")
    sub = await _create_submission(db_session, h.id, "Project Alpha", "https://devpost.com/alpha")
    await _create_coi(db_session, h.id, "test-judge-id", sub.id, "Conflict reason")

    resp = await organizer_client.get(f"/api/hackathons/{h.id}/conflicts-of-interest")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["reason"] == "Conflict reason"


@pytest.mark.asyncio
async def test_remove_conflict_of_interest(organizer_client: AsyncClient, db_session: AsyncSession):
    await _clean_tables(db_session)
    h = await _create_hackathon(db_session, "Target", organizer_id="test-organizer-id")
    sub = await _create_submission(db_session, h.id, "Project Alpha", "https://devpost.com/alpha")
    coi = await _create_coi(db_session, h.id, "test-judge-id", sub.id, "Conflict reason")

    resp = await organizer_client.delete(f"/api/hackathons/{h.id}/conflicts-of-interest/{coi.id}")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True


# --- Stats & Submissions ---


@pytest.mark.asyncio
async def test_get_hackathon_stats(client: AsyncClient, db_session: AsyncSession):
    await _clean_tables(db_session)
    user = await _create_user(db_session, "org@test.com", "Org", UserRole.organizer)
    h = await _create_hackathon(db_session, "Target", organizer_id=user.id)
    await _create_submission(db_session, h.id, "Project A", "https://devpost.com/a")
    await _create_submission(db_session, h.id, "Project B", "https://devpost.com/b")
    participant = await _create_user(db_session, "part@test.com", "Part", UserRole.participant)
    await _create_registration(db_session, h.id, participant.id, RegistrationStatus.accepted)

    resp = await client.get(f"/api/hackathons/{h.id}/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_submissions"] == 2
    assert data["registrations"]["accepted"] == 1


@pytest.mark.asyncio
async def test_get_hackathon_submissions(client: AsyncClient, db_session: AsyncSession):
    await _clean_tables(db_session)
    user = await _create_user(db_session, "org@test.com", "Org", UserRole.organizer)
    h = await _create_hackathon(db_session, "Target", organizer_id=user.id)
    await _create_submission(db_session, h.id, "Project A", "https://devpost.com/a")
    await _create_submission(db_session, h.id, "Project B", "https://devpost.com/b")

    resp = await client.get(f"/api/hackathons/{h.id}/submissions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    titles = {s["project_title"] for s in data}
    assert titles == {"Project A", "Project B"}


@pytest.mark.asyncio
async def test_get_swag_counts(organizer_client: AsyncClient, db_session: AsyncSession):
    await _clean_tables(db_session)
    h = await _create_hackathon(db_session, "Target", organizer_id="test-organizer-id")
    participant = await _create_user(db_session, "part@test.com", "Part", UserRole.participant)
    reg = await _create_registration(db_session, h.id, participant.id, RegistrationStatus.accepted)
    reg.t_shirt_size = "M"
    reg.dietary_restrictions = "Vegan"
    reg.experience_level = "Beginner"
    await db_session.commit()

    resp = await organizer_client.get(f"/api/hackathons/{h.id}/swag-counts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_accepted"] == 1
    assert data["t_shirt_sizes"]["M"] == 1
    assert data["dietary_restrictions"]["Vegan"] == 1
    assert data["experience_levels"]["Beginner"] == 1


# --- Bulk Registration Operations ---


@pytest.mark.asyncio
async def test_bulk_accept_registrations(organizer_client: AsyncClient, db_session: AsyncSession):
    await _clean_tables(db_session)
    h = await _create_hackathon(db_session, "Target", organizer_id="test-organizer-id")
    p1 = await _create_user(db_session, "p1@test.com", "P1", UserRole.participant)
    p2 = await _create_user(db_session, "p2@test.com", "P2", UserRole.participant)
    reg1 = await _create_registration(db_session, h.id, p1.id, RegistrationStatus.pending)
    reg2 = await _create_registration(db_session, h.id, p2.id, RegistrationStatus.pending)

    resp = await organizer_client.post(
        f"/api/hackathons/{h.id}/registrations/bulk-accept",
        json=[str(reg1.id), str(reg2.id)],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["accepted"] == 2
    assert data["waitlisted"] == 0


@pytest.mark.asyncio
async def test_bulk_reject_registrations(organizer_client: AsyncClient, db_session: AsyncSession):
    await _clean_tables(db_session)
    h = await _create_hackathon(db_session, "Target", organizer_id="test-organizer-id")
    p1 = await _create_user(db_session, "p1@test.com", "P1", UserRole.participant)
    reg1 = await _create_registration(db_session, h.id, p1.id, RegistrationStatus.pending)

    resp = await organizer_client.post(
        f"/api/hackathons/{h.id}/registrations/bulk-reject",
        json=[str(reg1.id)],
    )
    assert resp.status_code == 200
    assert resp.json()["rejected"] == 1


@pytest.mark.asyncio
async def test_bulk_waitlist_registrations(organizer_client: AsyncClient, db_session: AsyncSession):
    await _clean_tables(db_session)
    h = await _create_hackathon(db_session, "Target", organizer_id="test-organizer-id")
    h.waitlist_enabled = True
    await db_session.commit()
    p1 = await _create_user(db_session, "p1@test.com", "P1", UserRole.participant)
    reg1 = await _create_registration(db_session, h.id, p1.id, RegistrationStatus.pending)

    resp = await organizer_client.post(
        f"/api/hackathons/{h.id}/registrations/bulk-waitlist",
        json=[str(reg1.id)],
    )
    assert resp.status_code == 200
    assert resp.json()["waitlisted"] == 1


# --- Export ---


@pytest.mark.asyncio
async def test_export_registrations_csv(organizer_client: AsyncClient, db_session: AsyncSession):
    await _clean_tables(db_session)
    h = await _create_hackathon(db_session, "Target", organizer_id="test-organizer-id")
    p1 = await _create_user(db_session, "p1@test.com", "P1", UserRole.participant)
    await _create_registration(db_session, h.id, p1.id, RegistrationStatus.accepted)

    resp = await organizer_client.get(f"/api/hackathons/{h.id}/registrations/export")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "text/csv; charset=utf-8"
    body = resp.content.decode()
    assert "ID,Status,Registered At" in body
    assert "accepted" in body


# --- Organizers ---


@pytest.mark.asyncio
async def test_list_organizers(organizer_client: AsyncClient, db_session: AsyncSession):
    await _clean_tables(db_session)
    # Primary organizer must exist in DB because the route queries User by organizer_id
    db_org = User(id="test-organizer-id", email="organizer@test.com", name="Test Organizer", role=UserRole.organizer)
    db_session.add(db_org)
    await db_session.commit()
    h = await _create_hackathon(db_session, "Target", organizer_id="test-organizer-id")

    resp = await organizer_client.get(f"/api/hackathons/{h.id}/organizers")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["organizers"]) == 1
    assert data["organizers"][0]["role"] == "primary"


@pytest.mark.asyncio
async def test_add_organizer(organizer_client: AsyncClient, db_session: AsyncSession):
    await _clean_tables(db_session)
    db_org = User(id="test-organizer-id", email="organizer@test.com", name="Test Organizer", role=UserRole.organizer)
    db_session.add(db_org)
    await db_session.commit()
    h = await _create_hackathon(db_session, "Target", organizer_id="test-organizer-id")
    co_org = await _create_user(db_session, "co@test.com", "Co-Organizer", UserRole.organizer)

    resp = await organizer_client.post(
        f"/api/hackathons/{h.id}/organizers",
        json={"email": "co@test.com"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "co@test.com"
    assert data["role"] == "co-organizer"


@pytest.mark.asyncio
async def test_remove_organizer(organizer_client: AsyncClient, db_session: AsyncSession):
    await _clean_tables(db_session)
    db_org = User(id="test-organizer-id", email="organizer@test.com", name="Test Organizer", role=UserRole.organizer)
    db_session.add(db_org)
    await db_session.commit()
    h = await _create_hackathon(db_session, "Target", organizer_id="test-organizer-id")
    co_org = await _create_user(db_session, "co@test.com", "Co-Organizer", UserRole.organizer)
    co = HackathonOrganizer(hackathon_id=h.id, user_id=co_org.id, added_by="test-organizer-id")
    db_session.add(co)
    await db_session.commit()

    resp = await organizer_client.delete(f"/api/hackathons/{h.id}/organizers/{co_org.id}")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True


# --- Similarity ---


@pytest.mark.asyncio
async def test_run_similarity(organizer_client: AsyncClient, db_session: AsyncSession):
    from unittest.mock import patch

    await _clean_tables(db_session)
    db_org = User(id="test-organizer-id", email="organizer@test.com", name="Test Organizer", role=UserRole.organizer)
    db_session.add(db_org)
    await db_session.commit()
    h = await _create_hackathon(db_session, "Target", organizer_id="test-organizer-id")
    await _create_submission(db_session, h.id, "Project A", "https://devpost.com/a")
    await _create_submission(db_session, h.id, "Project B", "https://devpost.com/b")

    with patch("app.routes.hackathons.run_similarity", return_value={"checked": 2, "similar": 0}):
        resp = await organizer_client.post(f"/api/hackathons/{h.id}/similarity")
        assert resp.status_code == 200
        assert resp.json()["checked"] == 2


# --- Email Blast ---


@pytest.mark.asyncio
async def test_email_blast_accepted(organizer_client: AsyncClient, db_session: AsyncSession):
    from unittest.mock import AsyncMock, patch

    await _clean_tables(db_session)
    db_org = User(id="test-organizer-id", email="organizer@test.com", name="Test Organizer", role=UserRole.organizer)
    db_session.add(db_org)
    await db_session.commit()
    h = await _create_hackathon(db_session, "Blast Hack", organizer_id="test-organizer-id")

    for i in range(2):
        u = await _create_user(db_session, f"user-{i}@example.com", f"User {i}", UserRole.participant)
        await _create_registration(db_session, h.id, u.id, RegistrationStatus.accepted)

    with patch("app.services.email_blast_service.send_email_with_retry", new_callable=AsyncMock, return_value=True):
        resp = await organizer_client.post(
            f"/api/hackathons/{h.id}/email-blast",
            json={"subject": "Hello", "body": "World", "cohort": "accepted"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["cohort"] == "accepted"
    assert data["sent"] == 2
    assert data["failed"] == 0


@pytest.mark.asyncio
async def test_email_blast_waitlist(organizer_client: AsyncClient, db_session: AsyncSession):
    from unittest.mock import AsyncMock, patch

    await _clean_tables(db_session)
    db_org = User(id="test-organizer-id", email="organizer@test.com", name="Test Organizer", role=UserRole.organizer)
    db_session.add(db_org)
    await db_session.commit()
    h = await _create_hackathon(db_session, "Blast Hack", organizer_id="test-organizer-id")

    for i in range(2):
        u = await _create_user(db_session, f"user-{i}@example.com", f"User {i}", UserRole.participant)
        await _create_registration(db_session, h.id, u.id, RegistrationStatus.waitlisted)

    with patch("app.services.email_blast_service.send_email_with_retry", new_callable=AsyncMock, return_value=True):
        resp = await organizer_client.post(
            f"/api/hackathons/{h.id}/email-blast",
            json={"subject": "Hello", "body": "World", "cohort": "waitlist"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["cohort"] == "waitlist"
    assert data["sent"] == 2
    assert data["failed"] == 0


@pytest.mark.asyncio
async def test_email_blast_checked_in(organizer_client: AsyncClient, db_session: AsyncSession):
    from unittest.mock import AsyncMock, patch

    await _clean_tables(db_session)
    db_org = User(id="test-organizer-id", email="organizer@test.com", name="Test Organizer", role=UserRole.organizer)
    db_session.add(db_org)
    await db_session.commit()
    h = await _create_hackathon(db_session, "Blast Hack", organizer_id="test-organizer-id")

    for i in range(3):
        u = await _create_user(db_session, f"user-{i}@example.com", f"User {i}", UserRole.participant)
        await _create_registration(db_session, h.id, u.id, RegistrationStatus.checked_in)

    with patch("app.services.email_blast_service.send_email_with_retry", new_callable=AsyncMock, return_value=True):
        resp = await organizer_client.post(
            f"/api/hackathons/{h.id}/email-blast",
            json={"subject": "Hello", "body": "World", "cohort": "checked_in"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["cohort"] == "checked_in"
    assert data["sent"] == 3
    assert data["failed"] == 0


@pytest.mark.asyncio
async def test_email_blast_track(organizer_client: AsyncClient, db_session: AsyncSession):
    from unittest.mock import AsyncMock, patch

    from app.models import Track

    await _clean_tables(db_session)
    db_org = User(id="test-organizer-id", email="organizer@test.com", name="Test Organizer", role=UserRole.organizer)
    db_session.add(db_org)
    await db_session.commit()
    h = await _create_hackathon(db_session, "Blast Hack", organizer_id="test-organizer-id")

    track = Track(
        hackathon_id=h.id,
        name="AI Track",
        description="AI",
        challenge="Use ML",
        icon="🤖",
        color="#10b981",
        prize="Prize",
        track_type="themed",
        criteria=["Innovation"],
        resources=[],
    )
    db_session.add(track)
    await db_session.commit()
    await db_session.refresh(track)

    for i in range(2):
        u = await _create_user(db_session, f"user-{i}@example.com", f"User {i}", UserRole.participant)
        reg = Registration(hackathon_id=h.id, user_id=u.id, status=RegistrationStatus.accepted, track_id=track.id)
        db_session.add(reg)
    await db_session.commit()

    with patch("app.services.email_blast_service.send_email_with_retry", new_callable=AsyncMock, return_value=True):
        resp = await organizer_client.post(
            f"/api/hackathons/{h.id}/email-blast",
            json={"subject": "Hello", "body": "World", "cohort": "track", "track_id": str(track.id)},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["cohort"] == "track"
    assert data["sent"] == 2
    assert data["failed"] == 0


@pytest.mark.asyncio
async def test_email_blast_non_organizer(judge_client: AsyncClient, db_session: AsyncSession):
    from unittest.mock import AsyncMock, patch

    await _clean_tables(db_session)
    db_org = User(id="test-organizer-id", email="organizer@test.com", name="Test Organizer", role=UserRole.organizer)
    db_session.add(db_org)
    await db_session.commit()
    h = await _create_hackathon(db_session, "Blast Hack", organizer_id="test-organizer-id")

    with patch("app.services.email_blast_service.send_email_with_retry", new_callable=AsyncMock, return_value=True):
        resp = await judge_client.post(
            f"/api/hackathons/{h.id}/email-blast",
            json={"subject": "Hello", "body": "World", "cohort": "accepted"},
        )
    assert resp.status_code == 403
