"""Tests for repository age check."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from app.checks.interface import CheckContext, HackathonInfo, ScrapedData
from app.checks.repo_age import check_repo_age


def _make_context(github_url: str | None = None, hackathon: HackathonInfo | None = None) -> CheckContext:
    return CheckContext(
        repo_path=None,
        scraped=ScrapedData(github_url=github_url),
        submission_id=uuid4(),
        hackathon=hackathon,
    )


def _mock_client(response: MagicMock):
    """Return a patch target for httpx.AsyncClient that yields ``response`` from ``get``."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=response)
    return mock_client


@pytest.mark.asyncio
async def test_repo_age_no_github_url():
    """Must return pass when no GitHub URL is present."""
    ctx = _make_context()
    result = await check_repo_age(ctx)
    assert result.status == "pass"
    assert result.score == 0
    assert result.details["reason"] == "No GitHub URL available"


@pytest.mark.asyncio
async def test_repo_age_unparseable_url():
    """Must return pass when URL cannot be parsed."""
    ctx = _make_context(github_url="https://not-github.com/foo/bar")
    result = await check_repo_age(ctx)
    assert result.status == "pass"
    assert result.score == 0
    assert result.details["reason"] == "Could not parse GitHub URL"


@pytest.mark.asyncio
async def test_repo_age_api_error():
    """Must return pass with low score when GitHub API returns non-200."""
    ctx = _make_context(github_url="https://github.com/owner/repo")
    response = MagicMock()
    response.status_code = 404
    with patch("httpx.AsyncClient", return_value=_mock_client(response)):
        result = await check_repo_age(ctx)
    assert result.status == "pass"
    assert result.score == 10
    assert "404" in result.details["reason"]


@pytest.mark.asyncio
async def test_repo_age_old_repo():
    """Must flag repos older than 365 days with a high score."""
    old_date = (datetime.now(UTC).replace(tzinfo=None) - timedelta(days=400)).isoformat() + "Z"
    ctx = _make_context(github_url="https://github.com/owner/repo")
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "created_at": old_date,
        "pushed_at": old_date,
        "stargazers_count": 0,
        "forks_count": 0,
        "fork": False,
        "default_branch": "main",
        "open_issues_count": 0,
    }
    with patch("httpx.AsyncClient", return_value=_mock_client(response)):
        result = await check_repo_age(ctx)
    assert result.status in ("warn", "fail")
    assert result.score >= 40
    assert result.details["age_days"] >= 365


@pytest.mark.asyncio
async def test_repo_age_fork():
    """Must increase score for forked repositories."""
    recent_date = datetime.now(UTC).isoformat()
    ctx = _make_context(github_url="https://github.com/owner/repo")
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "created_at": recent_date,
        "pushed_at": recent_date,
        "stargazers_count": 0,
        "forks_count": 0,
        "fork": True,
        "default_branch": "main",
        "open_issues_count": 0,
        "parent": {"full_name": "original/repo"},
    }
    with patch("httpx.AsyncClient", return_value=_mock_client(response)):
        result = await check_repo_age(ctx)
    assert result.score >= 30
    assert any("fork" in e.lower() for e in result.evidence)
    assert result.details["forked_from"] == "original/repo"


@pytest.mark.asyncio
async def test_repo_age_high_stars():
    """Must increase score for repositories with many stars."""
    recent_date = datetime.now(UTC).isoformat()
    ctx = _make_context(github_url="https://github.com/owner/repo")
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "created_at": recent_date,
        "pushed_at": recent_date,
        "stargazers_count": 60,
        "forks_count": 0,
        "fork": False,
        "default_branch": "main",
        "open_issues_count": 0,
    }
    with patch("httpx.AsyncClient", return_value=_mock_client(response)):
        result = await check_repo_age(ctx)
    assert result.score >= 40
    assert any("star" in e.lower() for e in result.evidence)


@pytest.mark.asyncio
async def test_repo_age_hackathon_context_pre_existing():
    """Must flag repos created well before hackathon start."""
    hack_start = (datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1)).isoformat()
    repo_created = (datetime.now(UTC).replace(tzinfo=None) - timedelta(days=60)).isoformat() + "Z"
    ctx = _make_context(
        github_url="https://github.com/owner/repo",
        hackathon=HackathonInfo(
            id=uuid4(),
            name="Test Hack",
            start_date=hack_start,
            end_date=hack_start,
        ),
    )
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "created_at": repo_created,
        "pushed_at": repo_created,
        "stargazers_count": 0,
        "forks_count": 0,
        "fork": False,
        "default_branch": "main",
        "open_issues_count": 0,
    }
    with patch("httpx.AsyncClient", return_value=_mock_client(response)):
        result = await check_repo_age(ctx)
    assert result.status in ("warn", "fail")
    assert any("before hackathon" in e.lower() for e in result.evidence)


@pytest.mark.asyncio
async def test_repo_age_exception_handling():
    """Must return pass with low score when an exception occurs."""
    ctx = _make_context(github_url="https://github.com/owner/repo")
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(side_effect=Exception("boom"))
    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await check_repo_age(ctx)
    assert result.status == "pass"
    assert result.score == 10
    assert "boom" in result.details["reason"]
