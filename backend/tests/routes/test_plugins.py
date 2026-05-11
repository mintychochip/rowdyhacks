"""Tests for plugin routes."""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Plugin, User
from app.routes.plugins import router as plugins_router

app = FastAPI()
app.include_router(plugins_router)


async def _override_require_clerk_user():
    return {"sub": "test-user-id", "email": "test@example.com"}


@pytest_asyncio.fixture
async def plugin_client(engine):
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
async def clean_plugins(db_session: AsyncSession):
    await db_session.execute(delete(Plugin))
    await db_session.execute(delete(User))
    await db_session.commit()


@pytest.mark.anyio
async def test_register_plugin(plugin_client, clean_plugins):
    resp = await plugin_client.post(
        "/api/plugins",
        json={
            "name": "my-plugin",
            "version": "1.0.0",
            "description": "A test plugin",
            "enabled": True,
            "config": {"key": "value"},
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "my-plugin"
    assert data["version"] == "1.0.0"


@pytest.mark.anyio
async def test_register_duplicate(plugin_client, clean_plugins):
    await plugin_client.post("/api/plugins", json={"name": "dup"})
    resp = await plugin_client.post("/api/plugins", json={"name": "dup"})
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_list_plugins(plugin_client, clean_plugins):
    await plugin_client.post("/api/plugins", json={"name": "p1"})
    await plugin_client.post("/api/plugins", json={"name": "p2"})
    resp = await plugin_client.get("/api/plugins")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


@pytest.mark.anyio
async def test_get_plugin(plugin_client, clean_plugins):
    create_resp = await plugin_client.post("/api/plugins", json={"name": "get-me"})
    pid = create_resp.json()["id"]
    resp = await plugin_client.get(f"/api/plugins/{pid}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "get-me"


@pytest.mark.anyio
async def test_update_plugin(plugin_client, clean_plugins):
    create_resp = await plugin_client.post("/api/plugins", json={"name": "old"})
    pid = create_resp.json()["id"]
    resp = await plugin_client.put(f"/api/plugins/{pid}", json={"enabled": False})
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False


@pytest.mark.anyio
async def test_delete_plugin(plugin_client, clean_plugins):
    create_resp = await plugin_client.post("/api/plugins", json={"name": "del-me"})
    pid = create_resp.json()["id"]
    resp = await plugin_client.delete(f"/api/plugins/{pid}")
    assert resp.status_code == 204

    get_resp = await plugin_client.get(f"/api/plugins/{pid}")
    assert get_resp.status_code == 404
