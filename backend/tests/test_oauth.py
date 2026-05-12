import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_providers_empty(client: AsyncClient):
    res = await client.get("/api/auth/providers")
    assert res.status_code == 200
    assert res.json() == []


@pytest.mark.asyncio
async def test_oauth_login_provider_not_found(client: AsyncClient):
    res = await client.get("/api/auth/oauth/github/login")
    assert res.status_code == 404
    assert res.json()["detail"] == "OAuth provider not found or inactive"


@pytest.mark.asyncio
async def test_admin_list_providers_unauthorized(client: AsyncClient):
    res = await client.get("/api/admin/oauth/providers")
    assert res.status_code == 401
