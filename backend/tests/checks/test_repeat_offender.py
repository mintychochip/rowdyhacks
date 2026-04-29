import uuid
import pytest
from app.checks.interface import CheckContext, ScrapedData, HackathonInfo
from app.checks.repeat_offender import check_repeat_offender


@pytest.mark.asyncio
async def test_no_team_members_returns_pass():
    """Check returns pass when there are no team members."""
    ctx = CheckContext(
        repo_path=None,
        scraped=ScrapedData(team_members=[]),
        submission_id=uuid.uuid4(),
    )
    result = await check_repeat_offender(ctx)
    assert result.status == "pass"
    assert result.score == 0
    assert result.details["reason"] == "no team members"


@pytest.mark.asyncio
async def test_team_members_without_github_returns_pass():
    """Team members without GitHub usernames should score 0."""
    ctx = CheckContext(
        repo_path=None,
        scraped=ScrapedData(team_members=[
            {"name": "Alice", "devpost_profile": "/alice", "github": None},
            {"name": "Bob", "devpost_profile": "/bob", "github": None},
        ]),
        submission_id=uuid.uuid4(),
    )
    result = await check_repeat_offender(ctx)
    assert result.status == "pass"
    assert result.score == 0
    assert result.details["reason"] == "no github usernames found"


@pytest.mark.asyncio
async def test_no_prior_flags_returns_pass(db_session):
    """Team with GitHub usernames but no prior flagged submissions returns pass."""
    ctx = CheckContext(
        repo_path=None,
        scraped=ScrapedData(team_members=[
            {"name": "Alice", "devpost_profile": "/alice",
             "github": "https://github.com/alice"},
        ]),
        submission_id=uuid.uuid4(),
    )
    result = await check_repeat_offender(ctx, db=db_session)
    # With no flagged submissions in DB, should be pass
    assert result.status == "pass"


@pytest.mark.asyncio
async def test_suspicious_multiple_github_per_devpost(db_session):
    """Same Devpost profile linked to multiple GitHub accounts should trigger suspicious."""
    ctx = CheckContext(
        repo_path=None,
        scraped=ScrapedData(team_members=[
            {"name": "Alice", "devpost_profile": "/alice",
             "github": "https://github.com/alice"},
            {"name": "Alice Dupe", "devpost_profile": "/alice",
             "github": "https://github.com/alice2"},
        ]),
        submission_id=uuid.uuid4(),
    )
    result = await check_repeat_offender(ctx, db=db_session)
    assert result.score >= 20  # suspicious pattern detected
    assert len(result.details["suspicious_patterns"]) >= 1
