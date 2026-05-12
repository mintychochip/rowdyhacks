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
    from app.auth import require_organizer
    from app.main import app as main_app

    original = main_app.dependency_overrides.pop(require_organizer, None)
    try:
        res = await client.get("/api/admin/oauth/providers")
        # With conftest auth override, a fake participant hits organizer-only endpoint -> 403
        assert res.status_code == 403
    finally:
        if original:
            main_app.dependency_overrides[require_organizer] = original
