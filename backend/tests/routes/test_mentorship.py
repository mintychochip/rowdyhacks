"""Tests for mentorship routes."""

import pytest
import pytest_asyncio
from fastapi import FastAPI, Header
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Hackathon, MentorshipRequest, Registration, RegistrationStatus, User, UserRole
from app.routes.mentorship import router as mentorship_router

app = FastAPI()
app.include_router(mentorship_router)


async def _override_require_clerk_user(authorization: str | None = Header(alias="Authorization", default=None)):
    user_id = "test-user-id"
    email = "test@example.com"
    if authorization and authorization.startswith("Bearer test-"):
        parts = authorization.removeprefix("Bearer test-").split(":", 1)
        user_id = parts[0]
        if len(parts) > 1:
            email = parts[1]
    return {"sub": user_id, "email": email}


@pytest_asyncio.fixture
async def mentorship_client(engine):
    async_session_maker = __import__("sqlalchemy.ext.asyncio", fromlist=["async_sessionmaker"]).async_sessionmaker

    async def override_get_db():
        async with async_session_maker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
            yield session

    from app.clerk_auth import require_clerk_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_clerk_user] = _override_require_clerk_user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def hackathon_with_reg(db_session: AsyncSession):
    from datetime import UTC, datetime
    from sqlalchemy import delete

    await db_session.execute(delete(MentorshipRequest))
    await db_session.execute(delete(Registration))
    await db_session.execute(delete(Hackathon))
    await db_session.execute(delete(User))
    await db_session.commit()

    user = User(id="test-user-id", email="test@example.com", name="Test User", role=UserRole.participant)
    db_session.add(user)

    hackathon = Hackathon(
        name="Hack",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id="test-user-id",
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)

    reg = Registration(
        hackathon_id=hackathon.id,
        user_id=user.id,
        status=RegistrationStatus.accepted,
    )
    db_session.add(reg)
    await db_session.commit()

    return hackathon, user


@pytest.mark.anyio
async def test_request_mentor(mentorship_client, hackathon_with_reg):
    hackathon, _ = hackathon_with_reg
    resp = await mentorship_client.post(
        f"/api/hackathons/{hackathon.id}/mentorship/request",
        json={"topic": "Need help with FastAPI"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["topic"] == "Need help with FastAPI"
    assert data["status"] == "pending"
    assert data["requester_id"] == "test-user-id"


@pytest.mark.anyio
async def test_list_mentorship_requests(mentorship_client, hackathon_with_reg):
    hackathon, _ = hackathon_with_reg
    await mentorship_client.post(
        f"/api/hackathons/{hackathon.id}/mentorship/request",
        json={"topic": "Need help with React"},
    )

    resp = await mentorship_client.get(f"/api/hackathons/{hackathon.id}/mentorship/requests")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["topic"] == "Need help with React"
    assert data[0]["requester_name"] == "Test User"


@pytest.mark.anyio
async def test_accept_mentorship_request(mentorship_client, hackathon_with_reg, db_session: AsyncSession):

    hackathon, _ = hackathon_with_reg

    mentor = User(id="mentor-id", email="mentor@example.com", name="Mentor User", role=UserRole.participant)
    db_session.add(mentor)
    reg = Registration(
        hackathon_id=hackathon.id,
        user_id=mentor.id,
        status=RegistrationStatus.accepted,
    )
    db_session.add(reg)
    await db_session.commit()

    create_resp = await mentorship_client.post(
        f"/api/hackathons/{hackathon.id}/mentorship/request",
        json={"topic": "Help with deployment"},
    )
    request_id = create_resp.json()["id"]

    resp = await mentorship_client.post(
        f"/api/mentorship/{request_id}/accept",
        headers={"Authorization": "Bearer test-mentor-id"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "accepted"
    assert data["mentor_id"] == "mentor-id"
    assert data["updated"] is True


@pytest.mark.anyio
async def test_complete_mentorship_request(mentorship_client, hackathon_with_reg, db_session: AsyncSession):

    hackathon, _ = hackathon_with_reg

    mentor = User(id="mentor-id", email="mentor@example.com", name="Mentor User", role=UserRole.participant)
    db_session.add(mentor)
    reg = Registration(
        hackathon_id=hackathon.id,
        user_id=mentor.id,
        status=RegistrationStatus.accepted,
    )
    db_session.add(reg)
    await db_session.commit()

    create_resp = await mentorship_client.post(
        f"/api/hackathons/{hackathon.id}/mentorship/request",
        json={"topic": "Help with CSS"},
    )
    request_id = create_resp.json()["id"]

    await mentorship_client.post(
        f"/api/mentorship/{request_id}/accept",
        headers={"Authorization": "Bearer test-mentor-id"},
    )

    resp = await mentorship_client.post(f"/api/mentorship/{request_id}/complete")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["updated"] is True


@pytest.mark.anyio
async def test_complete_mentorship_request_unauthorized(
    mentorship_client, hackathon_with_reg, db_session: AsyncSession
):

    hackathon, _ = hackathon_with_reg

    other_user = User(id="other-id", email="other@example.com", name="Other User", role=UserRole.participant)
    db_session.add(other_user)
    reg = Registration(
        hackathon_id=hackathon.id,
        user_id=other_user.id,
        status=RegistrationStatus.accepted,
    )
    db_session.add(reg)
    await db_session.commit()

    create_resp = await mentorship_client.post(
        f"/api/hackathons/{hackathon.id}/mentorship/request",
        json={"topic": "Help with DB"},
    )
    request_id = create_resp.json()["id"]

    resp = await mentorship_client.post(
        f"/api/mentorship/{request_id}/complete",
        headers={"Authorization": "Bearer test-other-id"},
    )
    assert resp.status_code == 403
