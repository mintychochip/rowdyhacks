"""Crawl scheduler: orchestrates discovery -> submission discovery -> project scrape."""

import logging

from sqlalchemy import select

from app.crawler.discovery import discover_hackathons
from app.crawler.project_scraper import scrape_projects
from app.crawler.submission_discovery import discover_submissions
from app.database import async_session
from app.models import CrawledHackathon

logger = logging.getLogger(__name__)

_crawler_running: bool = False


def is_crawling() -> bool:
    """Return whether a crawl cycle is currently running.

    Behavior:
    1. Return the value of the module-level ``_crawler_running`` flag.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: None
    Consumers: Crawl status endpoints, scheduler health checks.
    """
    return _crawler_running


async def run_crawl() -> dict:
    """Orchestrate a full crawl cycle.

    Behavior:
    1. Check the ``_crawler_running`` flag; if already active, raise ``RuntimeError``.
    2. Set the flag to ``True`` and initialize a summary dict.
    3. Discover new hackathons on Devpost and record the count.
    4. Iterate over all known hackathons and discover their submissions.
    5. Scrape metadata for all uncrawled projects in batches until no new projects remain.
    6. Record any errors encountered during the cycle.
    7. Reset the flag and return the summary dict.

    Raises: RuntimeError if another crawl is already in progress.
    Side Effects: Mutates ``_crawler_running``; writes to PostgreSQL via downstream crawlers.
    Dependencies: app.crawler.discovery.discover_hackathons, app.crawler.submission_discovery.discover_submissions, app.crawler.project_scraper.scrape_projects.
    Consumers: Background task scheduler, manual crawl triggers.
    """
    global _crawler_running

    if _crawler_running:
        raise RuntimeError("Crawl already in progress")

    _crawler_running = True
    summary: dict = {
        "new_hackathons": 0,
        "new_submissions": 0,
        "scraped_projects": 0,
        "errors": [],
    }

    try:
        # 1. Discover new hackathons
        logger.info("Starting hackathon discovery...")
        new_hackathon_ids = await discover_hackathons()
        summary["new_hackathons"] = len(new_hackathon_ids)
        logger.info(f"Discovered {len(new_hackathon_ids)} new hackathons")

        # 2. Find ALL hackathons for submission discovery (not just "active" ones)
        # We want to index projects from ALL hackathons, regardless of date
        async with async_session() as db:
            result = await db.execute(select(CrawledHackathon))
            all_hackathons = result.scalars().all()

        # 3. Discover submissions for ALL hackathons
        for hk in all_hackathons:
            try:
                logger.info(f"Discovering submissions for {hk.name}...")
                new_sub_ids = await discover_submissions(hk.id, hk.devpost_url)
                summary["new_submissions"] += len(new_sub_ids)
            except Exception as e:
                msg = f"Failed to discover submissions for {hk.name}: {e}"
                logger.error(msg)
                summary["errors"].append(msg)

        # 4. Scrape uncrawled projects
        logger.info("Scraping uncrawled projects...")
        total_scraped = 0
        while True:
            count = await scrape_projects(batch_size=50, concurrency=5)
            if count == 0:
                break
            total_scraped += count
            logger.info(f"Scraped {total_scraped} projects so far...")

        summary["scraped_projects"] = total_scraped

    finally:
        _crawler_running = False

    logger.info(f"Crawl complete: {summary}")
    return summary
