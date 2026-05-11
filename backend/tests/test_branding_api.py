import pytest


@pytest.mark.asyncio
async def test_get_branding_defaults(client):
    response = await client.get("/api/config/branding")
    assert response.status_code == 200
    data = response.json()
    assert data["hackathon_name"] == "OpenHack"
    assert data["hackathon_tagline"] == "The open-source hackathon framework"
    assert data["hackathon_email"] == "noreply@example.com"
    assert data["hackathon_primary_color"] == "#2563eb"
    assert data["hackathon_logo_url"] == "/openhack-logo.png"
    assert data["hackathon_favicon_url"] == "/openhack-logo.png"
    assert data["hackathon_year"] == 2025


@pytest.mark.asyncio
async def test_get_manifest_defaults(client):
    response = await client.get("/api/config/manifest.json")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "OpenHack"
    assert data["short_name"] == "OP"
    assert data["theme_color"] == "#2563eb"
    assert data["icons"][0]["src"] == "/openhack-logo.png"
    assert response.headers["cache-control"] == "no-cache, no-store, must-revalidate"
