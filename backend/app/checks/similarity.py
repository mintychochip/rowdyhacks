"""Cross-team similarity check (batch operation)."""

import asyncio
import logging
import re
import uuid

from sqlalchemy import select

from app.checks.interface import CheckResult
from app.database import async_session
from app.models import Submission, SubmissionStatus

logger = logging.getLogger(__name__)


def _parse_repo_name(github_url: str | None) -> str | None:
    """Extract the 'owner/repo' portion from a GitHub URL.

    Handles formats:
      - https://github.com/owner/repo
      - https://github.com/owner/repo.git
      - git@github.com:owner/repo.git
    Returns None if the URL is invalid or not a GitHub URL.
    """
    if not github_url:
        return None
    github_url = github_url.strip()
    # Try HTTPS format: https://github.com/owner/repo[.git]
    m = re.match(r"https?://github\.com/([^/]+/[^/]+?)(?:\.git)?/?$", github_url)
    if m:
        return m.group(1).lower()
    # Try SSH format: git@github.com:owner/repo.git
    m = re.match(r"git@github\.com:([^/]+/[^/]+?)(?:\.git)?$", github_url)
    if m:
        return m.group(1).lower()
    return None


async def _get_head_commit(github_url: str) -> str | None:
    """Fetch the HEAD commit hash from a GitHub repo via git ls-remote.

    Returns the full SHA-1 hash as a string, or None if the lookup fails
    (e.g. invalid URL, network error, empty repo).
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            "git",
            "ls-remote",
            github_url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode != 0 or not stdout:
            return None
        # First line: "<sha>\tHEAD"
        first_line = stdout.decode().strip().split("\n")[0]
        sha = first_line.split("\t")[0] if first_line else None
        return sha if sha and len(sha) == 40 else None
    except Exception:
        logger.exception("Failed to get HEAD commit for %s", github_url)
        return None


async def run_similarity(hackathon_id: uuid.UUID) -> list[CheckResult]:
    """Run cross-team similarity check for all submissions in a hackathon."""
    results = []
    async with async_session() as db:
        result = await db.execute(
            select(Submission).where(
                Submission.hackathon_id == hackathon_id,
                Submission.status == SubmissionStatus.completed,
            )
        )
        submissions = result.scalars().all()

        # Check for duplicate GitHub URLs
        seen_urls: dict[str, uuid.UUID] = {}
        for sub in submissions:
            if sub.github_url:
                url = sub.github_url.strip().lower()
                if url in seen_urls:
                    results.append(
                        CheckResult(
                            check_name="duplicate-github-url",
                            check_category="cross_team_similarity",
                            score=80,
                            status="fail",
                            details={"duplicate_url": url, "other_submission": str(seen_urls[url])},
                        )
                    )
                else:
                    seen_urls[url] = sub.id

    return results
