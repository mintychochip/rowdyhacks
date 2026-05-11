"""Monitoring and health check endpoints."""

import time
from datetime import UTC, datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import text

from app.cache import get_redis
from app.database import async_session

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


class HealthStatus(BaseModel):
    status: str
    timestamp: str
    version: str = "0.1.0"
    checks: dict


class MetricsResponse(BaseModel):
    uptime_seconds: float
    requests_total: int
    requests_per_minute: float
    average_response_time_ms: float
    error_rate: float
    active_connections: int


# Simple in-memory metrics (replace with Prometheus in production)
_metrics = {
    "start_time": time.monotonic(),
    "requests_total": 0,
    "requests_by_endpoint": {},
    "errors_total": 0,
    "response_times": [],
    "active_connections": 0,
}


@router.get("/health", response_model=HealthStatus)
async def health_check():
    """Comprehensive health check including database and Redis."""
    checks = {}

    # Database check
    try:
        async with async_session() as db:
            await db.execute(text("SELECT 1"))
            checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)}"

    # Redis check (optional)
    try:
        redis = await get_redis()
        if redis:
            await redis.ping()
            checks["redis"] = "healthy"
        else:
            checks["redis"] = "not_configured"
    except Exception as e:
        checks["redis"] = f"unhealthy: {str(e)}"

    # Disk space check (basic)
    try:
        import shutil

        stat = shutil.disk_usage("/tmp")
        free_percent = (stat.free / stat.total) * 100
        checks["disk"] = f"healthy ({free_percent:.1f}% free)"
    except Exception as e:
        checks["disk"] = f"unknown: {str(e)}"

    overall = (
        "healthy" if all(c.startswith("healthy") or c == "not_configured" for c in checks.values()) else "degraded"
    )

    return HealthStatus(
        status=overall,
        timestamp=datetime.now(UTC).isoformat(),
        checks=checks,
    )


@router.get("/ready")
async def readiness_check():
    """Kubernetes-style readiness probe."""
    try:
        async with async_session() as db:
            await db.execute(text("SELECT 1"))
        return {"ready": True}
    except Exception:
        return {"ready": False}


@router.get("/live")
async def liveness_check():
    """Kubernetes-style liveness probe."""
    return {"alive": True}


@router.get("/metrics")
async def get_metrics():
    """Application metrics (Prometheus-compatible format)."""
    uptime = time.monotonic() - _metrics["start_time"]

    # Calculate requests per minute
    requests_per_minute = (_metrics["requests_total"] / uptime) * 60 if uptime > 0 else 0

    # Calculate average response time
    avg_response_time = (
        sum(_metrics["response_times"]) / len(_metrics["response_times"]) if _metrics["response_times"] else 0
    ) * 1000  # Convert to ms

    # Calculate error rate
    error_rate = (_metrics["errors_total"] / _metrics["requests_total"]) * 100 if _metrics["requests_total"] > 0 else 0

    return MetricsResponse(
        uptime_seconds=round(uptime, 2),
        requests_total=_metrics["requests_total"],
        requests_per_minute=round(requests_per_minute, 2),
        average_response_time_ms=round(avg_response_time, 2),
        error_rate=round(error_rate, 2),
        active_connections=_metrics["active_connections"],
    )


@router.get("/metrics/prometheus")
async def prometheus_metrics():
    """Prometheus-formatted metrics endpoint."""
    uptime = time.monotonic() - _metrics["start_time"]

    lines = [
        "# HELP hackathon_uptime_seconds Total uptime in seconds",
        "# TYPE hackathon_uptime_seconds gauge",
        f"hackathon_uptime_seconds {uptime}",
        "",
        "# HELP hackathon_requests_total Total requests",
        "# TYPE hackathon_requests_total counter",
        f"hackathon_requests_total {_metrics['requests_total']}",
        "",
        "# HELP hackathon_errors_total Total errors",
        "# TYPE hackathon_errors_total counter",
        f"hackathon_errors_total {_metrics['errors_total']}",
        "",
        "# HELP hackathon_active_connections Current active connections",
        "# TYPE hackathon_active_connections gauge",
        f"hackathon_active_connections {_metrics['active_connections']}",
    ]

    # Add per-endpoint metrics
    for endpoint, count in _metrics["requests_by_endpoint"].items():
        lines.append(f'hackathon_requests_by_endpoint{{endpoint="{endpoint}"}} {count}')

    return "\n".join(lines)


# Request tracking middleware
async def track_request(request: Request, call_next):
    """Middleware to track request metrics."""
    _metrics["active_connections"] += 1
    _metrics["requests_total"] += 1

    endpoint = f"{request.method} {request.url.path}"
    _metrics["requests_by_endpoint"][endpoint] = _metrics["requests_by_endpoint"].get(endpoint, 0) + 1

    start = time.monotonic()
    try:
        response = await call_next(request)
        if response.status_code >= 400:
            _metrics["errors_total"] += 1
        return response
    except Exception:
        _metrics["errors_total"] += 1
        raise
    finally:
        _metrics["active_connections"] -= 1
        duration = time.monotonic() - start
        _metrics["response_times"].append(duration)

        # Keep only last 1000 response times
        if len(_metrics["response_times"]) > 1000:
            _metrics["response_times"] = _metrics["response_times"][-1000:]


@router.get("/diagnostics")
async def diagnostics():
    """Extended diagnostics for all subsystems."""
    checks = {}

    # Database
    try:
        async with async_session() as db:
            await db.execute(text("SELECT 1"))
            checks["database"] = {"status": "healthy"}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}

    # Redis
    try:
        redis = await get_redis()
        if redis:
            await redis.ping()
            info = await redis.info()
            checks["redis"] = {"status": "healthy", "version": info.get("redis_version", "unknown")}
        else:
            checks["redis"] = {"status": "not_configured"}
    except Exception as e:
        checks["redis"] = {"status": "unhealthy", "error": str(e)}

    # Discord bot
    try:
        from app.discord_bot import bot

        checks["discord"] = {
            "status": "healthy" if bot.is_ready() else "not_ready",
            "user": str(bot.user) if bot.user else None,
            "guild_count": len(bot.guilds),
        }
    except Exception as e:
        checks["discord"] = {"status": "unhealthy", "error": str(e)}

    # Scheduler
    try:
        from app.background_jobs import scheduler

        checks["scheduler"] = {
            "status": "healthy" if scheduler and scheduler.running else "not_running",
            "jobs": len(scheduler.get_jobs()) if scheduler and scheduler.running else 0,
        }
    except Exception as e:
        checks["scheduler"] = {"status": "unhealthy", "error": str(e)}

    # Disk
    try:
        import shutil

        stat = shutil.disk_usage("/tmp")
        free_percent = (stat.free / stat.total) * 100
        checks["disk"] = {"status": "healthy", "free_percent": round(free_percent, 1)}
    except Exception as e:
        checks["disk"] = {"status": "unknown", "error": str(e)}

    overall = (
        "healthy"
        if all(c.get("status") in ("healthy", "not_configured", "not_ready", "not_running") for c in checks.values())
        else "degraded"
    )

    return {
        "status": overall,
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": checks,
    }


@router.get("/version")
async def version():
    """Get application version and build info."""
    return {
        "version": "0.1.0",
        "build_time": None,  # Set during CI/CD
        "git_sha": None,  # Set during CI/CD
        "python_version": "3.11",
        "fastapi_version": "0.115.0",
    }
