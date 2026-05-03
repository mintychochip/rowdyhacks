import pytest

from app.checks.interface import CheckCategory, CheckResult, ScrapedData


def test_check_result_valid():
    r = CheckResult(check_name="test", check_category="timeline", score=50, status="warn")
    assert r.score == 50
    assert r.status == "warn"
    assert r.details == {}
    assert r.evidence == []


def test_check_result_score_range():
    with pytest.raises(ValueError, match="0-100"):
        CheckResult(check_name="t", check_category="t", score=-1, status="pass")
    with pytest.raises(ValueError, match="0-100"):
        CheckResult(check_name="t", check_category="t", score=101, status="pass")


def test_check_result_invalid_status():
    with pytest.raises(ValueError, match="Invalid status"):
        CheckResult(check_name="t", check_category="t", score=0, status="unknown")


def test_scraped_data_defaults():
    s = ScrapedData()
    assert s.title is None
    assert s.claimed_tech == []
    assert s.team_members == []


def test_check_categories():
    assert CheckCategory.TIMELINE.value == "timeline"
    assert CheckCategory.AI_DETECTION.value == "ai_detection"
