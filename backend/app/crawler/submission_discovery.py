"""Discover all submission URLs for a given hackathon."""
import asyncio
import logging
import uuid

from bs4 import BeautifulSoup
from sqlalchemy import select

from app.database import async_session
from app.models import CrawledProject
from app.scraper import _fetch_page_sync

logger = logging.getLogger(__name__)

MAX_SUBMISSION_PAGES = 200


async def discover_submissions(hackathon_id: uuid.UUID, hackathon_url: str) -> list[str]:
    """Scrape a hackathon's submission gallery, insert new project rows.

    Args:
        hackathon_id: UUID of the CrawledHackathon row
        hackathon_url: Devpost URL of the hackathon (e.g. https://devpost.com/hackathons/foo)

    Returns list of new CrawledProject IDs.
    """
    new_ids: list[str] = []
    base_url = hackathon_url.rstrip("/")

    async with async_session() as db:
        # Build globally known set of devpost_urls (UNIQUE constraint on
        # devpost_url applies across all hackathons, not per-hackathon)
        result = await db.execute(
            select(CrawledProject.devpost_url)
        )
        known_urls = set(result.scalars().all())

        for page_num in range(1, MAX_SUBMISSION_PAGES + 1):
            url = f"{base_url}/submissions?page={page_num}"
            try:
                html = await asyncio.to_thread(_fetch_page_sync, url)
            except Exception:
                logger.warning("Failed to fetch %s, stopping pagination for this hackathon", url)
                break
            soup = BeautifulSoup(html, "lxml")

            # Find submission links
            links = soup.select("a[href*='/software/'], a[href*='/projects/']")
            # Also try gallery-specific selectors
            if not links:
                links = soup.select(
                    ".gallery-item a, .submission a, [class*='submission'] a"
                )

            page_has_new = False
            for link in links:
                href = link.get("href", "")
                if not href:
                    continue
                # Resolve URL
                if href.startswith("/"):
                    full_url = f"https://devpost.com{href}"
                elif href.startswith("http"):
                    full_url = href
                else:
                    continue

                full_url = full_url.split("?")[0].split("#")[0]

                # Only accept submission pages, not the hackathon page itself
                if "/software/" not in full_url and "/projects/" not in full_url:
                    continue
                if full_url in known_urls:
                    continue

                p = CrawledProject(
                    devpost_url=full_url,
                    hackathon_id=hackathon_id,
                )
                db.add(p)
                known_urls.add(full_url)
                page_has_new = True
                new_ids.append(str(p.id))

            await db.commit()

            if not page_has_new:
                break

    return new_ids
