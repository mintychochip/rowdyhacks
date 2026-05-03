from datetime import UTC, datetime, timedelta

import pytest
from app.models import CheckResultModel, CheckStatus, Hackathon, Submission, SubmissionStatus, User, UserRole, Verdict
from sqlalchemy import select
from sqlalchemy.orm import selectinload


@pytest.mark.asyncio
async def test_create_user(db_session):
    """Create a user and verify it persists."""
    user = User(
        email="test@example.com",
        name="Test User",
        role=UserRole.organizer,
        password_hash="$2b$12$abcdefghijklmnopqrstuv",
    )
    db_session.add(user)
    await db_session.commit()

    result = await db_session.execute(select(User).where(User.email == "test@example.com"))
    fetched = result.scalar_one()
    assert fetched.id is not None
    assert fetched.email == "test@example.com"
    assert fetched.name == "Test User"
    assert fetched.role == UserRole.organizer
    assert fetched.password_hash == "$2b$12$abcdefghijklmnopqrstuv"
    assert fetched.created_at is not None


@pytest.mark.asyncio
async def test_create_hackathon(db_session):
    """Create a hackathon linked to a user."""
    user = User(
        email="org@example.com",
        name="Organizer",
        role=UserRole.organizer,
        password_hash="hash",
    )
    db_session.add(user)
    await db_session.flush()

    now = datetime.now(UTC)
    hackathon = Hackathon(
        name="TestHack 2026",
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=1),
        organizer_id=user.id,
    )
    db_session.add(hackathon)
    await db_session.commit()

    result = await db_session.execute(select(Hackathon).where(Hackathon.name == "TestHack 2026"))
    fetched = result.scalar_one()
    assert fetched.id is not None
    assert fetched.organizer_id == user.id
    assert fetched.start_date < now


@pytest.mark.asyncio
async def test_create_submission_with_check_results(db_session):
    """Create a submission with nested check results and verify relationships."""
    user = User(
        email="participant@example.com",
        name="Participant",
        role=UserRole.participant,
        password_hash="hash",
    )
    db_session.add(user)
    await db_session.flush()

    submission = Submission(
        devpost_url="https://devpost.com/software/test-project",
        github_url="https://github.com/user/test-project",
        project_title="Test Project",
        project_description="A test project",
        claimed_tech=["Python", "FastAPI"],
        team_members=[{"name": "Participant", "devpost_profile": "participant"}],
        submitted_by=user.id,
        status=SubmissionStatus.completed,
        risk_score=15,
        verdict=Verdict.clean,
    )
    db_session.add(submission)
    await db_session.flush()

    check = CheckResultModel(
        submission_id=submission.id,
        check_category="timeline",
        check_name="commit-timestamps",
        score=10,
        status=CheckStatus.pass_,
        details={"commits_before_start": 0, "commits_after_end": 0},
        evidence=["https://github.com/user/test-project/commits"],
    )
    db_session.add(check)
    await db_session.commit()

    # Verify relationships (eagerly load to avoid lazy loading in async session)
    result = await db_session.execute(
        select(Submission)
        .where(Submission.id == submission.id)
        .options(selectinload(Submission.check_results), selectinload(Submission.submitter))
    )
    fetched = result.scalar_one()
    assert len(fetched.check_results) == 1
    assert fetched.check_results[0].check_name == "commit-timestamps"
    assert fetched.check_results[0].score == 10
    assert fetched.submitter.email == "participant@example.com"
