"""Crawler trigger endpoint (organizer-only)."""

import asyncio
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import require_organizer
from app.crawler.scheduler import is_crawling, run_crawl

# Backward-compat alias for tests that import _require_organizer
_require_organizer = require_organizer
from app.database import get_db
from app.models import CrawledHackathon, CrawledProject

logger = logging.getLogger(__name__)
router = APIRouter()


class CreateCrawledHackathonRequest(BaseModel):
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
    Dependencies: app.models.CrawledHackathon.
    Consumers: POST /hackathons, admin/debug panel.
    """
    try:
        start = datetime.fromisoformat(req.start_date.replace("Z", "+00:00"))
        end = datetime.fromisoformat(req.end_date.replace("Z", "+00:00")) if req.end_date else None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")

    hackathon = CrawledHackathon(
        devpost_url=req.devpost_url,
        name=req.name,
        start_date=start,
        end_date=end,
        last_crawled_at=datetime.now(UTC),
    )
    db.add(hackathon)
    await db.commit()
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
    Dependencies: app.models.CrawledHackathon, app.models.CrawledProject, sqlalchemy.func.count.
    Consumers: GET /hackathons, organizer crawler dashboard.
    """
    from sqlalchemy import func, select

    query = (
        select(
            CrawledHackathon.id,
            CrawledHackathon.name,
            CrawledHackathon.devpost_url,
            CrawledHackathon.start_date,
            CrawledHackathon.end_date,
            CrawledHackathon.last_crawled_at,
            func.count(CrawledProject.id).label("project_count"),
        )
        .outerjoin(CrawledProject, CrawledProject.hackathon_id == CrawledHackathon.id)
        .group_by(CrawledHackathon.id)
        .order_by(CrawledHackathon.last_crawled_at.desc().nulls_last())
    )

    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "id": str(r.id),
            "name": r.name,
            "devpost_url": r.devpost_url,
            "start_date": r.start_date.isoformat() if r.start_date else None,
            "end_date": r.end_date.isoformat() if r.end_date else None,
            "last_crawled_at": r.last_crawled_at.isoformat() if r.last_crawled_at else None,
            "project_count": r.project_count,
        }
        for r in rows
    ]


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
    Dependencies: app.models.CrawledHackathon, app.models.CrawledProject.
    Consumers: GET /hackathons/{hackathon_id}/projects, organizer project browser.
    """
    from uuid import UUID

    try:
        hk_id = UUID(hackathon_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid hackathon ID")

    # Verify hackathon exists
    hk_result = await db.execute(select(CrawledHackathon).where(CrawledHackathon.id == hk_id))
    hackathon = hk_result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    # Get projects
    query = (
        select(CrawledProject)
        .where(CrawledProject.hackathon_id == hk_id)
        .order_by(CrawledProject.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    projects = result.scalars().all()

    # Get total count
    count_result = await db.execute(select(func.count()).where(CrawledProject.hackathon_id == hk_id))
    total = count_result.scalar()

    return {
        "hackathon": {
            "id": str(hackathon.id),
            "name": hackathon.name,
            "devpost_url": hackathon.devpost_url,
        },
        "projects": [
            {
                "id": str(p.id),
                "title": p.title,
                "devpost_url": p.devpost_url,
                "github_url": p.github_url,
                "team_members": p.team_members,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in projects
        ],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


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
    Dependencies: app.models.CrawledProject.
    Consumers: GET /projects, organizer project search.
    """

    query = select(CrawledProject)
    if q:
        query = query.where(CrawledProject.title.ilike(f"%{q}%"))

    query = query.order_by(CrawledProject.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    projects = result.scalars().all()

    return {
        "projects": [
            {
                "id": str(p.id),
                "title": p.title,
                "devpost_url": p.devpost_url,
                "github_url": p.github_url,
                "hackathon_id": str(p.hackathon_id),
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in projects
        ],
        "total": len(projects),
    }
