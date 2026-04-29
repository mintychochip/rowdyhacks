"""Check function contract for HackVerify analysis checks."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Awaitable, Callable
from uuid import UUID


class CheckCategory(str, Enum):
    TIMELINE = "timeline"
    DEVPOST_ALIGNMENT = "devpost_alignment"
    SUBMISSION_HISTORY = "submission_history"
    ASSET_INTEGRITY = "asset_integrity"
    CROSS_TEAM_SIMILARITY = "cross_team_similarity"
    AI_DETECTION = "ai_detection"
    CROSS_HACKATHON = "cross_hackathon"
    REPEAT_OFFENDER = "repeat_offender"


@dataclass
class ScrapedData:
    """Parsed Devpost submission metadata."""
    title: str | None = None
    description: str | None = None
    claimed_tech: list[str] = field(default_factory=list)
    team_members: list[dict] = field(default_factory=list)
    commit_hash: str | None = None  # HEAD hash from git ls-remote
    github_url: str | None = None
    video_url: str | None = None
    slides_url: str | None = None


@dataclass
class HackathonInfo:
    """Hackathon context for timeline-aware checks."""
    id: UUID
    name: str
    start_date: str  # ISO 8601
    end_date: str    # ISO 8601


@dataclass
class CheckContext:
    """Input to a single check function."""
    repo_path: Path | None
    scraped: ScrapedData
    submission_id: UUID
    hackathon: HackathonInfo | None = None


@dataclass
class CheckResult:
    """Output from a single check function."""
    check_name: str
    check_category: str
    score: int  # 0-100
    status: str  # "pass" | "warn" | "fail" | "error"
    details: dict = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.status not in ("pass", "warn", "fail", "error"):
            raise ValueError(f"Invalid status: {self.status}")
        if not 0 <= self.score <= 100:
            raise ValueError(f"Score {self.score} out of range 0-100")


CheckFn = Callable[[CheckContext], Awaitable[CheckResult]]
