import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from app.checks.ai_detection import check_ai
from app.checks.interface import CheckContext, ScrapedData


@pytest.mark.asyncio
async def test_ai_detection_clean():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        (repo / "code.py").write_text("def foo():\n    x = 1\n    y = 2\n    return x + y\n")
        ctx = CheckContext(repo_path=repo, scraped=ScrapedData(), submission_id=uuid4())
        result = await check_ai(ctx)
        assert result.score <= 30


@pytest.mark.asyncio
async def test_ai_detection_ai_phrases():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        (repo / "code.py").write_text(
            "# Certainly! Here's the implementation\n"
            "# I hope this helps!\n"
            "# This function takes two numbers\n"
            "# Let me know if you have any questions\n"
            "\n"
            "def add(a, b):\n"
            "    return a + b\n"
        )
        ctx = CheckContext(repo_path=repo, scraped=ScrapedData(), submission_id=uuid4())
        result = await check_ai(ctx)
        assert result.details["ai_phrases_found"] > 0
        assert result.score > 0


@pytest.mark.asyncio
async def test_ai_detection_no_repo():
    ctx = CheckContext(repo_path=None, scraped=ScrapedData(), submission_id=uuid4())
    result = await check_ai(ctx)
    assert result.status == "pass"
