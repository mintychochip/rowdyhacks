import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_dashboard_returns_list(client: AsyncClient):
    response = await client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "submissions" in data
    assert "total" in data
    assert isinstance(data["submissions"], list)


@pytest.mark.asyncio
async def test_create_hackathon_201(client: AsyncClient):
    response = await client.post("/api/hackathons", json={
        "name": "Test Hackathon",
        "start_date": "2026-04-15T00:00:00",
        "end_date": "2026-04-16T00:00:00",
    })
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_list_hackathons(client: AsyncClient):
    response = await client.get("/api/hackathons")
    assert response.status_code == 200
