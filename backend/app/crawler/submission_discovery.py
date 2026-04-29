"""Discover all submission URLs for a given hackathon using Playwright for JS rendering."""
import asyncio
import logging
import uuid

from playwright.async_api import async_playwright
from sqlalchemy import select

from app.database import async_session
from app.models import CrawledProject

logger = logging.getLogger(__name__)

MAX_SCROLLS = 200  # Max scrolls for infinite-load galleries

# JavaScript to extract submission links from the project gallery
_EXTRACT_SUBMISSIONS_JS = (
    "() => {"
    "  const results = [];"
    "  document.querySelectorAll('a[href*=\"/software/\"], a[href*=\"/projects/\"]').forEach(link => {"
    "    const href = link.getAttribute('href');"
    "    if (!href) return;"
    "    if (href.includes('/software/') || href.includes('/projects/')) {"
    "      const url = new URL(href, window.location.origin);"
    "      results.push(url.origin + url.pathname.split('?')[0].split('#')[0]);"
    "    }"
    "  });"
    "  const seen = new Set();"
    "  return results.filter(r => {"
    "    if (seen.has(r)) return false;"
    "    seen.add(r);"
    "    return true;"
    "  });"
    "}"
)


async def discover_submissions(hackathon_id: uuid.UUID, hackathon_url: str) -> list[str]:
    """Load the JS-rendered submission gallery, extract project URLs, insert new rows.

    Args:
        hackathon_id: UUID of the CrawledHackathon row
        hackathon_url: Devpost URL of the hackathon (e.g. https://slug.devpost.com)

    Returns list of new CrawledProject IDs.
    """
    new_ids: list[str] = []
    base_url = hackathon_url.rstrip("/")
    gallery_url = f"{base_url}/project-gallery"

    async with async_session() as db:
        result = await db.execute(select(CrawledProject.devpost_url))
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
            await page.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', { get: () => false });"
            )
            await page.goto(gallery_url, wait_until="domcontentloaded", timeout=60000)

            # Wait for submission links or a "not published" message
            try:
                await page.wait_for_selector(
                    'a[href*="/software/"], a[href*="/projects/"], .gallery-item, [class*="submission"]',
                    timeout=10000,
                )
            except Exception:
                logger.info("No submissions found for %s (gallery may not be published)", hackathon_url)
                await browser.close()
                return new_ids

            scrolls = 0
            while scrolls < MAX_SCROLLS:
                links = await page.evaluate(_EXTRACT_SUBMISSIONS_JS)

                page_has_new = False
                for full_url in links:
                    if full_url in known_urls:
                        continue
                    if not full_url.startswith("https://"):
                        continue
                    if "/software/" not in full_url and "/projects/" not in full_url:
                        continue

                    p = CrawledProject(
                        devpost_url=full_url,
                        hackathon_id=hackathon_id,
                    )
                    db.add(p)
                    await db.flush()
                    known_urls.add(full_url)
                    page_has_new = True
                    new_ids.append(str(p.id))

                await db.commit()

                if not page_has_new:
                    break

                # Scroll to load more
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
