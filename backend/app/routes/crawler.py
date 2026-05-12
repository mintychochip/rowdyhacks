"""Crawler trigger endpoint (organizer-only)."""

import asyncio
import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import require_organizer
from app.crawler.scheduler import is_crawling, run_crawl
from app.database import get_db
from app.services.crawler_service import CrawlerService

# Backward-compat alias for tests that import _require_organizer
_require_organizer = require_organizer

logger = logging.getLogger(__name__)
router = APIRouter()


crawler_service = CrawlerService()


class CreateCrawledHackathonRequest(BaseModel):
    """Request body for manually adding a crawled hackathon entry."""

    devpost_url: str
    name: str
    start_date: str
    end_date: str | None = None


@router.post("/trigger", status_code=202)
async def trigger_crawl(auth: dict = Depends(require_organizer)):
    """Manually trigger a full crawl cycle (organizer-only).

    Behavior:
    1. Check if a crawl is already in progress via is_crawling.
    2. Return 409 if a crawl is already running.
    3. Spawn run_crawl as an asyncio background task.
    4. Attach a done callback that logs exceptions.
    5. Return {"status": "started"}.

    Raises: HTTPException(409) if crawl already in progress.
    Side Effects: Spawns a background asyncio task.
    Dependencies: app.crawler.scheduler.is_crawling, app.crawler.scheduler.run_crawl.
    Consumers: POST /trigger, organizer dashboard.
    """
    if is_crawling():
        raise HTTPException(status_code=409, detail="Crawl already in progress")

    # Fire-and-forget: start crawl in background with exception logging
    task = asyncio.create_task(run_crawl())
    task.add_done_callback(lambda t: logger.error("Crawl failed", exc_info=t.exception()) if t.exception() else None)

    return {"status": "started"}


@router.post("/hackathons", status_code=201)
async def create_crawled_hackathon(
    req: CreateCrawledHackathonRequest,
    auth: dict = Depends(require_organizer),
    db: AsyncSession = Depends(get_db),
):
    """Manually add a crawled hackathon entry (admin/debug use).

    Behavior:
    1. Parse start_date and optional end_date from ISO strings.
    2. Create a CrawledHackathon record with the provided URL, name, and dates.
    3. Set last_crawled_at to now.
    4. Persist and return the created record ID.

    Raises: HTTPException(400) if date format is invalid.
    Side Effects: Inserts CrawledHackathon row.
    Dependencies: app.services.crawler_service.CrawlerService.
    Consumers: POST /hackathons, admin/debug panel.
    """
    try:
        start = datetime.fromisoformat(req.start_date.replace("Z", "+00:00"))
        end = datetime.fromisoformat(req.end_date.replace("Z", "+00:00")) if req.end_date else None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")

    hackathon = await crawler_service.create_hackathon(
        db=db,
        devpost_url=req.devpost_url,
        name=req.name,
        start_date=start,
        end_date=end,
    )
    return {"id": str(hackathon.id), "name": hackathon.name, "created": True}


@router.get("/hackathons")
async def list_crawled_hackathons(
    auth: dict = Depends(require_organizer),
    db: AsyncSession = Depends(get_db),
):
    """List all crawled hackathons with associated project counts.

    Behavior:
    1. Query all CrawledHackathon records with an outer join to CrawledProject.
    2. Aggregate project counts per hackathon.
    3. Order results by last_crawled_at descending (nulls last).
    4. Return serialized list with IDs, dates, URLs, and counts.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.services.crawler_service.CrawlerService.
    Consumers: GET /hackathons, organizer crawler dashboard.
    """
    return await crawler_service.list_hackathons(db)


@router.get("/hackathons/{hackathon_id}/projects")
async def list_crawled_projects(
    hackathon_id: str,
    offset: int = 0,
    limit: int = 50,
    auth: dict = Depends(require_organizer),
    db: AsyncSession = Depends(get_db),
):
    """List projects for a specific crawled hackathon with pagination.

    Behavior:
    1. Validate the hackathon_id as a UUID.
    2. Verify the hackathon exists; 404 if not found.
    3. Query CrawledProject rows for the hackathon ordered by created_at descending.
    4. Apply offset/limit pagination.
    5. Return the total count and paginated project list.

    Raises: HTTPException(400) for invalid UUID, HTTPException(404) if hackathon not found.
    Side Effects: None (read-only).
    Dependencies: app.services.crawler_service.CrawlerService.
    Consumers: GET /hackathons/{hackathon_id}/projects, organizer project browser.
    """
    try:
        hk_id = UUID(hackathon_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid hackathon ID")

    try:
        data = await crawler_service.list_projects(db, hk_id, offset=offset, limit=limit)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return data


@router.get("/projects")
async def search_crawled_projects(
    q: str = "",
    offset: int = 0,
    limit: int = 50,
    auth: dict = Depends(require_organizer),
    db: AsyncSession = Depends(get_db),
):
    """Search crawled projects by title with pagination.

    Behavior:
    1. Apply an optional case-insensitive title filter if q is provided.
    2. Query CrawledProject rows ordered by created_at descending.
    3. Apply offset/limit pagination.
    4. Return matching projects with hackathon linkage.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.services.crawler_service.CrawlerService.
    Consumers: GET /projects, organizer project search.
    """
    return await crawler_service.search_projects(db, query_str=q, offset=offset, limit=limit)
