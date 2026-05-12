import uuid

import pytest_asyncio
from fastapi import Header
from app.database import get_db
from app.main import app
from app.models import Base, UserRole
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Create a test engine and set up all tables."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine):
    """Provide a fresh async session for each test."""
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()


async def _override_require_clerk_user(authorization: str | None = Header(alias="Authorization", default=None)):
    """Override require_clerk_user for testing.

    Supports test tokens of the form 'Bearer test-<user_id>' to return
    a specific user sub. Falls back to a random UUID for plain tokens.
    """
    import sys

    print(f"[DEBUG] _override_require_clerk_user called with authorization={authorization!r}", file=sys.stderr)
    user_id = str(uuid.uuid4())
    email = "test@example.com"
    if authorization and authorization.startswith("Bearer test-"):
        parts = authorization.removeprefix("Bearer test-").split(":", 1)
        user_id = parts[0]
        if len(parts) > 1:
            email = parts[1]
    print(f"[DEBUG] returning sub={user_id}", file=sys.stderr)
    return {"sub": user_id, "email": email}


async def _override_require_organizer():
    """Override require_organizer for testing."""
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


async def _override_require_clerk_user_with_db():
    """Override require_clerk_user_with_db for testing."""
    fake_user = type(
        "FakeUser",
        (),
        {
            "role": UserRole.participant,
            "id": "test-user-id",
            "email": "test@example.com",
            "name": "Test User",
        },
    )()
    return {
        "user": fake_user,
        "sub": "test-user-id",
        "email": "test@example.com",
        "payload": {},
    }


async def _override_require_hackathon_organizer(hackathon_id: uuid.UUID):
    """Override require_hackathon_organizer for testing."""
    return {
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
        "sub": "test-organizer-id",
        "email": "organizer@test.com",
        "payload": {},
    }


@pytest_asyncio.fixture
async def client(engine):
    """Provide an async test client that uses the test DB."""
    from app.clerk_auth import (
        require_clerk_user,
        require_clerk_user_with_db,
        require_hackathon_organizer,
        require_organizer,
    )

    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with async_session_maker() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_clerk_user] = _override_require_clerk_user
    app.dependency_overrides[require_clerk_user_with_db] = _override_require_clerk_user_with_db
    app.dependency_overrides[require_organizer] = _override_require_organizer
    app.dependency_overrides[require_hackathon_organizer] = _override_require_hackathon_organizer
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
