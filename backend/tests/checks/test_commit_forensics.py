"""Tests for commit forensics check."""

import subprocess
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.checks.commit_forensics import check_commit_forensics
from app.checks.interface import CheckContext, ScrapedData


@pytest.mark.asyncio
async def test_forensics_no_repo(tmp_path):
    context = CheckContext(repo_path=None, scraped=ScrapedData(), hackathon=None, submission_id=uuid4())
    result = await check_commit_forensics(context)
    assert result.status == "pass"
    assert result.score == 0


@pytest.mark.asyncio
async def test_forensics_clean_repo(tmp_path):
    # Create a clean repo with normal commits
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)

    # Create a file and commit
    (tmp_path / "test.txt").write_text("hello")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial", "--no-verify"], cwd=tmp_path, capture_output=True)

    context = CheckContext(repo_path=tmp_path, scraped=ScrapedData(), hackathon=None, submission_id=uuid4())
    result = await check_commit_forensics(context)
    assert result.status == "pass"


@pytest.mark.asyncio
async def test_forensics_future_commit(tmp_path):
    # Create a repo with a future-dated commit
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)

    future = datetime.now(UTC) + timedelta(days=7)
    future_str = future.strftime("%Y-%m-%d %H:%M:%S")

    (tmp_path / "test.txt").write_text("hello")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "future", f"--date={future_str}", "--no-verify"], cwd=tmp_path, capture_output=True
    )

    context = CheckContext(repo_path=tmp_path, scraped=ScrapedData(), hackathon=None, submission_id=uuid4())
    result = await check_commit_forensics(context)
    # Should flag future commits (commit has author date in future, not commit date)
    # The check looks for future-dated commits in the details
    assert "future_commits" in result.details or result.score > 0


@pytest.mark.asyncio
async def test_forensics_date_mismatch(tmp_path):
    # Create a repo with backdated commits
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)

    past = datetime.now(UTC) - timedelta(days=30)
    past_str = past.strftime("%Y-%m-%d %H:%M:%S")

    (tmp_path / "test.txt").write_text("hello")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "backdated", f"--date={past_str}", "--no-verify"], cwd=tmp_path, capture_output=True
    )

    context = CheckContext(repo_path=tmp_path, scraped=ScrapedData(), hackathon=None, submission_id=uuid4())
    result = await check_commit_forensics(context)
    # Should detect author/commit date mismatch
    assert "author_date_mismatches" in result.details
