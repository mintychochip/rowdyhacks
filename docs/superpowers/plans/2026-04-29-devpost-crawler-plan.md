# Devpost Bulk Crawler & Cross-Hackathon Detection — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a bulk Devpost crawler that indexes all hackathon submission pages, plus two new detection checks (cross-hackathon duplicate detection and repeat offender tracking) powered by the index.

**Architecture:** Extend the existing FastAPI app with new models (`CrawledHackathon`, `CrawledProject`), four crawler modules under `backend/app/crawler/`, an apscheduler `AsyncIOScheduler` for weekly crawling, and two new per-submission check functions registered via the existing `CHECKS`/`WEIGHTS` pattern.

**Tech Stack:** FastAPI, SQLAlchemy async, apscheduler, BeautifulSoup/lxml, httpx, pytest + pytest-asyncio

---

## Chunk 1: Foundation — Models, Settings, Dependencies

### Task 1.1: Add CrawledHackathon and CrawledProject models

**Files:**
- Modify: `backend/app/models.py:1-97`
- Test: `backend/tests/test_crawler_models.py`

- [ ] **Step 1: Write failing test for CrawledHackathon model**

```python
# backend/tests/test_crawler_models.py
import pytest
import uuid
from app.models import CrawledHackathon, CrawledProject

@pytest.mark.asyncio
async def test_crawled_hackathon_creation():
    from app.database import async_session
    from app.models import Base
    from sqlalchemy import text

    async with async_session() as db:
        # Create
        h = CrawledHackathon(
            id=uuid.uuid4(),
            devpost_url="https://devpost.com/hackathons/test-fest-2025",
            name="Test Fest 2025",
            start_date=datetime(2025, 6, 1, tzinfo=timezone.utc),
            end_date=datetime(2025, 6, 3, tzinfo=timezone.utc),
            submission_count=120,
        )
        db.add(h)
        await db.commit()
        await db.refresh(h)

        assert h.id is not None
        assert h.devpost_url == "https://devpost.com/hackathons/test-fest-2025"
        assert h.name == "Test Fest 2025"
        assert h.last_crawled_at is None
        assert h.created_at is not None

@pytest.mark.asyncio
async def test_crawled_project_creation():
    from datetime import datetime, timezone
    from app.database import async_session
    import uuid

    async with async_session() as db:
        # Create parent hackathon first
        h = CrawledHackathon(
            id=uuid.uuid4(),
            devpost_url="https://devpost.com/hackathons/test-fest-2025",
            name="Test Fest 2025",
        )
        db.add(h)
        await db.commit()

        # Create project
        p = CrawledProject(
            id=uuid.uuid4(),
            devpost_url="https://devpost.com/software/test-project",
            hackathon_id=h.id,
            title="Test Project",
            description="A test project",
            claimed_tech=["python", "react"],
            team_members=[{"name": "Alice", "devpost_profile": "/alice", "github": "https://github.com/alice"}],
            github_url="https://github.com/alice/test-project",
            commit_hash="abc123def456",
            retry_count=0,
        )
        db.add(p)
        await db.commit()
        await db.refresh(p)

        assert p.id is not None
        assert p.devpost_url == "https://devpost.com/software/test-project"
        assert p.hackathon_id == h.id
        assert p.retry_count == 0
        assert p.last_crawled_at is None

@pytest.mark.asyncio
async def test_crawled_project_unique_devpost_url():
    from app.database import async_session
    import uuid

    async with async_session() as db:
        h = CrawledHackathon(
            id=uuid.uuid4(),
            devpost_url="https://devpost.com/hackathons/test-fest-2025",
            name="Test Fest 2025",
        )
        db.add(h)
        await db.commit()

        url = "https://devpost.com/software/duplicate-test"
        p1 = CrawledProject(id=uuid.uuid4(), devpost_url=url, hackathon_id=h.id)
        p2 = CrawledProject(id=uuid.uuid4(), devpost_url=url, hackathon_id=h.id)
        db.add_all([p1, p2])
        with pytest.raises(Exception):  # IntegrityError
            await db.commit()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_crawler_models.py -v`
Expected: FAIL with "name 'CrawledHackathon' is not defined" or similar import error

- [ ] **Step 3: Add models to backend/app/models.py**

Add after line 97 (end of existing model definitions), before the file ends. Add the `Index` import at top of file — modify the SQLAlchemy import line to include `Index`.

```python
# In models.py, add after the Registration class definition:

class CrawledHackathon(Base):
    __tablename__ = "crawled_hackathons"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    devpost_url = Column(Text, unique=True, nullable=False)
    name = Column(String(300), nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    submission_count = Column(Integer, nullable=True)
    last_crawled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    projects = relationship("CrawledProject", back_populates="hackathon")

    def __repr__(self) -> str:
        return f"<CrawledHackathon {self.name}>"


class CrawledProject(Base):
    __tablename__ = "crawled_projects"
    __table_args__ = (
        Index("ix_crawled_projects_github_url", "github_url"),
        Index("ix_crawled_projects_commit_hash", "commit_hash"),
    )

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    devpost_url = Column(Text, unique=True, nullable=False)
    hackathon_id = Column(Guid, ForeignKey("crawled_hackathons.id"), nullable=False)
    title = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    claimed_tech = Column(ArrayOfStrings, nullable=True)
    team_members = Column(JsonType, nullable=True)
    github_url = Column(Text, nullable=True)
    commit_hash = Column(String(40), nullable=True)
    video_url = Column(Text, nullable=True)
    slides_url = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    last_crawled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    hackathon = relationship("CrawledHackathon", back_populates="projects")

    def __repr__(self) -> str:
        return f"<CrawledProject {self.devpost_url}>"
```

Also add `from sqlalchemy import Index` to the existing imports at the top (line 6-8).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest backend/tests/test_crawler_models.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/models.py backend/tests/test_crawler_models.py
git commit -m "feat: add CrawledHackathon and CrawledProject models with indexes"
```

---

### Task 1.2: Add CROSS_HACKATHON and REPEAT_OFFENDER check categories

**Files:**
- Modify: `backend/app/checks/interface.py:10-16`
- Test: `backend/tests/test_check_categories.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_check_categories.py
from app.checks.interface import CheckCategory

def test_cross_hackathon_category_exists():
    assert hasattr(CheckCategory, "CROSS_HACKATHON")
    assert CheckCategory.CROSS_HACKATHON == "cross_hackathon"

def test_repeat_offender_category_exists():
    assert hasattr(CheckCategory, "REPEAT_OFFENDER")
    assert CheckCategory.REPEAT_OFFENDER == "repeat_offender"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_check_categories.py -v`
Expected: 2 FAIL (AttributeError or AssertionError)

- [ ] **Step 3: Add enum values**

Modify `backend/app/checks/interface.py:10-16`:

```python
class CheckCategory(str, Enum):
    TIMELINE = "timeline"
    DEVPOST_ALIGNMENT = "devpost_alignment"
    SUBMISSION_HISTORY = "submission_history"
    ASSET_INTEGRITY = "asset_integrity"
    CROSS_TEAM_SIMILARITY = "cross_team_similarity"
    AI_DETECTION = "ai_detection"
    CROSS_HACKATHON = "cross_hackathon"
    REPEAT_OFFENDER = "repeat_offender"
```

Also add `commit_hash` field to the `ScrapedData` dataclass (around line 25):

```python
@dataclass
class ScrapedData:
    title: str | None = None
    description: str | None = None
    claimed_tech: list[str] = field(default_factory=list)
    team_members: list[dict] = field(default_factory=list)
    github_url: str | None = None
    commit_hash: str | None = None  # HEAD hash from git ls-remote
    video_url: str | None = None
    slides_url: str | None = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest backend/tests/test_check_categories.py -v`
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/checks/interface.py backend/tests/test_check_categories.py
git commit -m "feat: add CROSS_HACKATHON and REPEAT_OFFENDER check categories"
```

---

### Task 1.3: Add crawler settings and dependency

**Files:**
- Modify: `backend/app/config.py:46-48`
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add crawler settings to config.py**

Add after line 46 (`google_wallet_issuer_id` field):

```python
    crawler_schedule: str = Field(
        default="0 3 * * 0",  # Sunday 3 AM UTC
        description="Cron expression for the weekly crawl (APScheduler format)",
    )
    crawler_refresh_window_days: int = Field(
        default=30,
        description="Days after hackathon end to keep refreshing for late submissions",
    )
```

- [ ] **Step 2: Add apscheduler to requirements.txt**

Add to `backend/requirements.txt`:
```
apscheduler==3.10.4
```

- [ ] **Step 3: Install the dependency**

Run: `pip install apscheduler==3.10.4`

- [ ] **Step 4: Verify settings load**

Run: `python -c "from app.config import settings; print(settings.crawler_schedule, settings.crawler_refresh_window_days)"`
Expected: `0 3 * * 0 30`

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/requirements.txt
git commit -m "feat: add crawler settings (schedule, refresh window) and apscheduler dependency"
```

---

## Chunk 2: Crawler Modules

### Task 2.1: Hackathon discovery

**Files:**
- Create: `backend/app/crawler/__init__.py`
- Create: `backend/app/crawler/discovery.py`
- Test: `backend/tests/crawler/test_discovery.py`

- [ ] **Step 1: Create the crawler package init**

```python
# backend/app/crawler/__init__.py
```

- [ ] **Step 2: Write failing test for discovery**

```python
# backend/tests/crawler/test_discovery.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.crawler.discovery import discover_hackathons

@pytest.mark.asyncio
async def test_discover_hackathons_inserts_new():
    """New hackathon URLs should be inserted, duplicates skipped."""
    page_html = """
    <html><body>
    <div class="hackathon-card">
        <a href="/hackathons/test-fest-2025">Test Fest 2025</a>
        <span class="date">Jun 1 - Jun 3, 2025</span>
    </div>
    <div class="hackathon-card">
        <a href="/hackathons/known-event-2024">Known Event 2024</a>
        <span class="date">Jan 1 - Jan 3, 2024</span>
    </div>
    </body></html>
    """

    # Seed DB with known hackathon to test dedup
    from app.database import async_session as db_session
    from app.models import CrawledHackathon
    async with db_session() as db:
        db.add(CrawledHackathon(
            id=uuid.uuid4(),
            devpost_url="https://devpost.com/hackathons/known-event-2024",
            name="Known Event 2024",
        ))
        await db.commit()

    mock_to_thread = AsyncMock(return_value=page_html)
    with patch("app.crawler.discovery.asyncio.to_thread", mock_to_thread):
        result = await discover_hackathons()
        # Only the NEW hackathon (test-fest-2025) should be returned
        assert len(result) == 1
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest backend/tests/crawler/test_discovery.py -v`
Expected: FAIL (import error)

- [ ] **Step 4: Implement discovery.py**

```python
# backend/app/crawler/discovery.py
"""Discover hackathons from Devpost's hackathon listing."""
import re
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from sqlalchemy import select
from app.database import async_session
from app.models import CrawledHackathon
import asyncio
from app.scraper import _fetch_page_sync

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
            html = await asyncio.to_thread(_fetch_page_sync, url)
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
```

- [ ] **Step 5: Run tests**

Run: `pytest backend/tests/crawler/test_discovery.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/crawler/__init__.py backend/app/crawler/discovery.py backend/tests/crawler/test_discovery.py
git commit -m "feat: add hackathon discovery crawler (Devpost listing scraper)"
```

---

### Task 2.2: Submission discovery

**Files:**
- Create: `backend/app/crawler/submission_discovery.py`
- Test: `backend/tests/crawler/test_submission_discovery.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/crawler/test_submission_discovery.py
import uuid
import pytest
from unittest.mock import patch, AsyncMock
from app.crawler.submission_discovery import discover_submissions
from app.models import CrawledHackathon

@pytest.mark.asyncio
async def test_discover_submissions_inserts_urls():
    hackathon_id = uuid.uuid4()
    page_html = """
    <html><body>
    <a href="/software/foo">Foo Project</a>
    <a href="/software/bar">Bar Project</a>
    </body></html>
    """

    # Create parent CrawledHackathon row for FK constraint
    from app.database import async_session
    async with async_session() as db:
        db.add(CrawledHackathon(id=hackathon_id, devpost_url="https://devpost.com/hackathons/test-fest", name="Test Fest"))
        await db.commit()

    mock_to_thread = AsyncMock(return_value=page_html)
    with patch("app.crawler.submission_discovery.asyncio.to_thread", mock_to_thread):
        result = await discover_submissions(hackathon_id, "https://devpost.com/hackathons/test-fest")
        assert len(result) >= 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/crawler/test_submission_discovery.py -v`
Expected: FAIL (import error)

- [ ] **Step 3: Implement submission_discovery.py**

```python
# backend/app/crawler/submission_discovery.py
"""Discover all submission URLs for a given hackathon."""
import asyncio
from bs4 import BeautifulSoup
from sqlalchemy import select
from app.database import async_session
from app.models import CrawledProject
from app.scraper import _fetch_page_sync

MAX_SUBMISSION_PAGES = 200

async def discover_submissions(hackathon_id, hackathon_url: str) -> list[str]:
    """Scrape a hackathon's submission gallery, insert new project rows.

    Args:
        hackathon_id: UUID of the CrawledHackathon row
        hackathon_url: Devpost URL of the hackathon (e.g. https://devpost.com/hackathons/foo)

    Returns list of new CrawledProject IDs.
    """
    new_ids: list[str] = []
    base_url = hackathon_url.rstrip("/")

    async with async_session() as db:
        # Build set of known devpost_urls for this hackathon
        result = await db.execute(
            select(CrawledProject.devpost_url).where(
                CrawledProject.hackathon_id == hackathon_id
            )
        )
        known_urls = set(result.scalars().all())

        for page_num in range(1, MAX_SUBMISSION_PAGES + 1):
            url = f"{base_url}/submissions?page={page_num}"
            html = await asyncio.to_thread(_fetch_page_sync, url)
            soup = BeautifulSoup(html, "lxml")

            # Find submission links
            links = soup.select("a[href*='/software/'], a[href*='/projects/']")
            # Also try gallery-specific selectors
            if not links:
                links = soup.select(".gallery-item a, .submission a, [class*='submission'] a")

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
```

- [ ] **Step 4: Run tests**

Run: `pytest backend/tests/crawler/test_submission_discovery.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/crawler/submission_discovery.py backend/tests/crawler/test_submission_discovery.py
git commit -m "feat: add submission discovery crawler (per-hackathon submission gallery scraper)"
```

---

### Task 2.3: Per-project scraper

**Files:**
- Create: `backend/app/crawler/project_scraper.py`
- Test: `backend/tests/crawler/test_project_scraper.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/crawler/test_project_scraper.py
import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock
from app.crawler.project_scraper import scrape_projects
from app.models import CrawledHackathon, CrawledProject

@pytest.mark.asyncio
async def test_scrape_projects_fills_metadata():
    """Projects with last_crawled_at=NULL and retry_count<3 should get scraped."""
    from app.database import async_session

    async with async_session() as db:
        h = CrawledHackathon(
            id=uuid.uuid4(),
            devpost_url="https://devpost.com/hackathons/test-fest",
            name="Test Fest",
        )
        db.add(h)
        await db.commit()

        p = CrawledProject(
            id=uuid.uuid4(),
            devpost_url="https://devpost.com/software/test-project",
            hackathon_id=h.id,
            retry_count=0,
        )
        db.add(p)
        await db.commit()

        mock_scraped = MagicMock()
        mock_scraped.title = "Test Project"
        mock_scraped.description = "A test"
        mock_scraped.claimed_tech = ["python"]
        mock_scraped.team_members = [{"name": "Alice", "devpost_profile": "/alice", "github": None}]
        mock_scraped.github_url = "https://github.com/alice/test"
        mock_scraped.video_url = None
        mock_scraped.slides_url = None

        with patch("app.crawler.project_scraper.scrape_devpost", return_value=mock_scraped):
            with patch("app.crawler.project_scraper._get_head_commit", return_value="abc123"):
                await scrape_projects(batch_size=10)

        # Re-fetch project
        await db.refresh(p)
        assert p.title == "Test Project"
        assert p.github_url == "https://github.com/alice/test"
        assert p.commit_hash == "abc123"
        assert p.retry_count == 0
        assert p.last_crawled_at is not None

@pytest.mark.asyncio
async def test_scrape_projects_increments_retry_on_failure():
    """Failed scrapes should increment retry_count, not set last_crawled_at."""
    from app.database import async_session

    async with async_session() as db:
        h = CrawledHackathon(
            id=uuid.uuid4(),
            devpost_url="https://devpost.com/hackathons/test-fest",
            name="Test Fest",
        )
        db.add(h)
        await db.commit()

        p = CrawledProject(
            id=uuid.uuid4(),
            devpost_url="https://devpost.com/software/failing-project",
            hackathon_id=h.id,
            retry_count=0,
        )
        db.add(p)
        await db.commit()

        with patch("app.crawler.project_scraper.scrape_devpost", side_effect=Exception("boom")):
            await scrape_projects(batch_size=10)

        await db.refresh(p)
        assert p.retry_count == 1
        assert p.last_crawled_at is None  # Not updated on failure

@pytest.mark.asyncio
async def test_scrape_projects_skips_max_retries():
    """Projects with retry_count >= 3 should be skipped."""
    from app.database import async_session

    async with async_session() as db:
        h = CrawledHackathon(
            id=uuid.uuid4(),
            devpost_url="https://devpost.com/hackathons/test-fest",
            name="Test Fest",
        )
        db.add(h)
        await db.commit()

        p = CrawledProject(
            id=uuid.uuid4(),
            devpost_url="https://devpost.com/software/skipped-project",
            hackathon_id=h.id,
            retry_count=3,
        )
        db.add(p)
        await db.commit()

        call_count = 0
        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return MagicMock(title="X", description="", claimed_tech=[], team_members=[], github_url=None, video_url=None, slides_url=None)

        with patch("app.crawler.project_scraper.scrape_devpost", side_effect=side_effect):
            await scrape_projects(batch_size=10)

        assert call_count == 0  # Never called for retry_count=3 project
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/crawler/test_project_scraper.py -v`
Expected: FAIL

- [ ] **Step 3: Implement project_scraper.py**

```python
# backend/app/crawler/project_scraper.py
"""Fill in metadata for uncrawled project rows using the Devpost scraper."""
import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import select, update
from app.database import async_session
from app.models import CrawledProject
from app.scraper import scrape_devpost
from app.checks.similarity import _get_head_commit

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
                            last_crawled_at=datetime.now(timezone.utc),
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
```

- [ ] **Step 4: Run tests**

Run: `pytest backend/tests/crawler/test_project_scraper.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/crawler/project_scraper.py backend/tests/crawler/test_project_scraper.py
git commit -m "feat: add per-project scraper with retry logic and git ls-remote"
```

---

## Chunk 3: Scheduler, Router, and Lifespan Integration

### Task 3.1: Crawler scheduler

**Files:**
- Create: `backend/app/crawler/scheduler.py`
- Test: `backend/tests/crawler/test_scheduler.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/crawler/test_scheduler.py
import pytest
from unittest.mock import patch, AsyncMock
from app.crawler.scheduler import run_crawl, is_crawling

@pytest.mark.asyncio
async def test_run_crawl_prevents_concurrent_runs():
    """When already running, second call should raise or be no-op."""
    # Simulate a crawl in progress
    with patch("app.crawler.scheduler._crawler_running", True):
        with pytest.raises(RuntimeError, match="already in progress"):
            await run_crawl()

@pytest.mark.asyncio
async def test_run_crawl_sets_and_clears_flag():
    """After a successful crawl, _crawler_running should be False."""
    with patch("app.crawler.scheduler.discover_hackathons", new_callable=AsyncMock) as mock_discover:
        with patch("app.crawler.scheduler.discover_submissions", new_callable=AsyncMock) as mock_disc_sub:
            with patch("app.crawler.scheduler.scrape_projects", new_callable=AsyncMock) as mock_scrape:
                mock_discover.return_value = []
                mock_disc_sub.return_value = []
                mock_scrape.return_value = 0

                await run_crawl()

                from app.crawler.scheduler import _crawler_running
                assert _crawler_running is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/crawler/test_scheduler.py -v`
Expected: FAIL

- [ ] **Step 3: Implement scheduler.py**

```python
# backend/app/crawler/scheduler.py
"""Crawl scheduler: orchestrates discovery -> submission discovery -> project scrape."""
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.database import async_session
from app.models import CrawledHackathon
from app.config import settings
from app.crawler.discovery import discover_hackathons
from app.crawler.submission_discovery import discover_submissions
from app.crawler.project_scraper import scrape_projects

logger = logging.getLogger(__name__)

_crawler_running: bool = False


def is_crawling() -> bool:
    """Check if a crawl is currently in progress."""
    return _crawler_running


async def run_crawl() -> dict:
    """Run a full crawl cycle.

    1. Discover new hackathons
    2. For active hackathons, discover submissions
    3. Scrape uncrawled projects

    Returns summary dict.
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

        # 2. Find "active" hackathons for submission discovery
        # Active = end_date in future OR ended within refresh window
        refresh_cutoff = datetime.now(timezone.utc) - timedelta(
            days=settings.crawler_refresh_window_days
        )

        async with async_session() as db:
            result = await db.execute(
                select(CrawledHackathon).where(
                    (CrawledHackathon.end_date.is_(None))
                    | (CrawledHackathon.end_date >= refresh_cutoff)
                )
            )
            active_hackathons = result.scalars().all()

        # 3. Discover submissions for each active hackathon
        for hk in active_hackathons:
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
```

- [ ] **Step 4: Run tests**

Run: `pytest backend/tests/crawler/test_scheduler.py -v`
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/crawler/scheduler.py backend/tests/crawler/test_scheduler.py
git commit -m "feat: add crawl scheduler (orchestration + concurrency guard)"
```

---

### Task 3.2: Crawler router and lifespan integration

**Files:**
- Create: `backend/app/routes/crawler.py`
- Modify: `backend/app/main.py:18-48`

- [ ] **Step 1: Write failing test for the trigger endpoint**

```python
# backend/tests/test_crawler_route.py
import pytest
from unittest.mock import patch, AsyncMock
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.routes.crawler import _require_organizer

# Override the auth dependency (matches existing conftest.py pattern)
async def _override_organizer():
    return {"sub": "test-user-id", "role": "organizer"}

app.dependency_overrides[_require_organizer] = _override_organizer

@pytest.mark.asyncio
async def test_trigger_crawl_returns_409_when_running():
    # Patch at the import site in routes/crawler.py (imported by value)
    with patch("app.routes.crawler.is_crawling", return_value=True):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/crawler/trigger")
            assert response.status_code == 409
            data = response.json()
            assert "already in progress" in data["detail"]

@pytest.mark.asyncio
async def test_trigger_crawl_starts_crawl():
    # Patch at the import site in routes/crawler.py (imported by value)
    with patch("app.routes.crawler.is_crawling", return_value=False):
        mock_run = AsyncMock(return_value={"new_hackathons": 0, "new_submissions": 0, "scraped_projects": 0})
        with patch("app.routes.crawler.run_crawl", mock_run):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post("/api/crawler/trigger")
                assert response.status_code == 202
                data = response.json()
                assert data["status"] == "started"
                mock_run.assert_awaited_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_crawler_route.py -v`
Expected: FAIL (404 or import error)

- [ ] **Step 3: Implement router at routes/crawler.py**

```python
# backend/app/routes/crawler.py
"""Crawler trigger endpoint (organizer-only)."""
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Header
from app.crawler.scheduler import is_crawling, run_crawl
from app.auth import decode_token
from app.models import UserRole

router = APIRouter()


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

    # Fire-and-forget: start crawl in background
    asyncio.create_task(run_crawl())

    return {"status": "started"}
```

- [ ] **Step 4: Integrate into main.py lifespan and routers**

Modify `backend/app/main.py`:

Add the import (after line 15):
```python
from app.routes.crawler import router as crawler_router
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.crawler.scheduler import run_crawl
from app.config import settings
```

Add the router (after line 47):
```python
app.include_router(crawler_router, prefix="/api/crawler", tags=["crawler"])
```

Modify the lifespan function (replace lines 18-23):
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup and start the crawler scheduler."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Start the crawler scheduler
    scheduler = AsyncIOScheduler()
    # Parse the cron expression (e.g., "0 3 * * 0" = Sunday 3 AM UTC)
    cron_parts = settings.crawler_schedule.split()
    scheduler.add_job(
        run_crawl,
        trigger="cron",
        minute=cron_parts[0],
        hour=cron_parts[1],
        day=cron_parts[2],
        month=cron_parts[3],
        day_of_week=cron_parts[4],
        id="devpost_crawl",
    )
    scheduler.start()

    yield

    scheduler.shutdown(wait=False)
```

- [ ] **Step 5: Run tests**

Run: `pytest backend/tests/test_crawler_route.py -v`
Expected: 2 PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/routes/crawler.py backend/app/main.py backend/tests/test_crawler_route.py
git commit -m "feat: add crawler trigger endpoint and lifespan scheduler integration"
```

---

## Chunk 4: Detection Checks

### Task 4.1: Cross-hackathon duplicate detection check

**Files:**
- Create: `backend/app/checks/cross_hackathon.py`
- Test: `backend/tests/checks/test_cross_hackathon.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/checks/test_cross_hackathon.py
import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock
from app.checks.interface import CheckContext, ScrapedData, HackathonInfo
from app.checks.cross_hackathon import check_cross_hackathon_duplicate

@pytest.mark.asyncio
async def test_no_duplicate_when_index_empty():
    """Check returns pass when crawled_projects is empty."""
    ctx = CheckContext(
        repo_path=None,
        scraped=ScrapedData(github_url="https://github.com/alice/unique-project"),
        submission_id=uuid.uuid4(),
        hackathon=HackathonInfo(
            id=uuid.uuid4(), name="Test Hack",
            start_date="2025-01-01T00:00:00", end_date="2025-01-03T00:00:00"
        ),
    )

    result = await check_cross_hackathon_duplicate(ctx)
    assert result.status == "pass"
    assert result.score == 0

@pytest.mark.asyncio
async def test_detects_exact_github_url_match_across_hackathons():
    """Same GitHub URL in a different hackathon should score 90."""
    from app.database import async_session
    from app.models import CrawledHackathon, CrawledProject
    from datetime import datetime, timezone

    hackathon_1_id = uuid.uuid4()
    hackathon_2_id = uuid.uuid4()
    duplicate_url = "https://github.com/alice/duplicate-project"

    # Seed: two hackathons, same GitHub URL in crawled_projects
    async with async_session() as db:
        db.add_all([
            CrawledHackathon(id=hackathon_1_id, devpost_url="http://dp.com/h/1", name="H1"),
            CrawledHackathon(id=hackathon_2_id, devpost_url="http://dp.com/h/2", name="H2"),
        ])
        await db.commit()

        db.add(CrawledProject(
            id=uuid.uuid4(),
            devpost_url="http://dp.com/s/dup",
            hackathon_id=hackathon_2_id,
            github_url=duplicate_url,
            title="Duplicate Project",
        ))
        await db.commit()

    ctx = CheckContext(
        repo_path=None,
        scraped=ScrapedData(github_url=duplicate_url, claimed_tech=[], team_members=[]),
        submission_id=uuid.uuid4(),
        hackathon=HackathonInfo(
            id=hackathon_1_id, name="H1",
            start_date="2025-01-01T00:00:00", end_date="2025-01-03T00:00:00"
        ),
    )
    result = await check_cross_hackathon_duplicate(ctx)
    assert result.status in ("warn", "fail")
    assert result.score >= 90

@pytest.mark.asyncio
async def test_no_duplicate_same_hackathon():
    """Same GitHub URL in the SAME hackathon should NOT flag (handled by similarity.py)."""
    from app.database import async_session
    from app.models import CrawledHackathon, CrawledProject

    hackathon_id = uuid.uuid4()
    same_url = "https://github.com/alice/test"

    # Seed: same hackathon has the project already crawled
    async with async_session() as db:
        db.add(CrawledHackathon(id=hackathon_id, devpost_url="http://dp.com/h/1", name="H1"))
        await db.commit()
        db.add(CrawledProject(
            id=uuid.uuid4(),
            devpost_url="http://dp.com/s/test",
            hackathon_id=hackathon_id,
            github_url=same_url,
        ))
        await db.commit()

    ctx = CheckContext(
        repo_path=None,
        scraped=ScrapedData(github_url=same_url, claimed_tech=[], team_members=[]),
        submission_id=uuid.uuid4(),
        hackathon=HackathonInfo(
            id=hackathon_id, name="H1",
            start_date="2025-01-01T00:00:00", end_date="2025-01-03T00:00:00"
        ),
    )
    result = await check_cross_hackathon_duplicate(ctx)
    # Same hackathon match should be excluded
    assert result.status == "pass"
    assert result.score == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/checks/test_cross_hackathon.py -v`
Expected: FAIL

- [ ] **Step 3: Implement cross_hackathon.py**

```python
# backend/app/checks/cross_hackathon.py
"""Check for cross-hackathon duplicate submissions using the crawled index."""
from app.checks.interface import CheckContext, CheckResult
from app.database import async_session
from app.models import CrawledProject
from app.checks.similarity import _parse_repo_name
from sqlalchemy import select


async def check_cross_hackathon_duplicate(context: CheckContext) -> CheckResult:
    """Check if the same project appears in other hackathons in the crawled index."""
    score = 0
    details: dict = {"matches": []}
    evidence: list[str] = []

    github_url = context.scraped.github_url
    if not github_url:
        return CheckResult(
            check_name="cross-hackathon-duplicate",
            check_category="cross_hackathon",
            score=0,
            status="pass",
            details={"reason": "no github URL"},
            evidence=[],
        )

    current_hackathon_id = str(context.hackathon.id) if context.hackathon else None

    async with async_session() as db:
        # 1. Exact GitHub URL match
        result = await db.execute(
            select(CrawledProject).where(
                CrawledProject.github_url == github_url.strip().lower()
            ).limit(20)
        )
        matches = result.scalars().all()

        for match in matches:
            if current_hackathon_id and str(match.hackathon_id) == current_hackathon_id:
                continue  # Same hackathon, handled by similarity.py

            score = max(score, 90)
            details["matches"].append({
                "type": "exact_github_url",
                "devpost_url": match.devpost_url,
                "hackathon_id": str(match.hackathon_id),
                "title": match.title,
            })
            evidence.append(
                f"Same GitHub URL ({github_url}) found in another hackathon: {match.devpost_url}"
            )

        # 2. Commit hash overlap (if commit_hash is provided in scraped data)
        own_commit = getattr(context.scraped, "commit_hash", None)
        if own_commit:
            hash_result = await db.execute(
                select(CrawledProject).where(
                    CrawledProject.commit_hash == own_commit,
                    CrawledProject.github_url != github_url.strip().lower(),
                ).limit(20)
            )
            for proj in hash_result.scalars().all():
                if current_hackathon_id and str(proj.hackathon_id) == current_hackathon_id:
                    continue
                score = max(score, 85)
                details["matches"].append({
                    "type": "same_commit_hash",
                    "commit_hash": own_commit[:8],
                    "devpost_url": proj.devpost_url,
                    "github_url": proj.github_url,
                    "hackathon_id": str(proj.hackathon_id),
                })
                evidence.append(
                    f"Same HEAD commit ({own_commit[:8]}) in another hackathon: {proj.devpost_url}"
                )

        # 3. Same repo name (different owner)
        repo_name = _parse_repo_name(github_url)
        if repo_name:
            name_result = await db.execute(
                select(CrawledProject).where(
                    CrawledProject.github_url.isnot(None),
                    CrawledProject.github_url != github_url.strip().lower(),
                ).limit(200)
            )
            for proj in name_result.scalars().all():
                if not proj.github_url:
                    continue
                if current_hackathon_id and str(proj.hackathon_id) == current_hackathon_id:
                    continue
                other_name = _parse_repo_name(proj.github_url)
                if other_name and other_name == repo_name:
                    # Check it's a different owner
                    score = max(score, 40)
                    details["matches"].append({
                        "type": "same_repo_name",
                        "repo_name": repo_name,
                        "devpost_url": proj.devpost_url,
                        "github_url": proj.github_url,
                    })
                    evidence.append(
                        f"Same repo name '{repo_name}' (different owner) in another hackathon: {proj.devpost_url}"
                    )

    score = min(100, score)
    if score <= 30:
        status = "pass"
    elif score <= 60:
        status = "warn"
    else:
        status = "fail"

    return CheckResult(
        check_name="cross-hackathon-duplicate",
        check_category="cross_hackathon",
        score=score,
        status=status,
        details=details,
        evidence=evidence,
    )
```

- [ ] **Step 4: Run tests**

Run: `pytest backend/tests/checks/test_cross_hackathon.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/checks/cross_hackathon.py backend/tests/checks/test_cross_hackathon.py
git commit -m "feat: add cross-hackathon duplicate detection check"
```

---

### Task 4.2: Repeat offender tracking check

**Files:**
- Create: `backend/app/checks/repeat_offender.py`
- Test: `backend/tests/checks/test_repeat_offender.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/checks/test_repeat_offender.py
import uuid
import pytest
from app.checks.interface import CheckContext, ScrapedData, HackathonInfo
from app.checks.repeat_offender import check_repeat_offender

@pytest.mark.asyncio
async def test_no_team_members_returns_pass():
    """Check returns pass when there are no team members."""
    ctx = CheckContext(
        repo_path=None,
        scraped=ScrapedData(team_members=[]),
        submission_id=uuid.uuid4(),
    )
    result = await check_repeat_offender(ctx)
    assert result.status == "pass"
    assert result.score == 0

@pytest.mark.asyncio
async def test_team_members_without_github_returns_pass():
    """Team members without GitHub usernames should score 0."""
    ctx = CheckContext(
        repo_path=None,
        scraped=ScrapedData(team_members=[
            {"name": "Alice", "devpost_profile": "/alice", "github": None},
            {"name": "Bob", "devpost_profile": "/bob", "github": None},
        ]),
        submission_id=uuid.uuid4(),
    )
    result = await check_repeat_offender(ctx)
    assert result.status == "pass"
    assert result.score == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/checks/test_repeat_offender.py -v`
Expected: FAIL

- [ ] **Step 3: Implement repeat_offender.py**

```python
# backend/app/checks/repeat_offender.py
"""Check if team members appear in previously flagged submissions."""
from sqlalchemy import select, or_
from app.checks.interface import CheckContext, CheckResult
from app.database import async_session
from app.models import CrawledProject, Submission, Verdict


async def check_repeat_offender(context: CheckContext) -> CheckResult:
    """Check if any team member has been flagged in prior hackathons."""
    score = 0
    details: dict = {"prior_flags": [], "suspicious_patterns": []}
    evidence: list[str] = []

    team_members = context.scraped.team_members or []
    if not team_members:
        return CheckResult(
            check_name="repeat-offender",
            check_category="repeat_offender",
            score=0,
            status="pass",
            details={"reason": "no team members"},
            evidence=[],
        )

    # Extract GitHub usernames from team members
    github_usernames: list[str] = []
    for member in team_members:
        gh = member.get("github", "")
        if gh:
            # Normalize: extract username from full URL
            if "github.com/" in gh:
                username = gh.split("github.com/")[-1].strip("/")
                if username and "/" not in username:
                    github_usernames.append(username.lower())
            elif not gh.startswith("github_uid:"):
                # Plain username
                github_usernames.append(gh.lower())

    if not github_usernames:
        return CheckResult(
            check_name="repeat-offender",
            check_category="repeat_offender",
            score=0,
            status="pass",
            details={"reason": "no github usernames found"},
            evidence=[],
        )

    async with async_session() as db:
        # Find flagged submissions (verdict = flagged or review)
        flagged_result = await db.execute(
            select(Submission).where(
                or_(
                    Submission.verdict == Verdict.flagged,
                    Submission.verdict == Verdict.review,
                )
            ).limit(500)
        )
        flagged_subs = flagged_result.scalars().all()

        flagged_github_urls: set[str] = set()
        for sub in flagged_subs:
            if sub.github_url:
                flagged_github_urls.add(sub.github_url.strip().lower())

        flagged_count = 0
        for username in github_usernames:
            # Query crawled_projects for projects involving this username
            # team_members is JSONB — search for the username in any member's github field
            # For SQLite compatibility, we fetch and filter in Python
            all_proj_result = await db.execute(
                select(CrawledProject).where(
                    CrawledProject.github_url.isnot(None),
                ).limit(1000)
            )
            all_projects = all_proj_result.scalars().all()

            for proj in all_projects:
                members = proj.team_members or []
                for m in members:
                    gh = m.get("github", "")
                    if not gh:
                        continue
                    if "github.com/" in gh:
                        member_username = gh.split("github.com/")[-1].strip("/").lower()
                    elif not gh.startswith("github_uid:"):
                        member_username = gh.lower()
                    else:
                        continue

                    if member_username == username:
                        # Check if any project by this member was flagged
                        if proj.github_url and proj.github_url.strip().lower() in flagged_github_urls:
                            flagged_count += 1
                            details["prior_flags"].append({
                                "github_username": username,
                                "devpost_url": proj.devpost_url,
                                "title": proj.title,
                                "github_url": proj.github_url,
                            })
                            evidence.append(
                                f"Team member '{username}' appears in flagged project: {proj.devpost_url}"
                            )
                            break

        # Score: 30 per flagged prior, capped at 60
        score = min(flagged_count * 30, 60)

        # Suspicious pattern: same Devpost profile, different GitHub
        devpost_to_githubs: dict[str, set[str]] = {}
        for member in team_members:
            dp = member.get("devpost_profile", "")
            gh = member.get("github", "")
            if dp and gh:
                devpost_to_githubs.setdefault(dp, set()).add(gh)

        for dp_profile, gh_set in devpost_to_githubs.items():
            if len(gh_set) > 1:
                score = max(score, 20)
                details["suspicious_patterns"].append({
                    "devpost_profile": dp_profile,
                    "github_accounts": list(gh_set),
                })
                evidence.append(
                    f"Devpost profile {dp_profile} linked to multiple GitHub accounts: {gh_set}"
                )

    score = min(100, score)
    if score <= 30:
        status = "pass"
    elif score <= 60:
        status = "warn"
    else:
        status = "fail"

    return CheckResult(
        check_name="repeat-offender",
        check_category="repeat_offender",
        score=score,
        status=status,
        details=details,
        evidence=evidence,
    )
```

- [ ] **Step 4: Run tests**

Run: `pytest backend/tests/checks/test_repeat_offender.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/checks/repeat_offender.py backend/tests/checks/test_repeat_offender.py
git commit -m "feat: add repeat offender tracking check"
```

---

## Chunk 5: Wire Everything Together

### Task 5.1: Register checks in __init__.py and final integration

**Files:**
- Modify: `backend/app/checks/__init__.py`
- Test: run full test suite

- [ ] **Step 1: Register the new checks**

Modify `backend/app/checks/__init__.py`:

```python
"""HackVerify check registry."""
from app.checks.interface import CheckFn, CheckContext, CheckResult, CheckCategory, ScrapedData, HackathonInfo
from app.checks import timeline, devpost_alignment_ai, submission_history, asset_integrity, ai_detection, contributor_audit
from app.checks import cross_hackathon, repeat_offender

# All checks except similarity (batch)
CHECKS: list[CheckFn] = [
    timeline.check_commits,
    devpost_alignment_ai.check_alignment_ai,
    submission_history.check_history,
    contributor_audit.check_contributors,
    asset_integrity.check_assets,
    ai_detection.check_ai,
    cross_hackathon.check_cross_hackathon_duplicate,
    repeat_offender.check_repeat_offender,
]

WEIGHTS: dict[str, float] = {
    "timeline": 0.25,
    "devpost_alignment": 0.30,
    "submission_history": 0.20,
    "asset_integrity": 0.15,
    "cross_team_similarity": 0.05,
    "ai_detection": 0.05,
    "cross_hackathon": 0.10,
    "repeat_offender": 0.05,
}
```

Note: The existing weights sum to 1.0. With the two new weights, the total is 1.15. The analyzer normalizes by dividing weighted_sum by total_weight, so this is fine — each check's score is weighted relative to the others.

- [ ] **Step 2: Run full test suite**

Run: `pytest backend/tests/ -v`
Expected: All tests pass

- [ ] **Step 3: Verify the app starts**

Run: `python -c "from app.main import app; print('App loaded successfully')"`
Expected: "App loaded successfully"

- [ ] **Step 4: Verify all checks are registered**

Run:
```python
python -c "
from app.checks import CHECKS, WEIGHTS
print(f'Checks: {len(CHECKS)}')
print(f'Weights: {len(WEIGHTS)}')
for c in CHECKS:
    print(f'  - {c.__module__}.{c.__name__}')
"
```
Expected: 8 checks listed, 8 weights listed

- [ ] **Step 5: Commit**

```bash
git add backend/app/checks/__init__.py
git commit -m "feat: register cross-hackathon duplicate and repeat-offender checks"
```

---

## Summary

**Files created:**
- `backend/app/crawler/__init__.py`
- `backend/app/crawler/discovery.py`
- `backend/app/crawler/submission_discovery.py`
- `backend/app/crawler/project_scraper.py`
- `backend/app/crawler/scheduler.py`
- `backend/app/routes/crawler.py`
- `backend/app/checks/cross_hackathon.py`
- `backend/app/checks/repeat_offender.py`
- `backend/tests/test_crawler_models.py`
- `backend/tests/test_check_categories.py`
- `backend/tests/test_crawler_route.py`
- `backend/tests/crawler/test_discovery.py`
- `backend/tests/crawler/test_submission_discovery.py`
- `backend/tests/crawler/test_project_scraper.py`
- `backend/tests/crawler/test_scheduler.py`
- `backend/tests/checks/test_cross_hackathon.py`
- `backend/tests/checks/test_repeat_offender.py`

**Files modified:**
- `backend/app/models.py` — add CrawledHackathon, CrawledProject (with indexes)
- `backend/app/checks/interface.py` — add CROSS_HACKATHON, REPEAT_OFFENDER enums
- `backend/app/checks/__init__.py` — register two new checks and weights
- `backend/app/config.py` — add crawler_schedule, crawler_refresh_window_days
- `backend/app/main.py` — add crawler router, AsyncIOScheduler in lifespan
- `backend/requirements.txt` — add apscheduler

**Total commits:** 8
