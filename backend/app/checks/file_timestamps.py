"""File timestamp integrity check — detect files created before hackathon start."""
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from app.checks.interface import CheckContext, CheckResult


async def check_timestamps(context: CheckContext) -> CheckResult:
    """Check if files were created/committed before the hackathon started."""
    repos = context.repo_paths or ([context.repo_path] if context.repo_path else [])
    if not repos:
        return CheckResult(
            check_name="file-timestamps", check_category="timeline",
            score=20, status="pass", details={"reason": "No repo available"},
        )

    if not context.hackathon:
        return CheckResult(
            check_name="file-timestamps", check_category="timeline",
            score=10, status="pass",
            details={"reason": "No hackathon dates to compare against"},
        )

    hack_start = context.hackathon.start_date
    all_early_files = []
    total_files = 0
    total_early = 0

    for repo in repos:
        try:
            result = subprocess.run(
                ["git", "-C", str(repo), "log", "--diff-filter=A", "--format=%aI %s",
                 "--name-only", "--since=" + _days_before(hack_start, 30)],
                capture_output=True, text=True, timeout=20,
            )
            if result.returncode != 0:
                continue

            # Parse: each commit has date line, then file list
            current_date = None
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if not line:
                    current_date = None
                    continue
                if line.startswith("20"):  # ISO date: 2026-04-15T10:00:00+00:00
                    current_date = line.split(" ")[0]
                elif current_date and current_date < hack_start[:10]:
                    total_early += 1
                    all_early_files.append({
                        "file": line,
                        "repo": str(repo.name) if repo.name else str(repo),
                        "date": current_date,
                    })
                    total_files += 1
                else:
                    total_files += 1

        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue

    pct_early = round(total_early / total_files * 100) if total_files > 0 else 0

    score = 0
    evidence = []
    if total_early > 0:
        if pct_early > 50:
            score += 60
            evidence.append(f"{pct_early}% of files ({total_early}/{total_files}) created before hackathon — likely pre-built")
        elif pct_early > 20:
            score += 35
            evidence.append(f"{pct_early}% of files ({total_early}/{total_files}) created before hackathon")
        else:
            score += 15
            evidence.append(f"{pct_early}% of files ({total_early}/{total_files}) created before hackathon — minor")

    # Also check: were ALL files created in one burst? (copy-paste)
    if total_files > 10 and total_early == 0:
        # Check if all files share the same commit (single commit = copy-pasted)
        try:
            for repo in repos:
                commit_count = subprocess.run(
                    ["git", "-C", str(repo), "rev-list", "--count", "HEAD"],
                    capture_output=True, text=True, timeout=10,
                )
                count = int(commit_count.stdout.strip()) if commit_count.returncode == 0 else 0
                if count == 1 and total_files > 20:
                    score += 25
                    evidence.append(f"All {total_files} files added in a single commit — possible copy-paste")
        except Exception:
            pass

    score = min(100, score)
    status = "pass" if score <= 30 else "warn" if score <= 60 else "fail"

    return CheckResult(
        check_name="file-timestamps", check_category="timeline",
        score=score, status=status,
        details={
            "total_files": total_files,
            "files_before_hackathon": total_early,
            "pct_early": pct_early,
            "early_files": all_early_files[:20],
            "hackathon_start": hack_start,
        },
        evidence=evidence,
    )


def _days_before(iso_date: str, days: int) -> str:
    """Return an ISO date N days before the given date."""
    try:
        dt = datetime.fromisoformat(iso_date[:19])
        return (dt.replace(tzinfo=None) - __import__('datetime').timedelta(days=days)).isoformat()
    except Exception:
        return "2020-01-01"
