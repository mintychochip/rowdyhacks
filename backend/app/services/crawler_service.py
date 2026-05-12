"""Crawler orchestration service.

Provides high-level operations for managing crawled hackathons and projects,
as well as triggering crawl cycles.
"""

import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crawler.scheduler import is_crawling, run_crawl
from app.models import CrawledHackathon, CrawledProject

logger = logging.getLogger(__name__)


class CrawlerService:
    """Service for crawler orchestration and crawled data management."""

    async def trigger_crawl(self) -> dict:
        """Trigger a full crawl cycle if one is not already running.

        Behavior:
        1. Check if a crawl is already in progress via ``is_crawling``.
        2. Raise RuntimeError if a crawl is already running.
        3. Spawn ``run_crawl`` as an asyncio background task.
        4. Attach a done callback that logs exceptions.
        5. Return {"status": "started"}.

        Raises: RuntimeError if crawl already in progress.
        Side Effects: Spawns a background asyncio task.
        """
        if is_crawling():
            raise RuntimeError("Crawl already in progress")

        task = asyncio.create_task(run_crawl())
        task.add_done_callback(
            lambda t: logger.error("Crawl failed", exc_info=t.exception()) if t.exception() else None
        )

        return {"status": "started"}

    async def create_hackathon(
        self,
        db: AsyncSession,
        devpost_url: str,
        name: str,
        start_date: datetime,
        end_date: datetime | None = None,
    ) -> CrawledHackathon:
        """Manually add a crawled hackathon entry.

        Behavior:
        1. Create a CrawledHackathon record with the provided URL, name, and dates.
        2. Set last_crawled_at to now.
        3. Persist and return the created record.

        Side Effects: Inserts CrawledHackathon row.
        """
        hackathon = CrawledHackathon(
            devpost_url=devpost_url,
            name=name,
            start_date=start_date,
            end_date=end_date,
            last_crawled_at=datetime.now(UTC),
        )
        db.add(hackathon)
        await db.commit()
        await db.refresh(hackathon)
        return hackathon

    async def list_hackathons(self, db: AsyncSession) -> list[dict]:
        """List all crawled hackathons with associated project counts.

        Behavior:
        1. Query all CrawledHackathon records with an outer join to CrawledProject.
        2. Aggregate project counts per hackathon.
        3. Order results by last_crawled_at descending (nulls last).
        4. Return serialized list with IDs, dates, URLs, and counts.

        Side Effects: None (read-only).
        """
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

    async def get_hackathon(self, db: AsyncSession, hackathon_id: UUID) -> CrawledHackathon | None:
        """Load a single crawled hackathon by ID.

        Side Effects: None (read-only).
        """
        result = await db.execute(select(CrawledHackathon).where(CrawledHackathon.id == hackathon_id))
        return result.scalar_one_or_none()

    async def list_projects(
        self,
        db: AsyncSession,
        hackathon_id: UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> dict:
        """List projects for a specific crawled hackathon with pagination.

        Behavior:
        1. Query CrawledProject rows for the hackathon ordered by created_at descending.
        2. Apply offset/limit pagination.
        3. Return the total count and paginated project list.

        Side Effects: None (read-only).
        """
        hackathon = await self.get_hackathon(db, hackathon_id)
        if not hackathon:
            raise ValueError("Hackathon not found")

        query = (
            select(CrawledProject)
            .where(CrawledProject.hackathon_id == hackathon_id)
            .order_by(CrawledProject.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(query)
        projects = result.scalars().all()

        count_result = await db.execute(select(func.count()).where(CrawledProject.hackathon_id == hackathon_id))
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

    async def search_projects(
        self,
        db: AsyncSession,
        query_str: str = "",
        offset: int = 0,
        limit: int = 50,
    ) -> dict:
        """Search crawled projects by title with pagination.

        Behavior:
        1. Apply an optional case-insensitive title filter if query_str is provided.
        2. Query CrawledProject rows ordered by created_at descending.
        3. Apply offset/limit pagination.
        4. Return matching projects with hackathon linkage.

        Side Effects: None (read-only).
        """
        query = select(CrawledProject)
        if query_str:
            query = query.where(CrawledProject.title.ilike(f"%{query_str}%"))

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
