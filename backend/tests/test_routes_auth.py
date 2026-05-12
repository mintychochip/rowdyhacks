"""Auth route tests for self-hosted JWT auth."""

import pytest


@pytest.mark.asyncio
async def test_get_me_no_token_401(client):
    """GET /api/auth/me without a token should return 401."""
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_invalid_token_401(client):
    """GET /api/auth/me with an invalid Bearer token should return 401."""
    response = await client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401
