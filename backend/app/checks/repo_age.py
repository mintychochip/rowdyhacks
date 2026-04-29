"""Check if the GitHub repo was created before the hackathon started."""
import re
import httpx
from datetime import datetime, timezone
from app.checks.interface import CheckContext, CheckResult
from app.config import settings


async def check_repo_age(context: CheckContext) -> CheckResult:
    """Check via GitHub API whether the repo was created before the hackathon."""
    if not context.hackathon:
        return CheckResult(
            check_name="repo-age", check_category="timeline",
            score=0, status="pass", details={"reason": "No hackathon dates to compare"},
        )

    gh_url = context.scraped.github_url
    if not gh_url:
        return CheckResult(
            check_name="repo-age", check_category="timeline",
            score=0, status="pass", details={"reason": "No GitHub URL available"},
        )

    # Extract owner/repo from URL
    m = re.match(r'https?://(?:www\.)?github\.com/([\w.-]+)/([\w.-]+)', gh_url)
    if not m:
        return CheckResult(
            check_name="repo-age", check_category="timeline",
            score=0, status="pass", details={"reason": f"Could not parse GitHub URL: {gh_url}"},
        )

    owner, repo_name = m.group(1), m.group(2)
    hack_start = datetime.fromisoformat(context.hackathon.start_date[:19])

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"https://api.github.com/repos/{owner}/{repo_name}",
                headers={
                    "User-Agent": "HackVerify/1.0",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            if resp.status_code != 200:
                return CheckResult(
                    check_name="repo-age", check_category="timeline",
                    score=10, status="pass",
                    details={"reason": f"GitHub API returned {resp.status_code}"},
                )

            data = resp.json()
            created_at_str = data.get("created_at", "")
            pushed_at = data.get("pushed_at", "")
            stars = data.get("stargazers_count", 0)
            forks = data.get("forks_count", 0)
            is_fork = data.get("fork", False)
            default_branch = data.get("default_branch", "main")

            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))

            score = 0
            evidence = []
            details = {
                "repo_created": created_at_str,
                "hackathon_start": context.hackathon.start_date,
                "stars": stars,
                "forks": forks,
                "is_fork": is_fork,
                "default_branch": default_branch,
            }

            # Repo created before hackathon
            if created_at < hack_start:
                days_before = (hack_start - created_at).days
                if days_before > 30:
                    score += 50
                    evidence.append(f"Repo created {days_before} days before hackathon — likely pre-existing project")
                elif days_before > 7:
                    score += 30
                    evidence.append(f"Repo created {days_before} days before hackathon")
                else:
                    score += 10
                    evidence.append(f"Repo created {days_before} days before hackathon — could be early setup")

            # Very popular repo = not built in a weekend
            if stars > 50:
                score += 40
                evidence.append(f"Repo has {stars} stars — unlikely to be built during a hackathon")
            elif stars > 10:
                score += 15
                evidence.append(f"Repo has {stars} stars")

            if is_fork:
                score += 30
                evidence.append("Repo is a GitHub fork")
                parent = data.get("parent", {})
                if parent:
                    details["forked_from"] = parent.get("full_name", "")

            # Last push was before hackathon
            if pushed_at:
                pushed_dt = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
                if pushed_dt < hack_start:
                    score += 20
                    evidence.append(f"Last push was before hackathon ({pushed_at[:10]})")

            score = min(100, score)
            status = "pass" if score <= 30 else "warn" if score <= 60 else "fail"

            return CheckResult(
                check_name="repo-age", check_category="timeline",
                score=score, status=status,
                details=details, evidence=evidence,
            )

    except Exception as e:
        return CheckResult(
            check_name="repo-age", check_category="timeline",
            score=10, status="pass",
            details={"reason": f"GitHub API error: {str(e)[:200]}"},
        )
