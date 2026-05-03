import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from app.checks.interface import CheckContext, ScrapedData
from app.checks.submission_history import check_history


@pytest.mark.asyncio
async def test_history_clean():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        (repo / "README.md").write_text("# My Project\n\nBuilt for a hackathon.\n")
        ctx = CheckContext(
            repo_path=repo,
            scraped=ScrapedData(team_members=[{"name": "Alice"}]),
            submission_id=uuid4(),
        )
        result = await check_history(ctx)
        assert result.score == 0


@pytest.mark.asyncio
async def test_history_readme_mentions_other_hackathon():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        (repo / "README.md").write_text("# My Project\n\nBuilt for HackMIT 2023.\n")
        ctx = CheckContext(
            repo_path=repo,
            scraped=ScrapedData(team_members=[{"name": "Alice"}]),
            submission_id=uuid4(),
        )
        result = await check_history(ctx)
        assert result.score > 0
        assert result.details["wrong_readme"] is True


@pytest.mark.asyncio
async def test_history_no_repo():
    ctx = CheckContext(repo_path=None, scraped=ScrapedData(), submission_id=uuid4())
    result = await check_history(ctx)
    assert result.score == 0  # can't check without repo
