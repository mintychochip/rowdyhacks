"""Crawler trigger endpoint (organizer-only)."""
import asyncio
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from app.crawler.scheduler import is_crawling, run_crawl
from app.auth import decode_token
from app.models import UserRole, CrawledHackathon, CrawledProject
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func

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


@router.get("/hackathons")
async def list_crawled_hackathons(
    user: dict = Depends(_require_organizer),
    db: AsyncSession = Depends(get_db),
):
    """List all crawled hackathons with project counts."""
    from sqlalchemy import func, select
    from app.models import CrawledProject

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
    user: dict = Depends(_require_organizer),
    db: AsyncSession = Depends(get_db),
):
    """List projects for a specific crawled hackathon."""
    from uuid import UUID
    from app.models import CrawledProject

    try:
        hk_id = UUID(hackathon_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid hackathon ID")

    # Verify hackathon exists
    hk_result = await db.execute(
        select(CrawledHackathon).where(CrawledHackathon.id == hk_id)
    )
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
    count_result = await db.execute(
        select(func.count()).where(CrawledProject.hackathon_id == hk_id)
    )
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
    user: dict = Depends(_require_organizer),
    db: AsyncSession = Depends(get_db),
):
    """Search crawled projects by title."""
    from app.models import CrawledProject

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
