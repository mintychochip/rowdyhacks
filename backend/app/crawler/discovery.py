"""Discover hackathons from Devpost's hackathon listing."""
import asyncio
import logging
import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup
from sqlalchemy import select

from app.database import async_session
from app.models import CrawledHackathon
from app.scraper import _fetch_page_sync

logger = logging.getLogger(__name__)

DEVPOST_HACKATHONS_URL = "https://devpost.com/hackathons"
MAX_PAGES = 50


async def discover_hackathons() -> list[str]:
    """Scrape Devpost hackathon listing, insert new hackathons.

    Returns list of crawled_hackathon IDs that are new (never crawled,
    identified by last_crawled_at IS NULL).
    """
    new_ids: list[str] = []

    async with async_session() as db:
        # Build set of known devpost_urls for quick lookup
        result = await db.execute(select(CrawledHackathon.devpost_url))
        known_urls = set(result.scalars().all())

        for page_num in range(1, MAX_PAGES + 1):
            url = f"{DEVPOST_HACKATHONS_URL}?page={page_num}"
            try:
                html = await asyncio.to_thread(_fetch_page_sync, url)
            except Exception:
                logger.warning("Failed to fetch %s, stopping pagination", url)
                break
            soup = BeautifulSoup(html, "lxml")

            cards = soup.select(".hackathon-card, [class*='hackathon-tile'], .challenge-listing")
            if not cards:
                # Try broader selectors for listing items
                cards = soup.select("a[href*='/hackathons/']")
                cards = [c for c in cards if c.get("href", "").count("/") >= 2]

            page_has_new = False
            for card in cards:
                link = card.get("href", "") if card.name == "a" else card.select_one("a[href*='/hackathons/']")
                if not link:
                    continue
                href = link if isinstance(link, str) else link.get("href", "")
                if not href or "/hackathons/" not in href:
                    continue

                # Resolve relative URL
                if href.startswith("/"):
                    full_url = f"https://devpost.com{href}"
                elif href.startswith("http"):
                    full_url = href
                else:
                    full_url = f"https://devpost.com/{href}"

                # Clean fragment/query params
                full_url = full_url.split("#")[0].split("?")[0]

                if full_url in known_urls:
                    continue

                # Extract name
                name = card.get_text(strip=True)[:300] if card.name != "a" else ""
                if not name and hasattr(card, "select_one"):
                    name_el = card.select_one("h2, h3, .name, [class*='title']")
                    name = name_el.get_text(strip=True)[:300] if name_el else full_url.split("/")[-1]
                elif not name:
                    name = full_url.split("/")[-1]

                # Try to extract dates
                start_date = None
                end_date = None
                date_text = card.get_text() if hasattr(card, "get_text") else ""
                date_match = re.search(
                    r"(\w+ \d{1,2})\s*[-–]\s*(\w+ \d{1,2}),?\s*(\d{4})",
                    date_text,
                )
                if date_match:
                    try:
                        start_str = f"{date_match.group(1)}, {date_match.group(3)}"
                        end_str = f"{date_match.group(2)}, {date_match.group(3)}"
                        start_date = datetime.strptime(start_str, "%b %d, %Y").replace(tzinfo=timezone.utc)
                        end_date = datetime.strptime(end_str, "%b %d, %Y").replace(tzinfo=timezone.utc)
                    except ValueError:
                        pass

                h = CrawledHackathon(
                    devpost_url=full_url,
                    name=name,
                    start_date=start_date,
                    end_date=end_date,
                )
                db.add(h)
                known_urls.add(full_url)
                page_has_new = True
                new_ids.append(str(h.id))

            await db.commit()

            # Stop if entire page was duplicates
            if not page_has_new:
                break

    return new_ids
