"""Auth route tests for self-hosted local auth endpoints."""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import hash_password
from app.main import app
from app.models import User, UserRole


@pytest_asyncio.fixture(autouse=True)
async def clean_db(engine):
    """Truncate users and refresh_tokens tables before each test."""
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM refresh_tokens"))
        await conn.execute(text("DELETE FROM oauth_accounts"))
        await conn.execute(text("DELETE FROM users"))
    yield


@pytest_asyncio.fixture
async def organizer_user(engine):
    """Create an organizer user directly in the test DB."""
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as db:
        user = User(
            email="organizer@example.com",
            name="Organizer",
            role=UserRole.organizer,
            password_hash=hash_password("Organizer123"),
            email_verified=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        yield user


@pytest.mark.asyncio
async def test_register_new_user(client, clean_db, organizer_user):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        res = await ac.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "Password123",
                "name": "New User",
            },
        )
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "newuser@example.com"
    assert data["role"] == "participant"


@pytest.mark.asyncio
async def test_register_blocked_until_organizer_exists(client, clean_db):
    # This test assumes DB is empty at start — will need conftest setup
    async with AsyncClient(app=app, base_url="http://test") as ac:
        res = await ac.post(
            "/api/auth/register",
            json={
                "email": "first@example.com",
                "password": "Password123",
                "name": "First",
            },
        )
    assert res.status_code == 403
    assert "organizer" in res.json()["detail"]


@pytest.mark.asyncio
async def test_register_duplicate_email(client, clean_db, organizer_user):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        res = await ac.post(
            "/api/auth/register",
            json={
                "email": "dup@example.com",
                "password": "Password123",
                "name": "Dup",
            },
        )
    assert res.status_code == 201

    async with AsyncClient(app=app, base_url="http://test") as ac:
        res = await ac.post(
            "/api/auth/register",
            json={
                "email": "dup@example.com",
                "password": "Password123",
                "name": "Dup2",
            },
        )
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_register_weak_password(client, clean_db, organizer_user):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        res = await ac.post(
            "/api/auth/register",
            json={
                "email": "weak@example.com",
                "password": "weak",
                "name": "Weak",
            },
        )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client, clean_db, organizer_user):
    # Create a participant
    async with AsyncClient(app=app, base_url="http://test") as ac:
        await ac.post(
            "/api/auth/register",
            json={
                "email": "login@example.com",
                "password": "Password123",
                "name": "Login User",
            },
        )

    async with AsyncClient(app=app, base_url="http://test") as ac:
        res = await ac.post(
            "/api/auth/login",
            json={
                "email": "login@example.com",
                "password": "Password123",
            },
        )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "refresh_token" in res.cookies


@pytest.mark.asyncio
async def test_login_invalid_credentials(client, clean_db, organizer_user):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        res = await ac.post(
            "/api/auth/login",
            json={
                "email": "nope@example.com",
                "password": "Password123",
            },
        )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_rotation(client, clean_db, organizer_user):
    # Register and login to get a refresh token
    async with AsyncClient(app=app, base_url="http://test") as ac:
        await ac.post(
            "/api/auth/register",
            json={
                "email": "refresh@example.com",
                "password": "Password123",
                "name": "Refresh User",
            },
        )
        login_res = await ac.post(
            "/api/auth/login",
            json={
                "email": "refresh@example.com",
                "password": "Password123",
            },
        )
    assert login_res.status_code == 200
    old_refresh = login_res.cookies["refresh_token"]

    async with AsyncClient(app=app, base_url="http://test") as ac:
        ac.cookies.set("refresh_token", old_refresh)
        res = await ac.post("/api/auth/refresh")
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "refresh_token" in res.cookies
    new_refresh = res.cookies["refresh_token"]
    assert new_refresh != old_refresh


@pytest.mark.asyncio
async def test_refresh_invalid_token(client, clean_db):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        ac.cookies.set("refresh_token", "invalid-token")
        res = await ac.post("/api/auth/refresh")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(client, clean_db, organizer_user):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        await ac.post(
            "/api/auth/register",
            json={
                "email": "logout@example.com",
                "password": "Password123",
                "name": "Logout User",
            },
        )
        login_res = await ac.post(
            "/api/auth/login",
            json={
                "email": "logout@example.com",
                "password": "Password123",
            },
        )
    refresh = login_res.cookies["refresh_token"]

    async with AsyncClient(app=app, base_url="http://test") as ac:
        ac.cookies.set("refresh_token", refresh)
        res = await ac.post("/api/auth/logout")
    assert res.status_code == 200
    # Cookie may be None or empty string after clearing
    assert not res.cookies.get("refresh_token")

    # Refresh should fail after logout
    async with AsyncClient(app=app, base_url="http://test") as ac:
        ac.cookies.set("refresh_token", refresh)
        res = await ac.post("/api/auth/refresh")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_get_me_with_valid_token(client, clean_db, organizer_user):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        await ac.post(
            "/api/auth/register",
            json={
                "email": "me@example.com",
                "password": "Password123",
                "name": "Me User",
            },
        )
        login_res = await ac.post(
            "/api/auth/login",
            json={
                "email": "me@example.com",
                "password": "Password123",
            },
        )
    token = login_res.json()["access_token"]

    async with AsyncClient(app=app, base_url="http://test") as ac:
        res = await ac.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "me@example.com"
    assert data["role"] == "participant"


@pytest.mark.asyncio
async def test_get_me_no_token_401(client, clean_db):
    from app.auth import get_current_user
    from app.main import app as main_app

    # Temporarily remove the auth override to test real 401 behavior
    original = main_app.dependency_overrides.pop(get_current_user, None)
    try:
        res = await client.get("/api/auth/me")
        assert res.status_code == 401
    finally:
        if original:
            main_app.dependency_overrides[get_current_user] = original


@pytest.mark.asyncio
async def test_forgot_password_generic_response(client, clean_db, organizer_user):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        res = await ac.post(
            "/api/auth/forgot-password",
            json={
                "email": "nonexistent@example.com",
            },
        )
    assert res.status_code == 200

    async with AsyncClient(app=app, base_url="http://test") as ac:
        res = await ac.post(
            "/api/auth/forgot-password",
            json={
                "email": organizer_user.email,
            },
        )
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_reset_password_success(client, clean_db, organizer_user, engine):
    # Register a user
    async with AsyncClient(app=app, base_url="http://test") as ac:
        await ac.post(
            "/api/auth/register",
            json={
                "email": "reset@example.com",
                "password": "Password123",
                "name": "Reset User",
            },
        )

    # Manually set a reset token on the user
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from app.auth import hash_reset_token

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as db:
        result = await db.execute(select(User).where(User.email == "reset@example.com"))
        user = result.scalar_one()
        raw_token = "test-reset-token-123"
        user.password_reset_token_hash = hash_reset_token(raw_token)
        from datetime import UTC, datetime, timedelta

        user.password_reset_expires = datetime.now(UTC) + timedelta(hours=1)
        await db.commit()

    async with AsyncClient(app=app, base_url="http://test") as ac:
        res = await ac.post(
            "/api/auth/reset-password",
            json={
                "token": raw_token,
                "new_password": "NewPassword456",
            },
        )
    assert res.status_code == 200

    # Login with new password should work
    async with AsyncClient(app=app, base_url="http://test") as ac:
        res = await ac.post(
            "/api/auth/login",
            json={
                "email": "reset@example.com",
                "password": "NewPassword456",
            },
        )
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_reset_password_invalid_token(client, clean_db):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        res = await ac.post(
            "/api/auth/reset-password",
            json={
                "token": "invalid",
                "new_password": "NewPassword456",
            },
        )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_get_providers_empty(client, clean_db):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        res = await ac.get("/api/auth/providers")
    assert res.status_code == 200
    assert res.json() == []
