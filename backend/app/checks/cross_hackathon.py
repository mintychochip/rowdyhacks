"""Check for cross-hackathon duplicate submissions using the crawled index."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.checks.interface import CheckContext, CheckResult
from app.checks.similarity import _parse_repo_name
from app.database import async_session
from app.models import CrawledProject


@asynccontextmanager
async def _resolve_session(
    db: AsyncSession | None,
) -> AsyncIterator[AsyncSession]:
    """Yield the provided database session, or create one from the default pool.

    Behavior:
    1. If a session is provided, yield it directly.
    2. Otherwise, open a new async session from the global pool and yield it.

    Raises: None
    Side Effects: None (session creation is scoped to the async context manager).
    Dependencies: app.database.async_session.
    Consumers: Internal helper used by check_cross_hackathon_duplicate and check_repeat_offender.
    """
    if db is not None:
        yield db
    else:
        async with async_session() as session:
            yield session


async def check_cross_hackathon_duplicate(
    context: CheckContext,
    db: AsyncSession | None = None,
) -> CheckResult:
    """Check if the same project appears in other hackathons in the crawled index.

    Behavior:
    1. Return early if no GitHub URL is present in the scraped data.
    2. Open a database session (provided or newly created).
    3. Query CrawledProject for exact GitHub URL matches across other hackathons.
    4. Query for matching HEAD commit hashes across different GitHub URLs.
    5. Query for duplicate repository names with different owners.
    6. Compute a score based on match severity and return a CheckResult.

    Raises: None
    Side Effects: None (read-only database query).
    Dependencies: app.checks.interface.CheckContext, app.checks.interface.CheckResult, app.checks.similarity._parse_repo_name, app.database.async_session, app.models.CrawledProject.
    Consumers: Internal check used by the analyzer pipeline.
    """
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

    async with _resolve_session(db) as session:
        # 1. Exact GitHub URL match
        result = await session.execute(
            select(CrawledProject).where(CrawledProject.github_url == github_url.strip().lower()).limit(20)
        )
        matches = result.scalars().all()

        for match in matches:
            if current_hackathon_id and str(match.hackathon_id) == current_hackathon_id:
                continue  # Same hackathon, handled by similarity.py

            score = max(score, 90)
            details["matches"].append(
                {
                    "type": "exact_github_url",
                    "devpost_url": match.devpost_url,
                    "hackathon_id": str(match.hackathon_id),
                    "title": match.title,
                }
            )
            evidence.append(f"Same GitHub URL ({github_url}) found in another hackathon: {match.devpost_url}")

        # 2. Commit hash overlap
        own_commit = getattr(context.scraped, "commit_hash", None)
        if own_commit:
            hash_result = await session.execute(
                select(CrawledProject)
                .where(
                    CrawledProject.commit_hash == own_commit,
                    CrawledProject.github_url != github_url.strip().lower(),
                )
                .limit(20)
            )
            for proj in hash_result.scalars().all():
                if current_hackathon_id and str(proj.hackathon_id) == current_hackathon_id:
                    continue
                score = max(score, 85)
                details["matches"].append(
                    {
                        "type": "same_commit_hash",
                        "commit_hash": own_commit[:8],
                        "devpost_url": proj.devpost_url,
                        "github_url": proj.github_url,
                        "hackathon_id": str(proj.hackathon_id),
                    }
                )
                evidence.append(f"Same HEAD commit ({own_commit[:8]}) in another hackathon: {proj.devpost_url}")

        # 3. Same repo name (different owner)
        repo_name = _parse_repo_name(github_url)
        if repo_name:
            name_result = await session.execute(
                select(CrawledProject)
                .where(
                    CrawledProject.github_url.isnot(None),
                    CrawledProject.github_url != github_url.strip().lower(),
                )
                .limit(200)
            )
            for proj in name_result.scalars().all():
                if not proj.github_url:
                    continue
                if current_hackathon_id and str(proj.hackathon_id) == current_hackathon_id:
                    continue
                other_name = _parse_repo_name(proj.github_url)
                if other_name and other_name == repo_name:
                    score = max(score, 40)
                    details["matches"].append(
                        {
                            "type": "same_repo_name",
                            "repo_name": repo_name,
                            "devpost_url": proj.devpost_url,
                            "github_url": proj.github_url,
                        }
                    )
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
