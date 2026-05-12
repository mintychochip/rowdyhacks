"""Tests for meal management routes."""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Hackathon, User, UserRole
from app.routes.meals import router as meals_router

app = FastAPI()
app.include_router(meals_router)


async def _override_require_clerk_user():
    return {"sub": "test-user-id", "email": "test@example.com"}


@pytest_asyncio.fixture
async def meal_client(engine):
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
async def hackathon(db_session: AsyncSession):
    from datetime import UTC, datetime

    await db_session.execute(delete(Hackathon))
    await db_session.execute(delete(User))
    await db_session.commit()

    user = User(id="test-user-id", email="test@example.com", name="Test User", role=UserRole.organizer)
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
    return hackathon


@pytest.mark.anyio
async def test_create_meal(meal_client, hackathon):
    from datetime import UTC, datetime

    now = datetime.now(UTC).isoformat()
    resp = await meal_client.post(
        f"/api/hackathons/{hackathon.id}/meals",
        json={"meal_type": "Lunch", "start_time": now, "end_time": now, "location": "Cafeteria", "max_capacity": 100},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["meal_type"] == "Lunch"
    assert data["location"] == "Cafeteria"
    assert data["max_capacity"] == 100


@pytest.mark.anyio
async def test_list_meals(meal_client, hackathon):
    from datetime import UTC, datetime

    now = datetime.now(UTC).isoformat()
    await meal_client.post(
        f"/api/hackathons/{hackathon.id}/meals",
        json={"meal_type": "Dinner", "start_time": now, "end_time": now},
    )
    resp = await meal_client.get(f"/api/hackathons/{hackathon.id}/meals")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["meal_type"] == "Dinner"


@pytest.mark.anyio
async def test_rsvp_for_meal(meal_client, hackathon):
    from datetime import UTC, datetime

    now = datetime.now(UTC).isoformat()
    create_resp = await meal_client.post(
        f"/api/hackathons/{hackathon.id}/meals",
        json={"meal_type": "Breakfast", "start_time": now, "end_time": now, "max_capacity": 10},
    )
    meal_id = create_resp.json()["id"]

    resp = await meal_client.post(
        f"/api/hackathons/meals/{meal_id}/rsvp",
        json={"dietary_restrictions": "Vegetarian"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["user_id"] == "test-user-id"
    assert data["dietary_restrictions"] == "Vegetarian"


@pytest.mark.anyio
async def test_list_meal_attendance(meal_client, hackathon):
    from datetime import UTC, datetime

    now = datetime.now(UTC).isoformat()
    create_resp = await meal_client.post(
        f"/api/hackathons/{hackathon.id}/meals",
        json={"meal_type": "Snack", "start_time": now, "end_time": now},
    )
    meal_id = create_resp.json()["id"]

    await meal_client.post(
        f"/api/hackathons/meals/{meal_id}/rsvp",
        json={},
    )

    resp = await meal_client.get(f"/api/hackathons/meals/{meal_id}/attendance")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["user_id"] == "test-user-id"
