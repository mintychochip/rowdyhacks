"""Tests for health check and monitoring endpoints."""

import pytest


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Health endpoint should return 200 with status info."""
    resp = await client.get("/api/monitoring/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "checks" in data
    assert "database" in data["checks"]


@pytest.mark.asyncio
async def test_liveness_endpoint(client):
    """Liveness probe should always return 200."""
    resp = await client.get("/api/monitoring/live")
    assert resp.status_code == 200
    data = resp.json()
    assert data["alive"] is True


@pytest.mark.asyncio
async def test_readiness_endpoint(client):
    """Readiness probe should return 200 when DB is accessible."""
    resp = await client.get("/api/monitoring/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert "ready" in data


@pytest.mark.asyncio
async def test_health_includes_redis_status(client):
    """Health check should report Redis status (even if not configured)."""
    resp = await client.get("/api/monitoring/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "redis" in data["checks"]
