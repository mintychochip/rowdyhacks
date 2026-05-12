"""Tests for team finder routes."""

import pytest
import pytest_asyncio
from fastapi import FastAPI, Header
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Hackathon, Registration, RegistrationStatus, User, UserRole
from app.routes.team_finder import router as team_finder_router

app = FastAPI()
app.include_router(team_finder_router)


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
async def team_finder_client(engine):
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
async def test_create_team_finder_post(team_finder_client, hackathon_with_reg):
    hackathon, _ = hackathon_with_reg
    resp = await team_finder_client.post(
        f"/api/hackathons/{hackathon.id}/team-finder",
        json={
            "post_type": "looking_for_team",
            "skills_needed": ["react", "design"],
            "description": "Looking for a team to build something cool",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["post_type"] == "looking_for_team"
    assert data["skills_needed"] == ["react", "design"]
    assert data["description"] == "Looking for a team to build something cool"
    assert data["is_active"] is True


@pytest.mark.anyio
async def test_create_team_finder_post_invalid_type(team_finder_client, hackathon_with_reg):
    hackathon, _ = hackathon_with_reg
    resp = await team_finder_client.post(
        f"/api/hackathons/{hackathon.id}/team-finder",
        json={
            "post_type": "invalid_type",
            "description": "Bad post",
        },
    )
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_list_team_finder_posts(team_finder_client, hackathon_with_reg):
    hackathon, _ = hackathon_with_reg
    create_resp = await team_finder_client.post(
        f"/api/hackathons/{hackathon.id}/team-finder",
        json={
            "post_type": "looking_for_members",
            "skills_needed": ["python"],
            "description": "We need a backend dev",
        },
    )
    assert create_resp.status_code == 201

    resp = await team_finder_client.get(f"/api/hackathons/{hackathon.id}/team-finder")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["post_type"] == "looking_for_members"
    assert data[0]["user_name"] == "Test User"


@pytest.mark.anyio
async def test_deactivate_team_finder_post(team_finder_client, hackathon_with_reg):
    hackathon, _ = hackathon_with_reg
    create_resp = await team_finder_client.post(
        f"/api/hackathons/{hackathon.id}/team-finder",
        json={
            "post_type": "looking_for_team",
            "description": "Solo hacker",
        },
    )
    post_id = create_resp.json()["id"]

    resp = await team_finder_client.delete(f"/api/hackathons/{hackathon.id}/team-finder/{post_id}")
    assert resp.status_code == 200
    assert resp.json()["deactivated"] is True

    list_resp = await team_finder_client.get(f"/api/hackathons/{hackathon.id}/team-finder")
    assert len(list_resp.json()) == 0


@pytest.mark.anyio
async def test_deactivate_team_finder_post_unauthorized(
    team_finder_client, hackathon_with_reg, db_session: AsyncSession
):

    hackathon, _ = hackathon_with_reg

    other_user = User(id="other-user-id", email="other@example.com", name="Other User", role=UserRole.participant)
    db_session.add(other_user)
    reg = Registration(
        hackathon_id=hackathon.id,
        user_id=other_user.id,
        status=RegistrationStatus.accepted,
    )
    db_session.add(reg)
    await db_session.commit()

    create_resp = await team_finder_client.post(
        f"/api/hackathons/{hackathon.id}/team-finder",
        json={"post_type": "looking_for_team", "description": "Other user's post"},
        headers={"Authorization": "Bearer test-other-user-id"},
    )
    post_id = create_resp.json()["id"]

    resp = await team_finder_client.delete(f"/api/hackathons/{hackathon.id}/team-finder/{post_id}")
    assert resp.status_code == 403
