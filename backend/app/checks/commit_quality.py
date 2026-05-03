"""Check commit message quality for suspicious patterns."""

import asyncio
import re

from app.checks.interface import CheckContext, CheckResult

# Messages that scream "no effort" or "AI wrote this"
SUSPICIOUS_MESSAGES = {
    "update",
    "fix",
    "commit",
    "test",
    "wip",
    ".",
    "changes",
    "stuff",
    "done",
    "work",
    "push",
    "save",
    "final",
    "initial commit",
    "first commit",
    "added files",
    "updated code",
    "fixed bug",
    "minor fix",
    "clean up",
    "cleanup",
    "refactor",
    "updated",
    "fixed",
    "added",
    "patch",
    "tweak",
    "tmp",
    "temp",
    "misc",
}


async def check_commit_quality(context: CheckContext) -> CheckResult:
    """Analyze commit messages for quality and suspicious patterns."""
    if not context.repo_path:
        return CheckResult(
            check_name="commit-quality",
            check_category="timeline",
            score=20,
            status="pass",
            details={"reason": "No repo available"},
        )

    try:
        proc = await asyncio.create_subprocess_exec(
            "git",
            "-C",
            str(context.repo_path),
            "log",
            "--format=%s",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
        if proc.returncode != 0:
            return CheckResult(
                check_name="commit-quality",
                check_category="timeline",
                score=10,
                status="pass",
                details={"reason": "Git log failed"},
            )
    except (TimeoutError, FileNotFoundError, OSError):
        return CheckResult(
            check_name="commit-quality",
            check_category="timeline",
            score=10,
            status="pass",
            details={"reason": "Git command error"},
        )

    messages = [m.strip().lower() for m in stdout.decode().strip().split("\n") if m.strip()]
    total = len(messages)
    if total == 0:
        return CheckResult(
            check_name="commit-quality",
            check_category="timeline",
            score=30,
            status="warn",
            details={"reason": "No commits found"},
        )

    sus_count = sum(1 for m in messages if m in SUSPICIOUS_MESSAGES)
    empty_count = sum(1 for m in messages if not m or len(m) < 3)

    # Average message length
    avg_len = sum(len(m) for m in messages) / total

    # Messages that are pure numbers or single words
    single_word = sum(1 for m in messages if " " not in m)

    pct_bad = round(sus_count / total * 100) if total > 0 else 0
    pct_single = round(single_word / total * 100) if total > 0 else 0

    score = 0
    evidence = []

    if pct_bad > 80 and total >= 3:
        score += 35
        evidence.append(
            f"{pct_bad}% of {total} commits are 'update', 'fix', or similar — likely AI-generated or copy-pasted"
        )
    elif pct_bad > 50 and total >= 3:
        score += 20
        evidence.append(f"{pct_bad}% of {total} commits are generic placeholder messages")
    elif pct_bad > 30 and total >= 5:
        score += 10
        evidence.append(f"{pct_bad}% of commits have low-quality messages")

    if avg_len < 10 and total >= 3:
        score += 10
        evidence.append(f"Average commit message is {avg_len:.0f} characters — very short")

    if pct_single > 80 and total >= 5:
        score += 15
        evidence.append(f"{pct_single}% of commits are single words — no meaningful descriptions")

    # Not a single conventional commit message (feat:, fix:, chore:, etc.)
    conventional = sum(
        1 for m in messages if re.search(r"^(feat|fix|chore|docs|style|refactor|test|perf|ci|build|revert)[(:]", m)
    )
    if conventional == 0 and total >= 5:
        score += 10
        evidence.append("No conventional commits detected")

    score = min(100, score)
    status = "pass" if score <= 30 else "warn" if score <= 60 else "fail"

    return CheckResult(
        check_name="commit-quality",
        check_category="timeline",
        score=score,
        status=status,
        details={
            "total_commits": total,
            "suspicious_count": sus_count,
            "pct_suspicious": pct_bad,
            "single_word_count": single_word,
            "avg_message_len": round(avg_len, 1),
            "conventional_commits": conventional,
            "worst_messages": [m for m in messages if m in SUSPICIOUS_MESSAGES][:10],
        },
        evidence=evidence,
    )
