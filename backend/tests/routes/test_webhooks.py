"""Tests for webhook subscription routes."""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.database import get_db
from app.models import UserRole
from app.routes.webhooks import router as webhooks_router
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

app = FastAPI()
app.include_router(webhooks_router)


async def _override_require_organizer():
    """Override require_organizer for testing."""
    return {
        "sub": "test-user-id",
        "email": "organizer@example.com",
        "user": type("FakeUser", (), {"role": UserRole.organizer})(),
    }


@pytest_asyncio.fixture(autouse=True)
async def _clear_webhook_tables(engine):
    """Clear webhook tables before each test to ensure isolation."""
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM webhook_delivery_logs"))
        await conn.execute(text("DELETE FROM webhook_subscriptions"))


@pytest_asyncio.fixture
async def webhook_client(engine):
    """Provide an async test client for webhook routes using the test DB."""
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with async_session_maker() as session:
            yield session

    from app.clerk_auth import require_organizer

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_organizer] = _override_require_organizer
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_subscribe_unauthorized(webhook_client):
    """POST /api/webhooks/subscribe without auth must return 401."""
    from app.clerk_auth import require_organizer

    del app.dependency_overrides[require_organizer]
    try:
        resp = await webhook_client.post(
            "/api/webhooks/subscribe",
            json={
                "url": "https://example.com/webhook",
                "secret": "shhh",
                "events": ["registration.created"],
            },
        )
        assert resp.status_code == 401
    finally:
        app.dependency_overrides[require_organizer] = _override_require_organizer


@pytest.mark.anyio
async def test_list_subscriptions_unauthorized(webhook_client):
    """GET /api/webhooks/subscriptions without auth must return 401."""
    from app.clerk_auth import require_organizer

    del app.dependency_overrides[require_organizer]
    try:
        resp = await webhook_client.get("/api/webhooks/subscriptions")
        assert resp.status_code == 401
    finally:
        app.dependency_overrides[require_organizer] = _override_require_organizer


@pytest.mark.anyio
async def test_delete_subscription_unauthorized(webhook_client):
    """DELETE /api/webhooks/subscriptions/{id} without auth must return 401."""
    from app.clerk_auth import require_organizer

    del app.dependency_overrides[require_organizer]
    try:
        resp = await webhook_client.delete("/api/webhooks/subscriptions/123e4567-e89b-12d3-a456-426614174000")
        assert resp.status_code == 401
    finally:
        app.dependency_overrides[require_organizer] = _override_require_organizer


@pytest.mark.anyio
async def test_subscribe_and_list(webhook_client):
    """Authorized organizer can subscribe and list subscriptions."""
    resp = await webhook_client.post(
        "/api/webhooks/subscribe",
        json={
            "url": "https://example.com/webhook",
            "secret": "shhh",
            "events": ["registration.created"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["url"] == "https://example.com/webhook"
    assert data["events"] == ["registration.created"]
    assert data["active"] is True
    assert "id" in data

    resp = await webhook_client.get("/api/webhooks/subscriptions")
    assert resp.status_code == 200
    subs = resp.json()
    assert len(subs) == 1
    assert subs[0]["url"] == "https://example.com/webhook"


@pytest.mark.anyio
async def test_delete_subscription(webhook_client):
    """Authorized organizer can delete a subscription."""
    resp = await webhook_client.post(
        "/api/webhooks/subscribe",
        json={
            "url": "https://example.com/webhook",
            "secret": "shhh",
            "events": ["registration.created"],
        },
    )
    assert resp.status_code == 200
    sub_id = resp.json()["id"]

    resp = await webhook_client.delete(f"/api/webhooks/subscriptions/{sub_id}")
    assert resp.status_code == 200
    assert resp.json()["deleted"] == sub_id

    resp = await webhook_client.get("/api/webhooks/subscriptions")
    subs = resp.json()
    assert all(s["id"] != sub_id for s in subs)


@pytest.mark.anyio
async def test_delete_nonexistent_subscription(webhook_client):
    """Deleting an unknown subscription returns 404."""
    resp = await webhook_client.delete("/api/webhooks/subscriptions/123e4567-e89b-12d3-a456-426614174000")
    assert resp.status_code == 404
