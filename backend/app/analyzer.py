"""Orchestrate the analysis pipeline: scrape -> clone -> checks -> score."""
import asyncio
import os
import shutil
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.checks import CHECKS, WEIGHTS
from app.checks.interface import CheckContext, ScrapedData, HackathonInfo
from app.database import async_session
from app.models import Submission, SubmissionStatus, CheckResultModel, Verdict, CheckStatus
from app.scraper import scrape_devpost, ScraperError, is_github_url


async def analyze_submission(submission_id: uuid.UUID) -> None:
    """Run the full analysis pipeline on a submission."""
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
                tmp_dir = tempfile.mkdtemp(prefix="hackverify_")
                try:
                    proc = await asyncio.create_subprocess_exec(
                        "git", "clone", "--depth", "1", "--single-branch", github_url, tmp_dir,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        env={**os.environ, "GIT_CLONE_PROTECTION_ACTIVE": "false"},
                    )
                    await asyncio.wait_for(proc.communicate(), timeout=120)
                    if proc.returncode == 0:
                        repo_path = Path(tmp_dir)
                except (asyncio.TimeoutError, FileNotFoundError, OSError):
                    pass
            timings["clone"] = round(time.monotonic() - t2, 2)

            # 3. Build context
            hackathon_info = None
            if sub.hackathon_id:
                from app.models import Hackathon
                hk_result = await db.execute(select(Hackathon).where(Hackathon.id == sub.hackathon_id))
                hk = hk_result.scalar_one_or_none()
                if hk:
                    hackathon_info = HackathonInfo(
                        id=hk.id, name=hk.name,
                        start_date=hk.start_date.isoformat(),
                        end_date=hk.end_date.isoformat()
                    )

            ctx = CheckContext(
                repo_path=repo_path,
                scraped=scraped,
                submission_id=submission_id,
                hackathon=hackathon_info,
            )

            # 4. Run checks and track progress
            sub.stage = "checking"
            # Init progress tracking
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
                await db.commit()  # flush progress so frontend sees it immediately
            sub.check_progress["current"] = None
            await db.commit()
            timings["checks_total"] = round(time.monotonic() - t3, 2)
            timings["checks"] = check_timings

            # 5. Clear old results, store new ones, and compute score
            sub.stage = "scoring"
            from sqlalchemy import delete as sqla_delete
            await db.execute(sqla_delete(CheckResultModel).where(CheckResultModel.submission_id == submission_id))
            await db.commit()
            # Store results and compute weighted score by category
            category_scores: dict[str, list[int]] = {}
            for check_result in results:
                if isinstance(check_result, Exception):
                    import traceback
                    print(f"[CHECK ERROR] {type(check_result).__name__}: {check_result}")
                    traceback.print_exc()
                    continue

                # Store this check result in the DB
                db.add(CheckResultModel(
                    submission_id=submission_id,
                    check_category=check_result.check_category,
                    check_name=check_result.check_name,
                    score=check_result.score,
                    status=CheckStatus(check_result.status),
                    details=check_result.details,
                    evidence=check_result.evidence,
                ))

                # Group for weighted scoring
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

            # 6. Compute aggregate
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
            sub.completed_at = datetime.now(timezone.utc)
            timings["total"] = round(time.monotonic() - t0, 2)
            print(f"\n[PROFILE] Submission {submission_id}: {timings}\n")
            await db.commit()

        finally:
            # Cleanup temp repo
            if repo_path:
                try:
                    shutil.rmtree(repo_path)
                except Exception:
                    pass
