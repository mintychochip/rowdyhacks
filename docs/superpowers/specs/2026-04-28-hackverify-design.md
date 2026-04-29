# HackVerify — Design Spec

## Overview

HackVerify is a PWA that detects cheating in hackathon submissions. It accepts a Devpost URL (or GitHub URL), runs a suite of integrity checks, and produces a risk report with individual check scores and an aggregated risk score.

**Users:** Hackathon organizers (dashboard with submission queue) and participants (self-check before submitting).

## Tech Stack

- **Backend:** Python / FastAPI
- **Frontend:** React (PWA — manifest, installable, responsive)
- **Database:** PostgreSQL
- **Auth:** JWT with roles (organizer, participant)
- **Deployment:** Traditional server (cheap VM)
- **External APIs:** GitHub API (required), YouTube Data API (optional — video timestamp check skipped if not configured)

## Architecture

```
React PWA → FastAPI → PostgreSQL
                  ├→ Devpost (scraping — rate-limited, no API)
                  ├→ GitHub API (repo analysis)
                  └→ Git clone (shallow, for code analysis)
```

Analysis runs asynchronously. User submits URL → submission created with status "pending" → background task runs all checks → status becomes "completed" with risk score.

## Check Interface (Contract)

Every check is a function with this signature:

```python
async def check(context: CheckContext) -> CheckResult:
```

**Input (`CheckContext`):**
- `repo_path: Path | None` — path to cloned repo (None if no GitHub link found)
- `scraped: ScrapedData` — parsed Devpost data (title, description, claimed_tech, team_members, github_url, video_url, slides_url, etc.)
- `submission_id: UUID`
- `hackathon: Hackathon | None` — hackathon date range if submission is linked to one

**Output (`CheckResult`):**
- `check_name: str` — e.g. "commit-timestamps"
- `check_category: str` — e.g. "timeline"
- `score: int` — 0-100 (0=clean, 100=highly suspicious)
- `status: CheckStatus` — derived from score thresholds (see below)
- `details: dict` — check-specific findings (timestamps, missing imports, etc.)
- `evidence: list[str]` — supporting links/file paths/line numbers

**Score → Status mapping (individual check level):**
| Score | Status |
|-------|--------|
| 0-30 | pass |
| 31-60 | warn |
| 61-100 | fail |

`error` status is reserved for runtime failures (timeout, API error, unparseable repo) — not a scoring tier.

**At the aggregate level**, the same score thresholds map to `clean`/`review`/`flagged` (see Aggregate Scoring below). The different labels reflect different semantic levels: pass/warn/fail = individual check, clean/review/flagged = overall submission verdict.

## Data Model

### submissions
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| devpost_url | text | |
| github_url | text | nullable, extracted from Devpost or provided directly |
| project_title | text | scraped from Devpost |
| project_description | text | scraped from Devpost |
| claimed_tech | text[] | from Devpost "Built With" |
| team_members | jsonb | [{name, devpost_profile}] |
| hackathon_id | UUID | nullable, FK → hackathons |
| submitted_by | UUID | nullable FK → users (null = anonymous self-check) |
| status | enum | pending → analyzing → completed / failed |
| risk_score | int | 0-100 aggregate, computed when all checks done |
| verdict | enum | clean / review / flagged (derived from risk_score) |
| created_at | timestamptz | |
| completed_at | timestamptz | |

### check_results
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| submission_id | UUID | FK → submissions |
| check_category | text | "timeline", "devpost_alignment", "submission_history", "asset_integrity", "cross_team_similarity", "ai_detection" |
| check_name | text | e.g. "commit-timestamps", "claimed-vs-actual-apis" |
| score | int | 0-100 (0=clean, 100=suspicious) |
| status | enum | pass / warn / fail / error |
| details | jsonb | check-specific findings |
| evidence | text[] | links, line numbers, snippets |
| created_at | timestamptz | |

### users
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| email | text | unique |
| name | text | |
| role | enum | organizer / participant |
| password_hash | text | bcrypt |
| created_at | timestamptz | |

### hackathons
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| name | text | |
| start_date | timestamptz | |
| end_date | timestamptz | |
| organizer_id | UUID | FK → users |
| created_at | timestamptz | |

## API Routes

```
POST /api/auth/register              — create account
POST /api/auth/login                 — return JWT

POST /api/check                      — submit Devpost/GitHub URL for analysis (auth optional)
GET  /api/check/{id}                 — get submission status + check_results
GET  /api/check/{id}/report          — full report JSON
POST /api/check/{id}/retry           — retry a failed/errored submission (re-runs from scratch, preserves old results)

GET  /api/dashboard                  — organizer: list submissions (filterable by hackathon, status, verdict)
POST /api/hackathons                 — organizer: create hackathon
GET  /api/hackathons/{id}/stats      — aggregate stats for a hackathon
POST /api/hackathons/{id}/similarity — trigger cross-team similarity batch run
```

### Auth & Anonymous Self-Check

- **Anonymous self-check:** `POST /api/check` without auth creates a submission with `submitted_by = null`. The response includes a short-lived `access_token` (UUID, not JWT) scoped to that submission ID. The user passes this token as a query param on `GET /api/check/{id}` to view results. Tokens expire after 7 days.
- **Authenticated submissions:** `submitted_by` is set to the user's ID. Standard JWT auth protects organizer-only routes (`/dashboard`, `/hackathons`).
- **Rate limiting:** `POST /api/check` is rate-limited to 10 requests per minute per IP (anonymous) or 30 per minute (authenticated).

### Async Completion

Analysis is async. After `POST /api/check`, the frontend polls `GET /api/check/{id}` (status field) every 2 seconds until `completed` or `failed`. The submission object includes `risk_score` and immediate check results once complete.

**Idempotency:** `POST /api/check` with the same URL returns the existing submission (if `completed` and < 1 hour old) rather than creating a duplicate analysis. Newer or previously-failed submissions are re-analyzed.

**URL validation:** Non-Devpost, non-GitHub URLs return 400 with a descriptive error message.

**Repo cleanup:** Cloned repos are stored in a temp directory and deleted immediately after the analysis completes (or on error). No repos persist on disk between analyses.

## Analysis Pipeline

When a URL is submitted:

1. **Scrape Devpost** (if Devpost URL provided) — extract title, description, team members, claimed tech stack, GitHub repo link, demo video URL, slides URL. Uses HTTP GET + HTML parsing (BeautifulSoup). Rate-limited to avoid blocking. If scraping fails → submission marked "failed", no checks run. If a raw GitHub URL is submitted instead, skip this step — `ScrapedData` fields are `None` and checks that depend on scraped data return "warn" with a note that Devpost data was unavailable.
2. **Clone repo** (shallow, `git clone --depth 1`) if GitHub URL found and public. If repo is private or inaccessible, run remaining checks with `repo_path = None`.
3. **Run all checks in parallel** — each check receives the cloned repo path + scraped data. Checks are independent; one failing does not block others.
4. **Compute aggregate risk score** — weighted sum of individual check scores. If a check errors, its weight is excluded from the denominator.
5. **Store everything**, update submission status to "completed".

### Cross-Team Similarity (Late Binding)

The cross-team similarity check requires comparing against all other submissions in the same hackathon. To avoid blocking:

- The initial analysis runs all checks _except_ cross-team similarity.
- Cross-team similarity is computed in batch when the organizer requests it (e.g., after all submissions are in).
- Until then, the aggregate score excludes cross-team similarity weight.
- When batch similarity is run, existing submission scores are updated.

### Error Handling & Resilience

| Scenario | Behavior |
|----------|----------|
| Devpost unreachable | Submission → "failed", no checks run |
| GitHub repo private/404 | `repo_path = None`, run text/scrape-only checks |
| Single check throws/timeout | That check → status "error", others continue |
| GitHub API rate limited | Exponential backoff, 3 retries max |
| Check timeout | 60s per check, kill and mark "error" |
| All checks error | Submission → "failed" |

Failed submissions can be retried (POST /api/check/{id}/retry).

## Checks

### P0 — Timeline & Commit Analysis (weight: 25%)
- Commit timestamps vs hackathon window
- Giant single commit near deadline (>80% of code in one commit within 1hr of deadline)
- Commits before hackathon start
- Unusual commit frequency patterns
- Suspicious/generic commit messages

### P0 — Devpost vs GitHub Alignment (weight: 30%)
- Claimed features found in code (imports, function names, files)
- Claimed APIs/sponsor integrations verified (actual API calls, keys)
- Tech stack matches package files (package.json, requirements.txt, etc.)
- Dead code / unused files ratio
- Missing source code (repo is just boilerplate/README)

### P1 — Submission History (weight: 20%)
- Same repo submitted to previous hackathons (scrape Devpost search for project name)
- Team members with prior flags — query existing `check_results` for `fail`/`warn` statuses on past submissions matching team member devpost usernames or emails
- README references wrong hackathon name/date

### P1 — Asset Integrity (weight: 15%)
- Broken links — HEAD/GET the GitHub, demo video, and slides URLs; flag any returning 4xx/5xx or timing out (10s per link)
- Missing required assets — flag if submission lacks a README, demo video link, or at least one screenshot (specific requirements configurable per hackathon)
- Demo video upload timestamp vs hackathon dates (YouTube API)
- Private/inaccessible repo
- Missing AI disclosure — if README lacks any mention of AI tools (ChatGPT, Copilot, Claude, etc.) and code shows AI-typical patterns

### P2 — Cross-Team Similarity (weight: 5%)
- Code similarity across submissions in the same hackathon (embedding-based)
- Same repo/code appearing under multiple teams
- Computed as a batch operation after all submissions are in

### P2 — AI Generation Detection (weight: 5%)
- Uniform code style, excessive comments, lack of human-typical errors
- Sudden style shifts within files (patchwork from multiple sources)

## Aggregate Scoring

Each check returns a score 0-100. The aggregate risk score is the weighted sum (excluding errored checks and deferred cross-team similarity until batch run):

```
risk_score = Σ (check_score × weight) / Σ weights
```

Verdict thresholds (derived from risk_score):
- 0-30: **clean** (green)
- 31-60: **review** (yellow, needs manual review)
- 61-100: **flagged** (red, high risk)

## Report Format

The report page shows:
1. Overall risk score + verdict (big number, colored)
2. Category breakdown (individual scores with color coding and status labels)
3. Per-category detail sections with expandable evidence

## Frontend Screens

1. **Analyze page** (default) — paste URL, submit, see results inline
2. **Report page** — detailed view of a completed analysis
3. **Dashboard** (organizer only) — sortable/filterable submission queue
4. **Hackathon setup** (organizer only) — define hackathon date range
5. **Self-check** (public, no login) — same as analyze but for anonymous participants
6. **Login/Register** — auth pages

## PWA Requirements

- Installable (manifest.json)
- Responsive (works on phone/tablet/desktop)
