import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from app.checks.asset_integrity import check_assets
from app.checks.interface import CheckContext, ScrapedData


@pytest.mark.asyncio
async def test_assets_missing_readme():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        ctx = CheckContext(repo_path=repo, scraped=ScrapedData(), submission_id=uuid4())
        result = await check_assets(ctx)
        assert result.score > 0
        assert "README" in result.details["missing_assets"]


@pytest.mark.asyncio
async def test_assets_with_readme():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        (repo / "README.md").write_text("# Project\n")
        ctx = CheckContext(repo_path=repo, scraped=ScrapedData(), submission_id=uuid4())
        result = await check_assets(ctx)
        assert "README" not in result.details["missing_assets"]


@pytest.mark.asyncio
async def test_assets_ai_disclosure():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        (repo / "README.md").write_text("# Project\n\nBuilt with assistance from ChatGPT and GitHub Copilot.\n")
        ctx = CheckContext(repo_path=repo, scraped=ScrapedData(), submission_id=uuid4())
        result = await check_assets(ctx)
        assert result.details["ai_disclosure"] is True
