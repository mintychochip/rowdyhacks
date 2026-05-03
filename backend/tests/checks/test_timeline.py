import subprocess
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from app.checks.interface import CheckContext, HackathonInfo, ScrapedData
from app.checks.timeline import check_commits


@pytest.fixture
def git_repo():
    """Create a temp git repo with commits."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        # Use --template='' to skip any global git hooks
        subprocess.run(["git", "init", "--template=''"], cwd=repo, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo,
            capture_output=True,
        )
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
        (repo / "file.txt").write_text("content")
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit", "--date=2026-04-15T10:00:00", "--no-verify"],
            cwd=repo,
            capture_output=True,
        )
        (repo / "file.txt").write_text("updated")
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add feature", "--date=2026-04-15T14:00:00", "--no-verify"],
            cwd=repo,
            capture_output=True,
        )
        yield repo


@pytest.mark.asyncio
async def test_check_commits_clean(git_repo):
    hackathon = HackathonInfo(
        id=uuid4(),
        name="TestHack",
        start_date="2026-04-15T00:00:00",
        end_date="2026-04-16T00:00:00",
    )
    ctx = CheckContext(
        repo_path=git_repo,
        scraped=ScrapedData(),
        submission_id=uuid4(),
        hackathon=hackathon,
    )
    result = await check_commits(ctx)
    assert result.score <= 30
    assert result.status == "pass"


@pytest.mark.asyncio
async def test_check_commits_no_repo():
    ctx = CheckContext(repo_path=None, scraped=ScrapedData(), submission_id=uuid4())
    result = await check_commits(ctx)
    assert result.score == 30
    assert result.status == "warn"


@pytest.mark.asyncio
async def test_check_commits_before_hackathon():
    """Commits before hackathon should increase score."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        subprocess.run(["git", "init", "--template=''"], cwd=repo, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo,
            capture_output=True,
        )
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
        (repo / "f.txt").write_text("x")
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "pre-hack", "--date=2026-04-10T10:00:00", "--no-verify"],
            cwd=repo,
            capture_output=True,
        )
        (repo / "f.txt").write_text("y")
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "during-hack", "--date=2026-04-15T14:00:00", "--no-verify"],
            cwd=repo,
            capture_output=True,
        )

        hackathon = HackathonInfo(
            id=uuid4(),
            name="Hack",
            start_date="2026-04-15T00:00:00",
            end_date="2026-04-16T00:00:00",
        )
        ctx = CheckContext(
            repo_path=repo,
            scraped=ScrapedData(),
            submission_id=uuid4(),
            hackathon=hackathon,
        )
        result = await check_commits(ctx)
        # Should flag the pre-hackathon commit
        assert result.score > 0
