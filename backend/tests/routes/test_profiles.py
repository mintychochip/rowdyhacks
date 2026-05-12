"""Tests for profile routes."""

import pytest
import pytest_asyncio
from fastapi import FastAPI, Header
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Hackathon, Registration, RegistrationStatus, User, UserRole
from app.routes.profiles import public_router as profiles_public_router
from app.routes.profiles import router as profiles_router

app = FastAPI()
app.include_router(profiles_router)
app.include_router(profiles_public_router)


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
async def profile_client(engine):
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

    user = User(
        id="test-user-id",
        email="test@example.com",
        name="Test User",
        role=UserRole.participant,
        bio="Hello world",
        skills=["python", "fastapi"],
        links={"github": "https://github.com/test"},
        availability="Weekends",
        looking_for_team=True,
    )
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
async def test_get_my_profile(profile_client, hackathon_with_reg):
    resp = await profile_client.get("/api/users/me/profile")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "test-user-id"
    assert data["bio"] == "Hello world"
    assert data["skills"] == ["python", "fastapi"]
    assert data["links"] == {"github": "https://github.com/test"}
    assert data["availability"] == "Weekends"
    assert data["looking_for_team"] is True


@pytest.mark.anyio
async def test_update_my_profile(profile_client, hackathon_with_reg):
    resp = await profile_client.put(
        "/api/users/me/profile",
        json={
            "bio": "Updated bio",
            "skills": ["javascript", "react"],
            "links": {"portfolio": "https://portfolio.dev"},
            "availability": "All day",
            "looking_for_team": False,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["bio"] == "Updated bio"
    assert data["skills"] == ["javascript", "react"]
    assert data["links"] == {"portfolio": "https://portfolio.dev"}
    assert data["availability"] == "All day"
    assert data["looking_for_team"] is False
    assert data["updated"] is True


@pytest.mark.anyio
async def test_list_participants(profile_client, hackathon_with_reg):
    hackathon, _ = hackathon_with_reg
    resp = await profile_client.get(f"/api/hackathons/{hackathon.id}/participants")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == "test-user-id"
    assert data[0]["name"] == "Test User"
    assert data[0]["bio"] == "Hello world"
