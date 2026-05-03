"""HackVerify check registry."""

from app.checks import (
    ai_detection,
    asset_integrity,
    code_similarity,
    commit_forensics,
    commit_quality,
    cross_hackathon,
    dead_deps,
    devpost_alignment_ai,
    repeat_offender,
    repo_age,
    submission_history,
    template_detection,
    timeline,
)
from app.checks.interface import CheckCategory, CheckContext, CheckFn, CheckResult, HackathonInfo, ScrapedData

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
