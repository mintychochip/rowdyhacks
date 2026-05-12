"""Tests for admin routes."""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import AuditLog, Hackathon, Registration, RegistrationStatus, Team, TeamMember, User, UserRole
from app.routes.admin import router as admin_router

app = FastAPI()
app.include_router(admin_router)


@pytest_asyncio.fixture
async def admin_client(engine):
    async_session_maker = __import__("sqlalchemy.ext.asyncio", fromlist=["async_sessionmaker"]).async_sessionmaker

    async def override_get_db():
        async with async_session_maker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
            yield session

    from app.clerk_auth import require_clerk_user_with_db

    async def _override_organizer():
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

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_clerk_user_with_db] = _override_organizer
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_users(db_session: AsyncSession):
    await db_session.execute(delete(AuditLog))
    await db_session.execute(delete(TeamMember))
    await db_session.execute(delete(Team))
    await db_session.execute(delete(Registration))
    await db_session.execute(delete(Hackathon))
    await db_session.execute(delete(User))
    await db_session.commit()

    users = [
        User(id="user-1", email="alice@test.com", name="Alice", role=UserRole.participant),
        User(id="user-2", email="bob@test.com", name="Bob", role=UserRole.judge),
        User(id="user-3", email="carol@test.com", name="Carol", role=UserRole.organizer, is_banned=True),
    ]
    for u in users:
        db_session.add(u)
    await db_session.commit()
    return users


@pytest.mark.anyio
async def test_list_users(admin_client, admin_users):
    resp = await admin_client.get("/api/admin/users")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 3
    emails = {u["email"] for u in data["users"]}
    assert "alice@test.com" in emails


@pytest.mark.anyio
async def test_list_users_search(admin_client, admin_users):
    resp = await admin_client.get("/api/admin/users?search=alice")
    assert resp.status_code == 200
    data = resp.json()
    assert all("alice" in u["email"].lower() or "alice" in u["name"].lower() for u in data["users"])


@pytest.mark.anyio
async def test_list_users_filter_role(admin_client, admin_users):
    resp = await admin_client.get("/api/admin/users?role=judge")
    assert resp.status_code == 200
    data = resp.json()
    assert all(u["role"] == "judge" for u in data["users"])


@pytest.mark.anyio
async def test_list_users_filter_banned(admin_client, admin_users):
    resp = await admin_client.get("/api/admin/users?banned=true")
    assert resp.status_code == 200
    data = resp.json()
    assert all(u["is_banned"] is True for u in data["users"])


@pytest.mark.anyio
async def test_ban_user(admin_client, admin_users):
    resp = await admin_client.post("/api/admin/users/user-1/ban")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_banned"] is True
    assert data["banned_at"] is not None


@pytest.mark.anyio
async def test_unban_user(admin_client, admin_users):
    resp = await admin_client.post("/api/admin/users/user-3/unban")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_banned"] is False
    assert data["banned_at"] is None


@pytest.mark.anyio
async def test_change_role(admin_client, admin_users):
    resp = await admin_client.post("/api/admin/users/user-1/role", json={"role": "judge"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "judge"


@pytest.mark.anyio
async def test_change_role_invalid(admin_client, admin_users):
    resp = await admin_client.post("/api/admin/users/user-1/role", json={"role": "superuser"})
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_get_user_activity(admin_client, admin_users, db_session: AsyncSession):
    from datetime import UTC, datetime

    # Add some activity data
    hackathon = Hackathon(
        name="Activity Hack",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id="test-organizer-id",
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)

    reg = Registration(
        hackathon_id=hackathon.id,
        user_id="user-1",
        status=RegistrationStatus.accepted,
    )
    db_session.add(reg)
    await db_session.commit()

    resp = await admin_client.get("/api/admin/users/user-1/activity")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == "user-1"
    assert data["registrations"] == 1


@pytest.mark.anyio
async def test_admin_forbidden_for_participant(engine):
    async_session_maker = __import__("sqlalchemy.ext.asyncio", fromlist=["async_sessionmaker"]).async_sessionmaker

    async def override_get_db():
        async with async_session_maker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
            yield session

    from app.clerk_auth import require_clerk_user_with_db

    async def _override_participant():
        fake_user = type(
            "FakeUser",
            (),
            {
                "role": UserRole.participant,
                "id": "test-participant-id",
                "email": "part@test.com",
                "name": "Part",
            },
        )()
        return {
            "user": fake_user,
            "sub": "test-participant-id",
            "email": "part@test.com",
            "payload": {},
        }

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_clerk_user_with_db] = _override_participant
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/admin/users")
        assert resp.status_code == 403
    app.dependency_overrides.clear()
