import uuid
import pytest
from datetime import datetime, timezone
from app.checks.interface import CheckContext, ScrapedData, HackathonInfo
from app.checks.cross_hackathon import check_cross_hackathon_duplicate


@pytest.mark.asyncio
async def test_no_duplicate_when_no_github_url():
    """Check returns pass when there's no GitHub URL."""
    ctx = CheckContext(
        repo_path=None,
        scraped=ScrapedData(github_url=None),
        submission_id=uuid.uuid4(),
        hackathon=HackathonInfo(
            id=uuid.uuid4(), name="Test Hack",
            start_date="2025-01-01T00:00:00", end_date="2025-01-03T00:00:00"
        ),
    )
    result = await check_cross_hackathon_duplicate(ctx)
    assert result.status == "pass"
    assert result.score == 0


@pytest.mark.asyncio
async def test_no_match_when_index_empty(db_session):
    """Check returns pass when crawled_projects is empty."""
    ctx = CheckContext(
        repo_path=None,
        scraped=ScrapedData(github_url="https://github.com/alice/unique-project"),
        submission_id=uuid.uuid4(),
    )
    result = await check_cross_hackathon_duplicate(ctx, db=db_session)
    assert result.status == "pass"
    assert result.score == 0


@pytest.mark.asyncio
async def test_detects_exact_github_url_match(db_session):
    """Same GitHub URL in a different hackathon should score 90."""
    from app.models import CrawledHackathon, CrawledProject

    hackathon_1_id = uuid.uuid4()
    hackathon_2_id = uuid.uuid4()
    duplicate_url = "https://github.com/alice/duplicate-project"

    # Seed: two hackathons, same GitHub URL in crawled_projects (different hackathon)
    db_session.add_all([
        CrawledHackathon(id=hackathon_1_id, devpost_url="http://dp.com/h/1", name="H1"),
        CrawledHackathon(id=hackathon_2_id, devpost_url="http://dp.com/h/2", name="H2"),
    ])
    await db_session.flush()

    db_session.add(CrawledProject(
        id=uuid.uuid4(),
        devpost_url="http://dp.com/s/dup",
        hackathon_id=hackathon_2_id,  # DIFFERENT hackathon
        github_url=duplicate_url,
        title="Duplicate Project",
    ))
    await db_session.flush()

    ctx = CheckContext(
        repo_path=None,
        scraped=ScrapedData(github_url=duplicate_url, claimed_tech=[], team_members=[]),
        submission_id=uuid.uuid4(),
        hackathon=HackathonInfo(
            id=hackathon_1_id, name="H1",
            start_date="2025-01-01T00:00:00", end_date="2025-01-03T00:00:00"
        ),
    )
    result = await check_cross_hackathon_duplicate(ctx, db=db_session)
    assert result.status in ("warn", "fail")
    assert result.score >= 90


@pytest.mark.asyncio
async def test_no_duplicate_same_hackathon(db_session):
    """Same GitHub URL in the SAME hackathon should NOT flag."""
    from app.models import CrawledHackathon, CrawledProject

    hackathon_id = uuid.uuid4()
    same_url = "https://github.com/alice/test"

    db_session.add(CrawledHackathon(id=hackathon_id, devpost_url="http://dp.com/h/1", name="H1"))
    await db_session.flush()
    db_session.add(CrawledProject(
        id=uuid.uuid4(),
        devpost_url="http://dp.com/s/test",
        hackathon_id=hackathon_id,  # SAME hackathon
        github_url=same_url,
    ))
    await db_session.flush()

    ctx = CheckContext(
        repo_path=None,
        scraped=ScrapedData(github_url=same_url, claimed_tech=[], team_members=[]),
        submission_id=uuid.uuid4(),
        hackathon=HackathonInfo(
            id=hackathon_id, name="H1",
            start_date="2025-01-01T00:00:00", end_date="2025-01-03T00:00:00"
        ),
    )
    result = await check_cross_hackathon_duplicate(ctx, db=db_session)
    assert result.status == "pass"
    assert result.score == 0
