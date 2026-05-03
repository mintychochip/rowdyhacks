import pytest
from httpx import AsyncClient

from app.auth import hash_password
from app.models import User, UserRole


@pytest.mark.asyncio
async def test_dashboard_returns_list(client: AsyncClient):
    response = await client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "submissions" in data
    assert "total" in data
    assert isinstance(data["submissions"], list)


@pytest.mark.asyncio
async def test_create_hackathon_201(client: AsyncClient, db_session):
    # Create an organizer user
    organizer = User(
        email="dashorg@test.com", name="Organizer", role=UserRole.organizer, password_hash=hash_password("password123")
    )
    db_session.add(organizer)
    await db_session.commit()

    # Login to get token
    from app.auth import create_access_token

    token = create_access_token(str(organizer.id), organizer.role.value)

    response = await client.post(
        "/api/hackathons",
        json={
            "name": "Test Hackathon",
            "start_date": "2026-04-15T00:00:00",
            "end_date": "2026-04-16T00:00:00",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_list_hackathons(client: AsyncClient):
    response = await client.get("/api/hackathons")
    assert response.status_code == 200
