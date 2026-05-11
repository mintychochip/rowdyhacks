"""Tests for monitoring routes."""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routes.monitoring import router as monitoring_router

app = FastAPI()
app.include_router(monitoring_router)


@pytest_asyncio.fixture
async def monitoring_client(engine):
    async_session_maker = __import__("sqlalchemy.ext.asyncio", fromlist=["async_sessionmaker"]).async_sessionmaker

    async def override_get_db():
        async with async_session_maker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_health_check(monitoring_client):
    resp = await monitoring_client.get("/api/monitoring/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("healthy", "degraded")
    assert "checks" in data
    assert "database" in data["checks"]


@pytest.mark.anyio
async def test_readiness_check(monitoring_client):
    resp = await monitoring_client.get("/api/monitoring/ready")
    assert resp.status_code == 200
    assert "ready" in resp.json()


@pytest.mark.anyio
async def test_liveness_check(monitoring_client):
    resp = await monitoring_client.get("/api/monitoring/live")
    assert resp.status_code == 200
    assert resp.json()["alive"] is True


@pytest.mark.anyio
async def test_diagnostics(monitoring_client):
    resp = await monitoring_client.get("/api/monitoring/diagnostics")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "checks" in data
    assert "database" in data["checks"]
    assert "redis" in data["checks"]
    assert "discord" in data["checks"]
    assert "scheduler" in data["checks"]
    assert "disk" in data["checks"]


@pytest.mark.anyio
async def test_metrics(monitoring_client):
    resp = await monitoring_client.get("/api/monitoring/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "uptime_seconds" in data
    assert "requests_total" in data


@pytest.mark.anyio
async def test_prometheus_metrics(monitoring_client):
    resp = await monitoring_client.get("/api/monitoring/metrics/prometheus")
    assert resp.status_code == 200
    text = resp.text
    assert "hackathon_uptime_seconds" in text
    assert "hackathon_requests_total" in text


@pytest.mark.anyio
async def test_version(monitoring_client):
    resp = await monitoring_client.get("/api/monitoring/version")
    assert resp.status_code == 200
    data = resp.json()
    assert "version" in data
