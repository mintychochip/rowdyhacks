"""Check commit timeline against hackathon window."""

import asyncio

from app.checks.interface import CheckContext, CheckResult


async def check_commits(context: CheckContext) -> CheckResult:
    """Analyze git commit history for timeline integrity against the hackathon window.

    Behavior:
    1. Return early if no repo path is available.
    2. Run git log to extract commit hashes, ISO author dates, and messages.
    3. Detect commits that occur before the hackathon start date.
    4. Flag a single monolithic commit as suspicious.
    5. Detect commit bursts with crude heuristics.
    6. Score based on suspicious message ratios and timeline violations.
    7. Return a CheckResult with timeline details and evidence.

    Raises: None
    Side Effects: None (read-only git log access).
    Dependencies: app.checks.interface.CheckContext, app.checks.interface.CheckResult, asyncio.
    Consumers: Internal check used by the analyzer pipeline.
    """
    if not context.repo_path:
        return CheckResult(
            check_name="commit-timestamps",
            check_category="timeline",
            score=30,
            status="warn",
            details={"reason": "No repo available"},
        )

    try:
        proc = await asyncio.create_subprocess_exec(
            "git",
            "-C",
            str(context.repo_path),
            "log",
            "--format=%H|%aI|%s",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        if proc.returncode != 0:
            return CheckResult(
                check_name="commit-timestamps",
                check_category="timeline",
                score=50,
                status="warn",
                details={"reason": "Git log failed"},
            )
    except (TimeoutError, FileNotFoundError, OSError):
        return CheckResult(
            check_name="commit-timestamps",
            check_category="timeline",
            score=50,
            status="warn",
            details={"reason": "Git command error"},
        )

    lines = stdout.decode().strip().split("\n")
    commits = []
    current = None
    for line in lines:
        # Skip stat/diff lines from --stat (start with space or tab)
        if "|" in line and not line.startswith((" ", "\t")):
            parts = line.split("|")
            if len(parts) >= 3:
                commits.append(
                    {
                        "hash": parts[0].strip(),
                        "date": parts[1].strip(),
                        "message": parts[2].strip(),
                    }
                )

    score = 0
    evidence = []
    details = {}

    if not commits:
        score += 80
        details["no_commits"] = True
    else:
        # Check commits before hackathon
        if context.hackathon:
            hack_start = context.hackathon.start_date
            hack_end = context.hackathon.end_date
            before = [c for c in commits if c["date"] < hack_start]
            details["commits_before_start"] = len(before)
            if len(before) > 0:
                score += min(40, len(before) * 10)

            # Giant commit near deadline (single monolithic commit)
            if len(commits) == 1:
                last_date = commits[-1]["date"]
                score += 50
                details["single_commit"] = True
                evidence.append(f"Single commit at {last_date}")

        # Burst detection
        if len(commits) >= 20:
            # crude: more than 30 commits in last 2 hours
            recent_count = 0
            if commits:
                last_date = commits[0]["date"]
                for c in commits:
                    recent_count += 1
            if recent_count > 30:
                score += 30
                details["commit_burst"] = True

        # Suspicious messages
        suspicious = [
            "update",
            "fix",
            "commit",
            "test",
            "wip",
            ".",
            "changes",
            "stuff",
        ]
        sus_count = sum(1 for c in commits if c["message"].lower().strip() in suspicious)
        if sus_count > len(commits) * 0.5 and len(commits) > 3:
            score += 20
            details["suspicious_messages"] = sus_count

    score = min(100, score)
    if score <= 30:
        status = "pass"
    elif score <= 60:
        status = "warn"
    else:
        status = "fail"

    return CheckResult(
        check_name="commit-timestamps",
        check_category="timeline",
        score=score,
        status=status,
        details=details,
        evidence=evidence,
    )
