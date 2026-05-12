import asyncio

import pytest
import pytest_asyncio
from fastapi import Header, HTTPException, status
from app.database import get_db
from app.main import app
from app.models import Base, UserRole
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


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


async def _override_get_current_user(
    authorization: str | None = Header(alias="Authorization", default=None),
):
    """Override get_current_user for testing.

    Supports real JWTs and test tokens of the form 'Bearer test-<user_id>'.
    Returns a default fake user when no header is present for convenience.
    Raises 401 for explicitly invalid tokens.
    """
    if not authorization:
        # Return a default fake participant for tests that don't send headers
        return type(
            "FakeUser",
            (),
            {
                "role": UserRole.participant,
                "id": "test-default-user-id",
                "email": "test@example.com",
                "name": "Test User",
                "password_hash": "hash",
                "email_verified": True,
            },
        )()

    token = authorization.removeprefix("Bearer ")

    # Try real JWT first
    try:
        from app.auth import verify_access_token

        payload = verify_access_token(token)
        role_str = payload.get("role", "participant")
        role = UserRole(role_str) if role_str in (r.value for r in UserRole) else UserRole.participant
        return type(
            "FakeUser",
            (),
            {
                "role": role,
                "id": payload.get("sub", "unknown"),
                "email": payload.get("email", "test@example.com"),
                "name": "Test User",
                "password_hash": "hash",
                "email_verified": True,
            },
        )()
    except Exception:
        pass

    # Test token format: test-<user_id> or test-<user_id>:<email>
    if token.startswith("test-"):
        parts = token.removeprefix("test-").split(":", 1)
        user_id = parts[0]
        email = parts[1] if len(parts) > 1 else "test@example.com"
        return type(
            "FakeUser",
            (),
            {
                "role": UserRole.participant,
                "id": user_id,
                "email": email,
                "name": "Test User",
                "password_hash": "hash",
                "email_verified": True,
            },
        )()

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


async def _override_require_organizer():
    """Override require_organizer for testing."""
    return type(
        "FakeUser",
        (),
        {
            "role": UserRole.organizer,
            "id": "test-organizer-id",
            "email": "organizer@test.com",
            "name": "Test Organizer",
            "password_hash": "hash",
            "email_verified": True,
        },
    )()


async def _override_require_participant():
    """Override require_participant for testing."""
    return type(
        "FakeUser",
        (),
        {
            "role": UserRole.participant,
            "id": "test-participant-id",
            "email": "participant@test.com",
            "name": "Test Participant",
            "password_hash": "hash",
            "email_verified": True,
        },
    )()


async def _override_require_judge():
    """Override require_judge for testing."""
    return type(
        "FakeUser",
        (),
        {
            "role": UserRole.judge,
            "id": "test-judge-id",
            "email": "judge@test.com",
            "name": "Test Judge",
            "password_hash": "hash",
            "email_verified": True,
        },
    )()


@pytest_asyncio.fixture
async def client(engine):
    """Provide an async test client that uses the test DB."""
    from app.auth import get_current_user, require_organizer, require_participant, require_judge

    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with async_session_maker() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    app.dependency_overrides[require_organizer] = _override_require_organizer
    app.dependency_overrides[require_participant] = _override_require_participant
    app.dependency_overrides[require_judge] = _override_require_judge

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
