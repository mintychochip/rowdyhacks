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
    """Scrape all uncrawled projects (last_crawled_at IS NULL, retry_count < 3).

    Args:
        batch_size: Max number of projects to scrape in one call
        concurrency: Max concurrent scrape requests

    Returns count of successfully scraped projects.
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
