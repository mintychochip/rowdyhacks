"""Tests for code similarity check."""

from uuid import uuid4

import pytest

from app.checks.code_similarity import _compute_simhash, _get_shingles, _hamming_distance, check_code_similarity
from app.checks.interface import CheckContext, ScrapedData


def test_shingle_generation():
    """Test shingle generation."""
    text = "def hello world function test"
    shingles = _get_shingles(text, k=2)
    assert len(shingles) > 0
    assert "def hello" in shingles


def test_simhash_computation():
    """Test SimHash fingerprint computation."""
    text = "def hello world function test code"
    shingles = _get_shingles(text)
    fingerprint = _compute_simhash(shingles)
    assert isinstance(fingerprint, int)
    assert fingerprint != 0


def test_hamming_distance():
    """Test Hamming distance calculation."""
    a = 0b10101010
    b = 0b10101011
    dist = _hamming_distance(a, b)
    assert dist == 1


@pytest.mark.asyncio
async def test_similarity_no_repo(tmp_path):
    context = CheckContext(repo_path=None, scraped=ScrapedData(), hackathon=None, submission_id=uuid4())
    result = await check_code_similarity(context)
    assert result.status == "pass"
    assert result.score == 0


@pytest.mark.asyncio
async def test_similarity_not_enough_code(tmp_path):
    # Very small code file
    (tmp_path / "tiny.py").write_text("print('hi')")
    context = CheckContext(repo_path=tmp_path, scraped=ScrapedData(), hackathon=None, submission_id=uuid4())
    result = await check_code_similarity(context)
    # Low score due to minimal code
    assert result.status == "pass"


@pytest.mark.asyncio
async def test_similarity_with_diverse_code(tmp_path):
    # Create diverse code files
    (tmp_path / "main.py").write_text("""
def process_data(data):
    results = []
    for item in data:
        if item.valid:
            results.append(transform(item))
    return results

class DataStore:
    def __init__(self, connection_string):
        self.conn = create_connection(connection_string)
        self.cache = LRUCache()

    def query(self, sql, params):
        return self.conn.execute(sql, params)
""")

    (tmp_path / "utils.py").write_text("""
import hashlib
import json
from datetime import datetime

def hash_content(content):
    return hashlib.sha256(content.encode()).hexdigest()[:16]

def format_timestamp(ts):
    return datetime.fromtimestamp(ts).isoformat()

def parse_json_safe(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
""")

    context = CheckContext(repo_path=tmp_path, scraped=ScrapedData(), hackathon=None, submission_id=uuid4())
    result = await check_code_similarity(context)

    # Should analyze the code
    assert result.details.get("total_lines", 0) > 0
    assert result.details.get("unique_shingles", 0) > 0
