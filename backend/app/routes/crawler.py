"""Crawler trigger endpoint (organizer-only)."""
import asyncio
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from app.crawler.scheduler import is_crawling, run_crawl
from app.auth import decode_token
from app.models import UserRole, CrawledHackathon
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter()


class CreateCrawledHackathonRequest(BaseModel):
    devpost_url: str
    name: str
    start_date: str
    end_date: str | None = None


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


@router.post("/hackathons", status_code=201)
async def create_crawled_hackathon(
    req: CreateCrawledHackathonRequest,
    user: dict = Depends(_require_organizer),
    db: AsyncSession = Depends(get_db),
):
    """Manually add a crawled hackathon (admin/debug use)."""
    try:
        start = datetime.fromisoformat(req.start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(req.end_date.replace('Z', '+00:00')) if req.end_date else None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")

    hackathon = CrawledHackathon(
        devpost_url=req.devpost_url,
        name=req.name,
        start_date=start,
        end_date=end,
        last_crawled_at=datetime.now(timezone.utc),
    )
    db.add(hackathon)
    await db.commit()
    return {"id": str(hackathon.id), "name": hackathon.name, "created": True}
