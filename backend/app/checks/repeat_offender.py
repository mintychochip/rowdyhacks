"""Check if team members appear in previously flagged submissions."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.checks.interface import CheckContext, CheckResult
from app.database import async_session
from app.models import CrawledProject, Submission, Verdict


@asynccontextmanager
async def _resolve_session(
    db: AsyncSession | None,
) -> AsyncIterator[AsyncSession]:
    """Yield the provided session, or create one from the default pool."""
    if db is not None:
        yield db
    else:
        async with async_session() as session:
            yield session


async def check_repeat_offender(
    context: CheckContext,
    db: AsyncSession | None = None,
) -> CheckResult:
    """Check if any team member has been flagged in prior hackathons.

    Parameters
    ----------
    context : CheckContext
        The analysis context containing scraped submission data.
    db : AsyncSession | None
        Optional database session for testing. When None (the default),
        a session is created from the application's connection pool.
    """
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
            if "github.com/" in gh:
                username = gh.split("github.com/")[-1].strip("/")
                if username and "/" not in username:
                    github_usernames.append(username.lower())
            elif not gh.startswith("github_uid:"):
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

    async with _resolve_session(db) as session:
        # Find flagged submissions
        flagged_result = await session.execute(
            select(Submission)
            .where(
                or_(
                    Submission.verdict == Verdict.flagged,
                    Submission.verdict == Verdict.review,
                )
            )
            .limit(500)
        )
        flagged_subs = flagged_result.scalars().all()

        flagged_github_urls: set[str] = {sub.github_url.strip().lower() for sub in flagged_subs if sub.github_url}

        flagged_count = 0
        for username in github_usernames:
            all_proj_result = await session.execute(
                select(CrawledProject)
                .where(
                    CrawledProject.github_url.isnot(None),
                )
                .limit(1000)
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
                        if proj.github_url and proj.github_url.strip().lower() in flagged_github_urls:
                            flagged_count += 1
                            details["prior_flags"].append(
                                {
                                    "github_username": username,
                                    "devpost_url": proj.devpost_url,
                                    "title": proj.title,
                                    "github_url": proj.github_url,
                                }
                            )
                            evidence.append(f"Team member '{username}' appears in flagged project: {proj.devpost_url}")
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
                details["suspicious_patterns"].append(
                    {
                        "devpost_profile": dp_profile,
                        "github_accounts": list(gh_set),
                    }
                )
                evidence.append(f"Devpost profile {dp_profile} linked to multiple GitHub accounts: {gh_set}")

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
