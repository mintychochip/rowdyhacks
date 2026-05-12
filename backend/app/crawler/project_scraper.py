"""Fill in metadata for uncrawled project rows using the Devpost scraper."""

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select, update

from app.checks.similarity import _get_head_commit
from app.database import async_session
from app.models import CrawledProject
from app.scraper import scrape_devpost

logger = logging.getLogger(__name__)


async def scrape_projects(batch_size: int = 50, concurrency: int = 5) -> int:
    """Scrape metadata for uncrawled Devpost projects.

    Behavior:
    1. Query the database for projects where ``last_crawled_at`` is ``NULL`` and ``retry_count < 3``.
    2. For each project, concurrently scrape its Devpost page (up to ``concurrency`` at a time).
    3. Fetch title, description, tech stack, team members, GitHub URL, and (when available) the HEAD commit hash.
    4. Update the ``CrawledProject`` row with the scraped metadata and set ``last_crawled_at``.
    5. On failure, increment ``retry_count``.
    6. Return the count of successfully scraped projects.

    Raises: None
    Side Effects: Updates ``CrawledProject`` rows in PostgreSQL.
    Dependencies: app.scraper.scrape_devpost, app.checks.similarity._get_head_commit, sqlalchemy.select/update.
    Consumers: Crawl scheduler, manual scrape triggers.
    """
    async with async_session() as db:
        result = await db.execute(
            select(CrawledProject)
            .where(CrawledProject.last_crawled_at.is_(None))
            .where(CrawledProject.retry_count < 3)
            .limit(batch_size)
        )
        projects = result.scalars().all()

    if not projects:
        return 0

    semaphore = asyncio.Semaphore(concurrency)
    scraped_count = 0

    async def scrape_one(project: CrawledProject):
        """Scrape a single project and update its metadata.

        Behavior:
        1. Acquire the concurrency semaphore.
        2. Scrape the project's Devpost page.
        3. If a GitHub URL is present, fetch the HEAD commit hash.
        4. Update the ``CrawledProject`` row in the database with the scraped metadata.
        5. On failure, increment the project's ``retry_count``.

        Raises: None
        Side Effects: Updates ``CrawledProject`` rows in PostgreSQL.
        Dependencies: app.scraper.scrape_devpost, app.checks.similarity._get_head_commit, sqlalchemy.update.
        Consumers: scrape_projects coroutine.
        """
        nonlocal scraped_count
        async with semaphore:
            try:
                data = await scrape_devpost(project.devpost_url)

                # Get commit hash if we have a GitHub URL
                commit_hash = None
                if data.github_url:
                    commit_hash = await _get_head_commit(data.github_url)

                async with async_session() as db:
                    await db.execute(
                        update(CrawledProject)
                        .where(CrawledProject.id == project.id)
                        .values(
                            title=data.title,
                            description=data.description,
                            claimed_tech=data.claimed_tech,
                            team_members=data.team_members,
                            github_url=data.github_url,
                            commit_hash=commit_hash,
                            video_url=data.video_url,
                            slides_url=data.slides_url,
                            last_crawled_at=datetime.now(UTC),
                        )
                    )
                    await db.commit()
                scraped_count += 1

            except Exception as e:
                logger.warning(f"Failed to scrape {project.devpost_url}: {e}")
                async with async_session() as db:
                    await db.execute(
                        update(CrawledProject)
                        .where(CrawledProject.id == project.id)
                        .values(retry_count=CrawledProject.retry_count + 1)
                    )
                    await db.commit()

    tasks = [scrape_one(p) for p in projects]
    await asyncio.gather(*tasks)

    return scraped_count
