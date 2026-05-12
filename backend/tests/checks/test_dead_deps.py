"""Tests for dead dependency check."""

import json
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from app.checks.dead_deps import check_dead_deps
from app.checks.interface import CheckContext, ScrapedData


@pytest.mark.asyncio
async def test_dead_deps_no_repo():
    """Must return pass when no repo path is available."""
    ctx = CheckContext(repo_path=None, scraped=ScrapedData(), submission_id=uuid4())
    result = await check_dead_deps(ctx)
    assert result.status == "pass"
    assert result.score == 20
    assert result.details["reason"] == "No repo available"


@pytest.mark.asyncio
async def test_dead_deps_no_package_files():
    """Must return pass when repo has no package files."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        ctx = CheckContext(repo_path=repo, scraped=ScrapedData(), submission_id=uuid4())
        result = await check_dead_deps(ctx)
        assert result.status == "pass"
        assert result.score == 0
        assert result.details["reason"] == "No package files found"


@pytest.mark.asyncio
async def test_dead_deps_all_used():
    """Must return pass when all declared deps are imported."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        pkg = repo / "package.json"
        pkg.write_text('{"dependencies": {"react": "^18.0.0"}}')
        src = repo / "src"
        src.mkdir()
        (src / "app.js").write_text("import React from 'react';\n")
        ctx = CheckContext(repo_path=repo, scraped=ScrapedData(), submission_id=uuid4())
        result = await check_dead_deps(ctx)
        assert result.status == "pass"
        assert result.score == 0
        assert result.details["total_declared"] == 1
        assert result.details["missing"] == []


@pytest.mark.asyncio
async def test_dead_deps_some_unused():
    """Must flag unused dependencies with a non-zero score."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        pkg = repo / "package.json"
        pkg.write_text('{"dependencies": {"react": "^18.0.0", "unused-lib": "1.0.0"}}')
        src = repo / "src"
        src.mkdir()
        (src / "app.js").write_text("import React from 'react';\n")
        ctx = CheckContext(repo_path=repo, scraped=ScrapedData(), submission_id=uuid4())
        result = await check_dead_deps(ctx)
        assert result.status in ("pass", "warn")
        assert result.score > 0
        assert "unused-lib" in result.details["missing"]


@pytest.mark.asyncio
async def test_dead_deps_requirements_txt():
    """Must parse requirements.txt and flag unused Python packages."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        req = repo / "requirements.txt"
        req.write_text("requests>=2.0\nflask==2.0\n")
        src = repo / "main.py"
        src.write_text("import requests\n")
        ctx = CheckContext(repo_path=repo, scraped=ScrapedData(), submission_id=uuid4())
        result = await check_dead_deps(ctx)
        assert result.status in ("pass", "warn")
        assert "flask" in result.details["missing"]
        assert "requests" not in result.details["missing"]


@pytest.mark.asyncio
async def test_dead_deps_pipfile():
    """Must parse Pipfile and flag unused packages."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        pipfile = repo / "Pipfile"
        pipfile.write_text('[packages]\nrequests = "*"\ndjango = "*"\n')
        src = repo / "main.py"
        src.write_text("import requests\n")
        ctx = CheckContext(repo_path=repo, scraped=ScrapedData(), submission_id=uuid4())
        result = await check_dead_deps(ctx)
        assert "django" in result.details["missing"]
        assert "requests" not in result.details["missing"]


@pytest.mark.asyncio
async def test_dead_deps_high_percentage_warn():
    """Must escalate to warn/fail when many deps are unused."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        pkg = repo / "package.json"
        deps = {f"dep-{i}": "1.0.0" for i in range(5)}
        pkg.write_text(json.dumps({"dependencies": deps}))
        src = repo / "index.js"
        src.write_text("import dep_0 from 'dep-0';\n")
        ctx = CheckContext(repo_path=repo, scraped=ScrapedData(), submission_id=uuid4())
        result = await check_dead_deps(ctx)
        assert result.status in ("warn", "fail")
        assert result.details["pct_dead"] >= 50
