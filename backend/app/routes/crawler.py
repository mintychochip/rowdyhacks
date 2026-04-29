"""Crawler trigger endpoint (organizer-only)."""
import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, Header
from app.crawler.scheduler import is_crawling, run_crawl
from app.auth import decode_token
from app.models import UserRole

logger = logging.getLogger(__name__)
router = APIRouter()


async def _require_organizer(authorization: str | None = Header(None)) -> dict:
    """FastAPI dependency: require a valid JWT from an organizer user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization.removeprefix("Bearer ")
    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("role") != UserRole.organizer.value:
        raise HTTPException(status_code=403, detail="Organizer access required")
    return payload


@router.post("/trigger", status_code=202)
async def trigger_crawl(user: dict = Depends(_require_organizer)):
    """Manually trigger a full crawl cycle (organizer-only).

    Returns 409 if a crawl is already running.
    """
    if is_crawling():
        raise HTTPException(status_code=409, detail="Crawl already in progress")

    # Fire-and-forget: start crawl in background with exception logging
    task = asyncio.create_task(run_crawl())
    task.add_done_callback(
        lambda t: logger.error("Crawl failed", exc_info=t.exception())
        if t.exception() else None
    )

    return {"status": "started"}
