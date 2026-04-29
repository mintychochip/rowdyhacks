"""Check if the GitHub repo was created before the hackathon started."""
import re
import httpx
from datetime import datetime, timezone
from app.checks.interface import CheckContext, CheckResult
from app.config import settings


async def check_repo_age(context: CheckContext) -> CheckResult:
    """Check repo age, stars, and fork status via GitHub API."""
    gh_url = context.scraped.github_url
    if not gh_url:
        return CheckResult(
            check_name="repo-age", check_category="timeline",
            score=0, status="pass", details={"reason": "No GitHub URL available"},
        )

    m = re.match(r'https?://(?:www\.)?github\.com/([\w.-]+)/([\w.-]+)', gh_url)
    if not m:
        return CheckResult(
            check_name="repo-age", check_category="timeline",
            score=0, status="pass", details={"reason": f"Could not parse GitHub URL"},
        )

    owner, repo_name = m.group(1), m.group(2)

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"https://api.github.com/repos/{owner}/{repo_name}",
                headers={"User-Agent": "HackVerify/1.0", "Accept": "application/vnd.github.v3+json"},
            )
            if resp.status_code != 200:
                return CheckResult(
                    check_name="repo-age", check_category="timeline",
                    score=10, status="pass", details={"reason": f"GitHub API returned {resp.status_code}"},
                )

            data = resp.json()
            created_at_str = data.get("created_at", "")
            pushed_at_str = data.get("pushed_at", "")
            stars = data.get("stargazers_count", 0)
            forks = data.get("forks_count", 0)
            is_fork = data.get("fork", False)
            default_branch = data.get("default_branch", "main")
            open_issues = data.get("open_issues_count", 0)

            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            age_days = (now.replace(tzinfo=None) - created_at.replace(tzinfo=None)).days

            score = 0
            evidence = []
            details = {
                "repo_created": created_at_str,
                "age_days": age_days,
                "stars": stars,
                "forks": forks,
                "is_fork": is_fork,
                "default_branch": default_branch,
                "open_issues": open_issues,
            }

            # Age-based flags (even without hackathon context)
            if age_days > 365:
                score += 40
                evidence.append(f"Repo is {age_days} days old — not built recently")
            elif age_days > 180:
                score += 25
                evidence.append(f"Repo is {age_days} days old ({age_days // 30} months)")

            # Compare against hackathon dates if available
            if context.hackathon:
                hack_start = datetime.fromisoformat(context.hackathon.start_date[:19])
                details["hackathon_start"] = context.hackathon.start_date
                if created_at.replace(tzinfo=None) < hack_start.replace(tzinfo=None):
                    days_before = (hack_start.replace(tzinfo=None) - created_at.replace(tzinfo=None)).days
                    if days_before > 30:
                        score += 50
                        evidence.append(f"Repo created {days_before} days before hackathon — likely pre-existing")
                    elif days_before > 7:
                        score += 30
                        evidence.append(f"Repo created {days_before} days before hackathon")

                if pushed_at_str:
                    pushed_dt = datetime.fromisoformat(pushed_at_str.replace("Z", "+00:00"))
                    if pushed_dt.replace(tzinfo=None) < hack_start.replace(tzinfo=None):
                        score += 20
                        evidence.append(f"Last push was before hackathon ({pushed_at_str[:10]})")

            # Star-based flags
            if stars > 50:
                score += 40
                evidence.append(f"Repo has {stars} stars — unlikely hackathon project")
            elif stars > 10:
                score += 15
                evidence.append(f"Repo has {stars} stars — unusual for a hackathon")

            # Fork detection
            if is_fork:
                score += 30
                evidence.append("Repo is a GitHub fork — not original work")
                parent = data.get("parent", {})
                if parent:
                    details["forked_from"] = parent.get("full_name", "")

            score = min(100, score)
            status = "pass" if score <= 30 else "warn" if score <= 60 else "fail"

            return CheckResult(
                check_name="repo-age", check_category="timeline",
                score=score, status=status, details=details, evidence=evidence,
            )

    except Exception as e:
        return CheckResult(
            check_name="repo-age", check_category="timeline",
            score=10, status="pass",
            details={"reason": f"GitHub API error: {str(e)[:200]}"},
        )
