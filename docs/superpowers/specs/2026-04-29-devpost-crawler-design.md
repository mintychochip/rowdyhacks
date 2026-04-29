# Devpost Bulk Crawler & Cross-Hackathon Detection — Design Spec

## Overview

Build a bulk Devpost crawler that indexes all hackathon submission pages to power:
- Cross-hackathon duplicate detection (same project submitted to multiple events)
- Repeat offender tracking (same people showing up in flagged submissions across events)

(Code-level similarity across hackathons is deferred to a follow-up spec — this spec establishes the data foundation needed for it.)

The crawler reuses the existing per-page scraper and extends the current FastAPI app with new tables, a crawling scheduler, and new detection checks.

---

## Data Model

Two new tables to build the Devpost index, separate from the existing `submissions` table (which stores HackVerify analysis requests):

### `crawled_hackathons`

| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| devpost_url | Text | e.g. `https://devpost.com/hackathons/hackmit-2025` |
| name | String(300) | |
| start_date | DateTime(tz) | nullable, parsed from page |
| end_date | DateTime(tz) | nullable |
| submission_count | Integer | how many submissions the gallery says it has |
| last_crawled_at | DateTime(tz) | when we last refreshed this hackathon's projects |
| created_at | DateTime(tz) | |

### `crawled_projects`

| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| devpost_url | Text | unique, the submission page URL |
| hackathon_id | UUID | FK → crawled_hackathons.id |
| title | Text | |
| description | Text | |
| claimed_tech | ArrayOfStrings | |
| team_members | JsonType | list of `{name, devpost_profile, github}` |
| github_url | Text | nullable |
| commit_hash | String(40) | nullable, HEAD hash via existing `_get_head_commit()` in similarity.py |
| video_url | Text | nullable |
| slides_url | Text | nullable |
| retry_count | Integer | default 0, incremented per failed scrape |
| last_crawled_at | DateTime(tz) | |
| created_at | DateTime(tz) | |

### Cross-referencing with Submissions

When a HackVerify submission is analyzed, cross-reference by matching `submissions.github_url` to `crawled_projects.github_url`. If a match is found in a different `hackathon_id`, flag as cross-hackathon duplicate. Additionally compare `crawled_projects.commit_hash` values — if two projects have different GitHub URLs but the same commit hash, they are the same codebase.

---

## Crawler Architecture

Four modules, all within the existing backend:

### 1. Hackathon Discovery (`crawler/discovery.py`)

Entry point. Scrapes Devpost's hackathon listing pages to find hackathons we haven't crawled yet.

- Start from `https://devpost.com/hackathons` — paginated list of all hackathons, ordered by recency
- Paginate through listing pages. Stop when a page contains only hackathons already in the index (no new URLs found on that entire page), or after 50 pages (safety cap).
- Extract each hackathon's URL, name, dates from the listing cards
- Insert new ones into `crawled_hackathons`, skip already-crawled ones
- Returns list of new/updated hackathon IDs

### 2. Submission Discovery (`crawler/submission_discovery.py`)

For a given hackathon, finds all submission page URLs.

- Scrapes the hackathon's submission gallery page (e.g., `devpost.com/hackathons/foo/submissions`)
- Handles pagination — Devpost shows ~20 submissions per page. Stop when a page returns no new submission URLs, or after 200 pages (safety cap for large hackathons).
- Extracts each submission's Devpost URL
- Inserts new URLs into `crawled_projects` with just `devpost_url` + `hackathon_id` (metadata filled later by the per-project scraper)

### 3. Per-Project Scraper (`crawler/project_scraper.py`)

Fills in metadata for uncrawled project rows.

- Calls the existing `scrape_devpost()` function for each uncrawled project
- Runs `git ls-remote` (reusing the existing `_get_head_commit()` from `similarity.py`) to capture the HEAD commit hash
- Updates the `crawled_projects` row with full metadata
- Failed scrapes increment `retry_count` on the row. Rows where `retry_count < 3` and `last_crawled_at = null` are retried on the next crawl cycle. Rows where `retry_count >= 3` and `last_crawled_at = null` are permanently skipped (no more retries).

### 4. Scheduler (`crawler/scheduler.py`)

An in-process `apscheduler` job using `AsyncIOScheduler` (from `apscheduler.schedulers.asyncio`) registered in the FastAPI lifespan:

- **Schedule:** Weekly (day/time configurable via `CRAWLER_SCHEDULE` env var, defaults to Sunday 3 AM UTC)
- **Concurrency safety:** A boolean `_crawler_running` flag prevents overlapping runs. If `POST /api/crawler/trigger` fires during a scheduled run, the trigger returns `409 Conflict` with `{"detail": "Crawl already in progress"}`.
- **What "active hackathon" means for refresh:** Hackathons whose `end_date` is in the future, plus hackathons that ended within the last 30 days (to catch late submissions). Controlled by `CRAWLER_REFRESH_WINDOW_DAYS` env var (default 30).
- **Rate limiting:** Uses an `asyncio.Semaphore(5)` to limit concurrent requests to Devpost.
- **Endpoint:** `POST /api/crawler/trigger` (organizer-only) — runs a full crawl cycle (discovery + submission scraping). Returns `{"status": "started"}` or 409.

### 5. New Dependency

Add `apscheduler` to `requirements.txt` (uses `AsyncIOScheduler` from `apscheduler.schedulers.asyncio` for async compatibility with FastAPI).

---

## Detection Features

### A. Cross-Hackathon Duplicate Detection

**Implementation:** New check function at `checks/cross_hackathon.py`, registered in `checks/__init__.py` with category `CROSS_HACKATHON` and weight **0.10**.

Runs in the per-submission pipeline when a Devpost URL is analyzed. Queries `crawled_projects` for the submission's `github_url` (and `commit_hash` if available from git clone) across different `hackathon_id` values:

| Detection | Score | Logic |
|---|---|---|
| Exact GitHub URL match, different hackathon | 90 | Same repo submitted to multiple events |
| Same commit hash, different GitHub URL, different hackathon | 85 | Cloned/renamed but identical codebase |
| Same repo name (different owner), different hackathon | 40 | Could be naming collision or renamed fork |

Details and evidence are persisted in the existing `CheckResultModel`, matching the pattern of all other checks.

**DB session:** Both new checks obtain database sessions via `app.database.async_session` directly (same pattern as `similarity.py`'s `run_similarity()`). The `CheckContext` dataclass is not modified — only checks that need DB access use the session factory directly, keeping the existing `CheckContext` contract clean.

### B. Repeat Offender Tracking

**Implementation:** New check function at `checks/repeat_offender.py`, registered in `checks/__init__.py` with category `REPEAT_OFFENDER` and weight **0.05**.

Runs in the per-submission pipeline. For each team member (by GitHub username) on the submission, queries `crawled_projects` to find other hackathons they've participated in:

| Detection | Score | Logic |
|---|---|---|
| GitHub username appears in a previously flagged/under-review submission | 30 | Scores per flagged prior submission, capped at 60 total |
| Same Devpost profile linked to different GitHub usernames across hackathons | 20 | Added to details as "suspicious pattern" |

Flagged prior submissions are those with `verdict = flagged` or `verdict = review` in the existing `submissions` table. Queries use the `crawled_projects.team_members` JSONB field to find matching GitHub usernames.

Details include: list of prior hackathons, prior verdicts, and the matching GitHub username/Devpost profile for each team member.

No new endpoint needed for v1 — the check surfaces prior-offender findings inline in the existing submission report. A standalone lookup endpoint (`GET /api/check/profile-lookup?github=...`) can be added later if needed.

---

## Integration Points

### ORM Models (`backend/app/models.py`)

Add two new SQLAlchemy model classes alongside the existing models, using the same cross-dialect type decorators (`Guid`, `ArrayOfStrings`, `JsonType`):

- `CrawledHackathon` — maps to `crawled_hackathons` table. Include a `projects = relationship("CrawledProject", back_populates="hackathon")` for consistency with existing model patterns.
- `CrawledProject` — maps to `crawled_projects` table. `hackathon_id` FK → `crawled_hackathons.id`. Include `hackathon = relationship("CrawledHackathon", back_populates="projects")`.

Database indexes to add:
- **B-tree index on `crawled_projects.github_url`** — cross-hackathon duplicate lookups match on this column
- **B-tree index on `crawled_projects.commit_hash`** — duplicate detection queries by commit hash
- **(Later) GIN index on `crawled_projects.team_members`** — repeat offender lookups query GitHub usernames in JSONB. Can be added if query performance degrades.

Tables are auto-created by the existing `Base.metadata.create_all` call in `main.py`'s lifespan.

### Settings (`backend/app/config.py`)

Add fields to the existing `Settings` class (which uses `pydantic-settings` `BaseSettings` with `HACKVERIFY_` prefix):

| Env var | Field | Default |
|---|---|---|
| `HACKVERIFY_CRAWLER_SCHEDULE` | `crawler_schedule` | Sunday 3 AM UTC cron expression |
| `HACKVERIFY_CRAWLER_REFRESH_WINDOW_DAYS` | `crawler_refresh_window_days` | `30` |

This follows the existing pattern where all env vars use the `HACKVERIFY_` prefix and are declared as typed fields on the `Settings` model.

### Router & Lifespan (`backend/app/main.py`)

- Create `backend/app/routes/crawler.py` with a `router` containing `POST /trigger` (organizer-only, requires auth)
- Import and include the router in `main.py`: `app.include_router(crawler_router, prefix="/api/crawler", tags=["crawler"])`
- Extend the `lifespan` context manager in `main.py`:
  - After `create_all`: start the apscheduler job from `crawler/scheduler.py`
  - During runtime: the scheduler runs in the background
  - After `yield` (shutdown): stop the scheduler gracefully

### Checks Registration (`backend/app/checks/__init__.py`)

Add the two new check functions and their weights:

```python
from app.checks.cross_hackathon import check_cross_hackathon_duplicate
from app.checks.repeat_offender import check_repeat_offender

CHECKS = [
    ...existing...,
    check_cross_hackathon_duplicate,
    check_repeat_offender,
]

WEIGHTS = {
    ...existing...,
    CheckCategory.CROSS_HACKATHON: 0.10,
    CheckCategory.REPEAT_OFFENDER: 0.05,
}
```

New `CheckCategory` enum values to add in `checks/interface.py`:
- `CROSS_HACKATHON = "cross_hackathon"`
- `REPEAT_OFFENDER = "repeat_offender"`

---
## Implementation Notes

- Reuses the existing `scrape_devpost()` function — no need to rewrite per-page scraping
- Reuses existing `httpx.AsyncClient` / curl fallback pattern for Devpost WAF bypass
- Reuses existing `_get_head_commit()` from `similarity.py` for commit hash capture (no duplicate code)
- Reuses existing `CheckResultModel` for persisting detection results from the new checks — same pattern as all other checks in `checks/__init__.py`
- Uses `apscheduler` for cron scheduling (new dependency to add to `requirements.txt`)
- `git ls-remote` is fast and cheap — no need to clone repos during crawling
- Crawler shares the database with the API — no new infrastructure needed
- Crawler runs in-process within the FastAPI lifespan (same process as the API server, not a separate service)

### Follow-up Specs

- **Code-level similarity** (minhash/SimHash across repos in the index) — requires the crawled data this spec produces. Will be a new batch check extending or complementing the existing `similarity.py`.
