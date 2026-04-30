"""HackVerify check registry."""
from app.checks.interface import CheckFn, CheckContext, CheckResult, CheckCategory, ScrapedData, HackathonInfo
from app.checks import (
    timeline, devpost_alignment_ai, submission_history, asset_integrity, 
    ai_detection, cross_hackathon, repeat_offender, dead_deps, 
    commit_quality, repo_age, code_similarity, template_detection,
    commit_forensics
)

# All checks except similarity (batch)
CHECKS: list[CheckFn] = [
    timeline.check_commits,
    commit_quality.check_commit_quality,
    repo_age.check_repo_age,
    commit_forensics.check_commit_forensics,
    devpost_alignment_ai.check_alignment_ai,
    dead_deps.check_dead_deps,
    template_detection.check_template,
    submission_history.check_history,
    asset_integrity.check_assets,
    ai_detection.check_ai,
    cross_hackathon.check_cross_hackathon_duplicate,
    repeat_offender.check_repeat_offender,
    code_similarity.check_code_similarity,
]

WEIGHTS: dict[str, float] = {
    "timeline": 0.25,
    "devpost_alignment": 0.30,
    "submission_history": 0.20,
    "asset_integrity": 0.15,
    "cross_team_similarity": 0.05,
    "ai_detection": 0.05,
    "cross_hackathon": 0.10,
    "repeat_offender": 0.05,
}
