"""Submission analysis and scoring service.

Orchestrates the submission integrity pipeline (scrape, clone, checks, score)
and provides CRUD helpers for submission lifecycle operations.
"""

import asyncio
import os
import shutil
import tempfile
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import delete as sqla_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.checks import CHECKS, WEIGHTS
from app.checks.interface import CheckContext, HackathonInfo, ScrapedData
from app.database import async_session
from app.models import CheckResultModel, CheckStatus, Submission, SubmissionStatus, Verdict
from app.scraper import ScraperError, is_github_url, scrape_devpost


class SubmissionService:
    """Service for managing submissions and running the integrity analysis pipeline."""

    # --- Analysis pipeline ---

    async def analyze_submission(self, submission_id: uuid.UUID) -> None:
        """Run the full submission integrity analysis pipeline.

        Behavior:
        1. Load the submission from the database and mark it as ``analyzing``.
        2. Scrape the Devpost page to extract metadata.
        3. If scraping fails, mark the submission as ``failed`` and abort.
        4. Clone the linked GitHub repository into a temporary directory.
        5. Resolve hackathon context from scraped data or the submission's linked hackathon.
        6. Build a CheckContext with the repo path, scraped data, and hackathon info.
        7. Run every registered check sequentially, updating progress after each one.
        8. Clear old CheckResultModel rows and persist new results.
        9. Compute a weighted risk score by category and assign a verdict.
        10. Mark the submission as ``completed``, record timings, and commit.
        11. In the finally block, clean up the temporary cloned repository.

        Side Effects: Updates the Submission row; inserts CheckResultModel rows;
        clones a GitHub repo to a temp directory; deletes the temp directory.
        """
        t0 = time.monotonic()
        async with async_session() as db:
            result = await db.execute(select(Submission).where(Submission.id == submission_id))
            sub = result.scalar_one_or_none()
            if not sub:
                return

            sub.status = SubmissionStatus.analyzing
            sub.stage = "scraping"
            await db.commit()

            repo_path = None
            timings = {}
            try:
                # 1. Scrape Devpost
                t1 = time.monotonic()
                scraped = ScrapedData()
                try:
                    scraped = await scrape_devpost(sub.devpost_url)
                    sub.project_title = scraped.title
                    sub.project_description = scraped.description
                    sub.claimed_tech = scraped.claimed_tech
                    sub.team_members = scraped.team_members
                    if scraped.github_url:
                        sub.github_url = scraped.github_url
                    await db.commit()
                except ScraperError:
                    sub.status = SubmissionStatus.failed
                    sub.stage = None
                    await db.commit()
                    return
                timings["scrape"] = round(time.monotonic() - t1, 2)

                # 2. Clone repo
                sub.stage = "cloning"
                await db.commit()
                t2 = time.monotonic()
                github_url = sub.github_url or scraped.github_url
                if github_url and is_github_url(github_url):
                    tmp_dir = tempfile.mkdtemp(prefix="hackathon_")
                    try:
                        proc = await asyncio.create_subprocess_exec(
                            "git",
                            "clone",
                            "--depth",
                            "1",
                            "--single-branch",
                            github_url,
                            tmp_dir,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                            env={**os.environ, "GIT_CLONE_PROTECTION_ACTIVE": "false"},
                        )
                        await asyncio.wait_for(proc.communicate(), timeout=120)
                        if proc.returncode == 0:
                            repo_path = Path(tmp_dir)
                    except (TimeoutError, FileNotFoundError, OSError):
                        pass
                timings["clone"] = round(time.monotonic() - t2, 2)

                # 3. Build context
                hackathon_info = None
                hk_name = scraped.hackathon_name
                hk_url = scraped.hackathon_url

                if hk_url or hk_name:
                    from app.models import CrawledHackathon

                    chk = None
                    if hk_url:
                        r = await db.execute(select(CrawledHackathon).where(CrawledHackathon.devpost_url == hk_url))
                        chk = r.scalar_one_or_none()
                    if not chk and hk_name:
                        r = await db.execute(
                            select(CrawledHackathon).where(CrawledHackathon.name.ilike(f"%{hk_name}%"))
                        )
                        chk = r.scalar_one_or_none()
                    if chk and chk.start_date:
                        hackathon_info = HackathonInfo(
                            id=chk.id,
                            name=chk.name,
                            start_date=chk.start_date.isoformat(),
                            end_date=(chk.end_date or chk.start_date).isoformat(),
                        )

                if not hackathon_info and sub.hackathon_id:
                    from app.models import Hackathon

                    hk_result = await db.execute(select(Hackathon).where(Hackathon.id == sub.hackathon_id))
                    hk = hk_result.scalar_one_or_none()
                    if hk:
                        hackathon_info = HackathonInfo(
                            id=hk.id,
                            name=hk.name,
                            start_date=hk.start_date.isoformat(),
                            end_date=hk.end_date.isoformat(),
                        )

                ctx = CheckContext(
                    repo_path=repo_path,
                    scraped=scraped,
                    submission_id=submission_id,
                    hackathon=hackathon_info,
                )

                # 4. Run checks and track progress
                sub.stage = "checking"
                check_names = [c.__module__.split(".")[-1] for c in CHECKS]
                sub.check_progress = {"completed": [], "pending": check_names[:], "current": None}
                await db.commit()
                t3 = time.monotonic()
                check_timings = {}
                results = []
                for i, check_fn in enumerate(CHECKS):
                    name = check_names[i]
                    sub.check_progress["current"] = name
                    await db.commit()
                    ct0 = time.monotonic()
                    try:
                        r = await check_fn(ctx)
                        results.append(r)
                    except Exception as e:
                        results.append(e)
                    check_timings[name] = round(time.monotonic() - ct0, 2)
                    sub.check_progress["completed"].append(name)
                    sub.check_progress["pending"].remove(name)
                    await db.commit()
                sub.check_progress["current"] = None
                await db.commit()
                timings["checks_total"] = round(time.monotonic() - t3, 2)
                timings["checks"] = check_timings

                # 5. Clear old results, store new ones, and compute score
                sub.stage = "scoring"
                await db.execute(sqla_delete(CheckResultModel).where(CheckResultModel.submission_id == submission_id))
                await db.commit()

                category_scores: dict[str, list[int]] = {}
                for check_result in results:
                    if isinstance(check_result, Exception):
                        import traceback

                        print(f"[CHECK ERROR] {type(check_result).__name__}: {check_result}")
                        traceback.print_exc()
                        continue

                    db.add(
                        CheckResultModel(
                            submission_id=submission_id,
                            check_category=check_result.check_category,
                            check_name=check_result.check_name,
                            score=check_result.score,
                            status=CheckStatus(check_result.status),
                            details=check_result.details,
                            evidence=check_result.evidence,
                        )
                    )

                    cat = check_result.check_category
                    if cat not in category_scores:
                        category_scores[cat] = []
                    category_scores[cat].append(check_result.score)

                total_weight = 0.0
                weighted_sum = 0.0
                for cat, scores in category_scores.items():
                    w = WEIGHTS.get(cat, 0.05)
                    avg = sum(scores) / len(scores)
                    total_weight += w
                    weighted_sum += avg * w

                if total_weight > 0:
                    sub.risk_score = int(weighted_sum / total_weight)
                else:
                    sub.risk_score = 50

                if sub.risk_score <= 30:
                    sub.verdict = Verdict.clean
                elif sub.risk_score <= 60:
                    sub.verdict = Verdict.review
                else:
                    sub.verdict = Verdict.flagged

                sub.status = SubmissionStatus.completed
                sub.stage = None
                sub.completed_at = datetime.now(UTC)
                timings["total"] = round(time.monotonic() - t0, 2)
                print(f"\n[PROFILE] Submission {submission_id}: {timings}\n")
                await db.commit()

            finally:
                if repo_path:
                    try:
                        shutil.rmtree(repo_path)
                    except Exception:
                        pass

    # --- Lifecycle helpers ---

    async def get_submission(self, db: AsyncSession, submission_id: uuid.UUID) -> Submission | None:
        """Load a submission by ID with check results eagerly loaded."""
        from sqlalchemy.orm import selectinload

        result = await db.execute(
            select(Submission).where(Submission.id == submission_id).options(selectinload(Submission.check_results))
        )
        return result.scalar_one_or_none()

    async def reset_submission(self, db: AsyncSession, submission_id: uuid.UUID) -> Submission | None:
        """Reset a submission for re-analysis.

        Behavior:
        1. Load the submission by ID.
        2. Delete all existing CheckResult rows for the submission.
        3. Reset submission status to pending and clear scoring fields.
        4. Commit and return the submission.

        Side Effects: Deletes CheckResult rows; mutates Submission fields.
        """
        result = await db.execute(select(Submission).where(Submission.id == submission_id))
        sub = result.scalar_one_or_none()
        if not sub:
            return None

        await db.execute(sqla_delete(CheckResultModel).where(CheckResultModel.submission_id == submission_id))

        sub.status = SubmissionStatus.pending
        sub.risk_score = None
        sub.verdict = None
        sub.completed_at = None
        sub.stage = None
        sub.check_progress = None
        await db.commit()
        return sub

    async def create_submission(
        self,
        db: AsyncSession,
        url: str,
        hackathon_id: uuid.UUID | None = None,
    ) -> Submission:
        """Create a pending submission with an anonymous access token.

        Side Effects: Inserts Submission row.
        """
        from app.auth import create_anonymous_token

        access_token = create_anonymous_token()
        sub = Submission(
            devpost_url=url,
            status=SubmissionStatus.pending,
            access_token=access_token,
            hackathon_id=hackathon_id,
        )
        db.add(sub)
        await db.commit()
        await db.refresh(sub)
        return sub

    async def get_submission_report(self, db: AsyncSession, submission_id: uuid.UUID) -> dict | None:
        """Build a full report dict for a submission.

        Returns None if the submission does not exist.
        """
        from app.checks import WEIGHTS
        from sqlalchemy.orm import selectinload

        result = await db.execute(
            select(Submission).where(Submission.id == submission_id).options(selectinload(Submission.check_results))
        )
        sub = result.scalar_one_or_none()
        if not sub:
            return None

        return {
            "submission": {
                "id": str(sub.id),
                "devpost_url": sub.devpost_url,
                "github_url": sub.github_url,
                "project_title": sub.project_title,
                "project_description": sub.project_description,
                "claimed_tech": sub.claimed_tech,
                "team_members": sub.team_members,
                "status": sub.status.value,
                "risk_score": sub.risk_score,
                "verdict": sub.verdict.value if sub.verdict else None,
            },
            "check_results": [
                {
                    "check_category": cr.check_category,
                    "check_name": cr.check_name,
                    "score": cr.score,
                    "status": cr.status,
                    "details": cr.details,
                    "evidence": cr.evidence,
                }
                for cr in (sub.check_results or [])
            ],
            "weights": WEIGHTS,
        }
