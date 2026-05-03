import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from app.checks.devpost_alignment import check_alignment
from app.checks.interface import CheckContext, ScrapedData


@pytest.fixture
def repo_with_package_json():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        (repo / "package.json").write_text('{"dependencies": {"react": "^18.0.0", "express": "^4.0.0"}}')
        (repo / "src").mkdir()
        (repo / "src" / "app.js").write_text("import React from 'react';")
        yield repo


@pytest.mark.asyncio
async def test_alignment_all_found(repo_with_package_json):
    scraped = ScrapedData(claimed_tech=["react", "express"], title="Test")
    ctx = CheckContext(repo_path=repo_with_package_json, scraped=scraped, submission_id=uuid4())
    result = await check_alignment(ctx)
    assert result.score <= 10  # all tech found
    assert len(result.details["missing_tech"]) == 0


@pytest.mark.asyncio
async def test_alignment_missing_tech(repo_with_package_json):
    scraped = ScrapedData(claimed_tech=["react", "redux", "tailwindcss"], title="Test")
    ctx = CheckContext(repo_path=repo_with_package_json, scraped=scraped, submission_id=uuid4())
    result = await check_alignment(ctx)
    assert "redux" in result.details["missing_tech"]
    assert result.score > 0


@pytest.mark.asyncio
async def test_alignment_no_repo():
    ctx = CheckContext(
        repo_path=None,
        scraped=ScrapedData(claimed_tech=["react"]),
        submission_id=uuid4(),
    )
    result = await check_alignment(ctx)
    assert result.status == "warn"
