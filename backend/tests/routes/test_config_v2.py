import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import _memory_cache
from app.database import get_db
from app.routes.config import router as config_router

app = FastAPI()
app.include_router(config_router)


@pytest_asyncio.fixture
async def config_client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    _memory_cache.clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_config_returns_all_keys(config_client):
    response = await config_client.get("/api/config/")
    assert response.status_code == 200
    data = response.json()
    assert "hackathon_name" in data
    assert data["hackathon_name"] == "OpenHack"
    assert "hackathon_primary_color" in data
    assert "custom_css" in data


@pytest.mark.asyncio
async def test_get_config_filtered_by_category(config_client):
    response = await config_client.get("/api/config/?category=theme")
    assert response.status_code == 200
    data = response.json()
    theme_keys = {
        "hackathon_primary_color",
        "hackathon_background_color",
        "hackathon_text_color",
        "hackathon_accent_color",
        "hackathon_font_heading",
        "hackathon_font_body",
        "custom_css",
    }
    assert set(data.keys()) == theme_keys


@pytest.mark.asyncio
async def test_get_config_invalid_category(config_client):
    response = await config_client.get("/api/config/?category=invalid")
    assert response.status_code == 400
    assert "Invalid category" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_single_key(config_client):
    response = await config_client.get("/api/config/keys/hackathon_name")
    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "hackathon_name"
    assert data["value"] == "OpenHack"


@pytest.mark.asyncio
async def test_get_theme_css(config_client):
    response = await config_client.get("/api/config/theme.css")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/css; charset=utf-8"
    css = response.text
    assert ":root {" in css
    assert "--oh-primary: #2563eb;" in css


@pytest.mark.asyncio
async def test_get_manifest_json(config_client):
    response = await config_client.get("/api/config/manifest.json")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "OpenHack"
    assert data["short_name"] == "OP"
    assert data["theme_color"] == "#2563eb"
    assert data["icons"][0]["src"] == "/openhack-logo.png"
    assert response.headers["cache-control"] == "no-cache, no-store, must-revalidate"


@pytest.mark.asyncio
async def test_get_branding_backward_compat(config_client):
    response = await config_client.get("/api/config/branding")
    assert response.status_code == 200
    data = response.json()
    assert data["hackathon_name"] == "OpenHack"
    assert data["hackathon_tagline"] == "The open-source hackathon framework"
    assert data["hackathon_email"] == "noreply@example.com"
    assert data["hackathon_primary_color"] == "#2563eb"
    assert data["hackathon_logo_url"] == "/openhack-logo.png"
    assert data["hackathon_favicon_url"] == "/openhack-logo.png"
    assert data["hackathon_year"] == 2025
