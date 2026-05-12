"""Tests for cross-team similarity check."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.checks.interface import CheckResult
from app.checks.similarity import _get_head_commit, _parse_repo_name, run_similarity
from app.models import Hackathon, Submission, SubmissionStatus, User, UserRole


@pytest_asyncio.fixture
async def hackathon_with_submissions(db_session: AsyncSession):
    """Create a hackathon with multiple submissions for similarity testing."""
    uid = uuid.uuid4().hex[:8]
    user = User(
        id=f"user-{uid}",
        email=f"{uid}@example.com",
        name="Test User",
        role=UserRole.participant,
    )
    db_session.add(user)

    hackathon = Hackathon(
        name="Sim Hack",
        start_date=__import__("datetime").datetime.now(__import__("datetime").UTC),
        end_date=__import__("datetime").datetime.now(__import__("datetime").UTC),
        organizer_id=user.id,
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)

    # Two completed submissions with the same GitHub URL
    sub1 = Submission(
        hackathon_id=hackathon.id,
        devpost_url="https://devpost.com/a",
        github_url="https://github.com/owner/repo",
        status=SubmissionStatus.completed,
    )
    sub2 = Submission(
        hackathon_id=hackathon.id,
        devpost_url="https://devpost.com/b",
        github_url="https://github.com/owner/repo ",
        status=SubmissionStatus.completed,
    )
    # Pending submission should be ignored
    sub3 = Submission(
        hackathon_id=hackathon.id,
        devpost_url="https://devpost.com/c",
        github_url="https://github.com/owner/repo",
        status=SubmissionStatus.pending,
    )
    db_session.add_all([sub1, sub2, sub3])
    await db_session.commit()
    return hackathon, [sub1, sub2, sub3]


@pytest.mark.anyio
async def test_run_similarity_finds_duplicates(db_session: AsyncSession, hackathon_with_submissions):
    """run_similarity must flag duplicate GitHub URLs among completed submissions."""
    hackathon, submissions = hackathon_with_submissions

    # Patch async_session to yield the test session
    class FakeSessionMgr:
        async def __aenter__(self):
            return db_session

        async def __aexit__(self, *args):
            pass

    with patch("app.checks.similarity.async_session", return_value=FakeSessionMgr()):
        results = await run_similarity(hackathon.id)

    assert len(results) >= 1
    assert all(isinstance(r, CheckResult) for r in results)
    duplicate = next(r for r in results if r.check_name == "duplicate-github-url")
    assert duplicate.status == "fail"
    assert duplicate.score == 80
    assert duplicate.details["duplicate_url"] == "https://github.com/owner/repo"


@pytest.mark.anyio
async def test_run_similarity_no_submissions(db_session: AsyncSession):
    """run_similarity must return empty list when there are no completed submissions."""
    uid = uuid.uuid4().hex[:8]
    user = User(
        id=f"user-{uid}",
        email=f"{uid}@example.com",
        name="Test User",
        role=UserRole.participant,
    )
    db_session.add(user)
    hackathon = Hackathon(
        name="Empty Hack",
        start_date=__import__("datetime").datetime.now(__import__("datetime").UTC),
        end_date=__import__("datetime").datetime.now(__import__("datetime").UTC),
        organizer_id=user.id,
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)

    class FakeSessionMgr:
        async def __aenter__(self):
            return db_session

        async def __aexit__(self, *args):
            pass

    with patch("app.checks.similarity.async_session", return_value=FakeSessionMgr()):
        results = await run_similarity(hackathon.id)

    assert results == []


@pytest.mark.asyncio
async def test_parse_repo_name_variants():
    """_parse_repo_name must handle HTTPS, SSH, and invalid URLs."""
    assert _parse_repo_name("https://github.com/owner/repo") == "owner/repo"
    assert _parse_repo_name("https://github.com/owner/repo.git") == "owner/repo"
    assert _parse_repo_name("git@github.com:owner/repo.git") == "owner/repo"
    assert _parse_repo_name(None) is None
    assert _parse_repo_name("") is None
    assert _parse_repo_name("https://gitlab.com/foo/bar") is None


@pytest.mark.asyncio
async def test_get_head_commit_success():
    """_get_head_commit must return a 40-character SHA on success."""
    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.communicate.return_value = (
        b"abc123def4567890abc123def4567890abc12345\tHEAD\n",
        b"",
    )
    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        sha = await _get_head_commit("https://github.com/owner/repo")
    assert sha == "abc123def4567890abc123def4567890abc12345"
    assert len(sha) == 40


@pytest.mark.asyncio
async def test_get_head_commit_failure():
    """_get_head_commit must return None when git ls-remote fails."""
    mock_proc = AsyncMock()
    mock_proc.returncode = 1
    mock_proc.communicate.return_value = (b"", b"error")
    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        sha = await _get_head_commit("https://github.com/owner/repo")
    assert sha is None
