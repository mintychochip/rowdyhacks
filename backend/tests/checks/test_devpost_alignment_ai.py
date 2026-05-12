"""Tests for AI-based Devpost alignment check."""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import numpy as np
import pytest

from app.checks.devpost_alignment_ai import (
    MAX_CHUNKS,
    _chunk_repo,
    _extract_feature_claims,
    _linkify_evidence,
    _parse_json,
    _retrieve_chunks,
    _retrieve_chunks_async,
    check_alignment_ai,
)
from app.checks.interface import CheckContext, CheckResult, ScrapedData


@pytest.fixture
def mock_context(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("def main():\n    print('hello')\n")
    (repo / "README.md").write_text("# Project\n")

    scraped = ScrapedData(
        title="My App",
        description="A web app built with React and Flask. It detects objects using AI.",
        claimed_tech=["React", "Flask", "AI"],
        github_url="https://github.com/alice/myapp",
    )
    return CheckContext(
        repo_path=repo,
        scraped=scraped,
        submission_id=uuid4(),
        hackathon=None,
    )


@pytest.fixture
def mock_context_no_repo():
    return CheckContext(
        repo_path=None,
        scraped=ScrapedData(claimed_tech=["React"]),
        submission_id=uuid4(),
        hackathon=None,
    )


class TestCheckAlignmentAi:
    @pytest.mark.asyncio
    async def test_no_repo_returns_warn(self, mock_context_no_repo):
        with patch("app.checks.devpost_alignment_ai.settings") as mock_settings:
            mock_settings.get_poolside_key.return_value = "key"
            result = await check_alignment_ai(mock_context_no_repo)
        assert isinstance(result, CheckResult)
        assert result.status == "warn"
        assert result.details["reason"] == "No repo available"

    @pytest.mark.asyncio
    async def test_no_api_key_returns_pass(self, mock_context):
        with patch("app.checks.devpost_alignment_ai.settings") as mock_settings:
            mock_settings.get_poolside_key.return_value = ""
            result = await check_alignment_ai(mock_context)
        assert result.status == "pass"
        assert result.details["reason"] == "LLM not configured"

    @pytest.mark.asyncio
    async def test_no_claims_returns_pass(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        ctx = CheckContext(
            repo_path=repo,
            scraped=ScrapedData(claimed_tech=[]),
            submission_id=uuid4(),
            hackathon=None,
        )
        with patch("app.checks.devpost_alignment_ai.settings") as mock_settings:
            mock_settings.get_poolside_key.return_value = "key"
            result = await check_alignment_ai(ctx)
        assert result.status == "pass"

    @pytest.mark.asyncio
    async def test_successful_alignment_check(self, mock_context):
        llm_response = {
            "overall_assessment": "All claims verified",
            "claims": [
                {"claim": "Uses React", "verdict": "VERIFIED", "evidence": ["app.py:1-2"], "explanation": "Found"}
            ],
            "suspicious_patterns": [],
            "alignment_score": 10,
        }

        with (
            patch("app.checks.devpost_alignment_ai.settings") as mock_settings,
            patch("httpx.AsyncClient") as mock_client_cls,
            patch("app.checks.devpost_alignment_ai._parse_json", return_value=llm_response),
        ):
            mock_settings.get_poolside_key.return_value = "key"
            mock_settings.poolside_api_url = "https://api.test"
            mock_settings.poolside_model = "test-model"

            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = {"choices": [{"message": {"content": json.dumps(llm_response)}}]}

            mock_http = AsyncMock()
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_http

            result = await check_alignment_ai(mock_context)
            assert isinstance(result, CheckResult)
            assert result.status == "pass"
            assert result.score == 10

    @pytest.mark.asyncio
    async def test_llm_api_error(self, mock_context):
        with (
            patch("app.checks.devpost_alignment_ai.settings") as mock_settings,
            patch("httpx.AsyncClient") as mock_client_cls,
        ):
            mock_settings.get_poolside_key.return_value = "key"
            mock_settings.poolside_api_url = "https://api.test"

            mock_http = AsyncMock()
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_http.post = AsyncMock(side_effect=Exception("network error"))
            mock_client_cls.return_value = mock_http

            result = await check_alignment_ai(mock_context)
            assert result.status == "warn"
            assert "LLM API error" in result.details["reason"]


class TestChunkRepo:
    def test_chunks_source_files(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "main.py").write_text("\n".join(f"line {i}" for i in range(100)))
        chunks = _chunk_repo(repo)
        assert len(chunks) > 0
        assert all("file" in c for c in chunks)
        assert all("start_line" in c for c in chunks)

    def test_skips_binary_files(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "image.png").write_bytes(b"\x89PNG")
        (repo / "main.py").write_text("print(1)\n")
        chunks = _chunk_repo(repo)
        assert all(c["file"].endswith(".py") for c in chunks)

    def test_skips_large_files(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        large = repo / "big.py"
        large.write_text("x" * 200_000)
        chunks = _chunk_repo(repo)
        assert not any(c["file"] == "big.py" for c in chunks)

    def test_skips_skip_dirs(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "node_modules" / "pkg" / "main.py").mkdir(parents=True)
        (repo / "src").mkdir(parents=True)
        (repo / "src" / "main.py").write_text("print(1)\n")
        chunks = _chunk_repo(repo)
        assert not any("node_modules" in c["file"] for c in chunks)

    def test_respects_max_chunks(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        for i in range(500):
            (repo / f"f{i}.py").write_text("\n".join(f"line {j}" for j in range(100)))
        chunks = _chunk_repo(repo)
        assert len(chunks) <= MAX_CHUNKS


class TestRetrieveChunks:
    def test_empty_chunks(self):
        result = _retrieve_chunks(["claim"], [])
        assert result == []

    def test_retrieves_top_k(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "main.py").write_text("import react\nimport flask\n")
        chunks = _chunk_repo(repo)
        claims = ["uses react"]
        result = _retrieve_chunks(claims, chunks)
        assert isinstance(result, list)


@pytest.mark.asyncio
class TestRetrieveChunksAsync:
    async def test_tfidf_fallback_when_embedding_fails(self):
        chunks = [{"file": "a.py", "content": "print(1)"}]
        with patch("app.checks.devpost_alignment_ai._embed_chunks_bge", return_value=None):
            result = await _retrieve_chunks_async(["claim"], chunks)
            assert isinstance(result, list)

    async def test_combines_tfidf_and_embedding(self):
        chunks = [{"file": "a.py", "content": "print(1)"}]
        with (
            patch("app.checks.devpost_alignment_ai._embed_chunks_bge", return_value=np.array([[0.1, 0.2]])),
            patch("app.checks.devpost_alignment_ai._embed_chunks_bge_static", return_value=np.array([[0.1, 0.2]])),
        ):
            result = await _retrieve_chunks_async(["claim"], chunks)
            assert isinstance(result, list)


class TestExtractFeatureClaims:
    def test_extracts_claims(self):
        desc = "Built with React and powered by AI. Detects objects in real-time."
        claims = _extract_feature_claims(desc)
        assert len(claims) > 0
        assert all(len(c) > 15 for c in claims)

    def test_empty_description(self):
        assert _extract_feature_claims("") == []


class TestLinkifyEvidence:
    def test_already_url(self):
        assert (
            _linkify_evidence("https://github.com/a/b/blob/main/c.py#L1", "")
            == "https://github.com/a/b/blob/main/c.py#L1"
        )

    def test_no_blob_base(self):
        assert _linkify_evidence("app.py:1-10", "") == "app.py:1-10"

    def test_linkifies_path(self):
        result = _linkify_evidence("app.py:1-10", "https://github.com/a/b/blob/main")
        assert "https://github.com/a/b/blob/main/app.py#L1-L10" in result

    def test_linkifies_with_description(self):
        result = _linkify_evidence("app.py:1-10 — main entry", "https://github.com/a/b/blob/main")
        assert "https://github.com/a/b/blob/main/app.py#L1-L10" in result


class TestParseJson:
    def test_parses_plain_json(self):
        assert _parse_json('{"a": 1}') == {"a": 1}

    def test_parses_code_fence(self):
        assert _parse_json('```json\n{"a": 1}\n```') == {"a": 1}

    def test_parses_generic_fence(self):
        assert _parse_json('```\n{"a": 1}\n```') == {"a": 1}

    def test_repairs_truncated(self):
        assert _parse_json('{"a": 1, "b": [1, 2') == {"a": 1, "b": [1, 2]}

    def test_returns_none_on_unrepairable(self):
        assert _parse_json("not json at all") is None
