"""Discover hackathons from Devpost's hackathon listing using Playwright for JS rendering."""

import asyncio
import logging
import re
from datetime import UTC, datetime

from playwright.async_api import async_playwright
from sqlalchemy import select

from app.database import async_session
from app.models import CrawledHackathon

logger = logging.getLogger(__name__)

DEVPOST_HACKATHONS_URL = "https://devpost.com/hackathons"
MAX_SCROLLS = 200  # Max "load more" scrolls (each shows ~10-12 hackathons)

# JavaScript to extract hackathon cards — defined separately to avoid Python escape issues
_EXTRACT_CARDS_JS = r"""() => {
  const results = [];
  document.querySelectorAll('a[href*=".devpost.com/"]').forEach(card => {
    const href = card.getAttribute('href');
    if (!href) return;
    const urlMatch = href.match(/^https:\/\/([^.]+)\.devpost\.com\//);
    if (!urlMatch) return;
    const name = card.querySelector('h3')?.textContent?.trim() || '';
    if (!name) return;
    const fullText = card.textContent || '';
    const dateMatch = fullText.match(/([A-Z][a-z]{2} \d{2})\s*[-\u2013]\s*([A-Z][a-z]{2} \d{2}),?\s*(\d{4})/);
    let dates = '';
    if (dateMatch) {
      dates = dateMatch[1] + ' - ' + dateMatch[2] + ', ' + dateMatch[3];
    }
    const partMatch = fullText.match(/(\d[\d,]*)\s*participants/);
    const participants = partMatch ? parseInt(partMatch[1].replace(/,/g, '')) : null;
    results.push({
      url: href.split('?')[0].replace(/\/$/, ''),
      name: name,
      dates: dates,
      participants: participants,
    });
  });
  const seen = new Set();
  return results.filter(r => {
    if (seen.has(r.url)) return false;
    seen.add(r.url);
    return true;
  });
}"""


async def discover_hackathons() -> list[str]:
    """Load the JS-rendered Devpost listing, extract hackathon cards, insert new rows.

    Returns list of crawled_hackathon IDs that are new.
    """
    new_ids: list[str] = []

    async with async_session() as db:
        result = await db.execute(select(CrawledHackathon.devpost_url))
        known_urls = set(result.scalars().all())

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
            )
            page = await context.new_page()
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => false });")
            await page.goto(DEVPOST_HACKATHONS_URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_selector('a[href*=".devpost.com/"] h3', timeout=15000)

            scrolls = 0

            while scrolls < MAX_SCROLLS:
                cards = await page.evaluate(_EXTRACT_CARDS_JS)

                page_has_new = False
                for card_data in cards:
                    full_url = card_data["url"]
                    if full_url in known_urls:
                        continue
                    if not full_url.startswith("https://"):
                        continue
                    name = card_data["name"][:300]
                    if not name:
                        continue

                    # Parse dates
                    start_date = None
                    end_date = None
                    date_text = card_data.get("dates", "")
                    if date_text:
                        date_match = re.search(
                            r"([A-Z][a-z]{2} \d{1,2})\s*[-–]\s*([A-Z][a-z]{2} \d{1,2}),?\s*(\d{4})",
                            date_text,
                        )
                        if date_match:
                            try:
                                start_str = f"{date_match.group(1)}, {date_match.group(3)}"
                                end_str = f"{date_match.group(2)}, {date_match.group(3)}"
                                start_date = datetime.strptime(start_str, "%b %d, %Y").replace(tzinfo=UTC)
                                end_date = datetime.strptime(end_str, "%b %d, %Y").replace(tzinfo=UTC)
                            except ValueError:
                                pass

                    h = CrawledHackathon(
                        devpost_url=full_url,
                        name=name,
                        start_date=start_date,
                        end_date=end_date,
                        submission_count=card_data.get("participants") or 0,
                    )
                    db.add(h)
                    await db.flush()
                    known_urls.add(full_url)
                    page_has_new = True
                    new_ids.append(str(h.id))

                await db.commit()

                if not page_has_new:
                    break

                # Scroll down to load more hackathons
                prev_height = await page.evaluate("document.body.scrollHeight")
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                try:
                    await page.wait_for_function(
                        f"document.body.scrollHeight > {prev_height}",
                        timeout=5000,
                    )
                except Exception:
                    break
                await asyncio.sleep(1)
                scrolls += 1

            await browser.close()

    return new_ids
