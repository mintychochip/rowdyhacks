import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_submit_invalid_url_400(client: AsyncClient):
    response = await client.post("/api/check", json={"url": "https://google.com"})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_submit_devpost_url_201(client: AsyncClient):
    # This will fail at scraping but should create the submission
    response = await client.post("/api/check", json={"url": "https://devpost.com/software/test"})
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert "access_token" in data
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_get_nonexistent_404(client: AsyncClient):
    response = await client.get("/api/check/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_check_with_token(client: AsyncClient):
    # Create first
    create_resp = await client.post("/api/check", json={"url": "https://devpost.com/software/test2"})
    data = create_resp.json()
    # Get with token
    response = await client.get(f"/api/check/{data['id']}?token={data['access_token']}")
    assert response.status_code == 200
    assert response.json()["status"] in ("pending", "analyzing")
