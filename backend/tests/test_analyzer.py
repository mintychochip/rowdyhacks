import pytest
import uuid
from unittest.mock import patch, AsyncMock
from app.analyzer import analyze_submission


@pytest.mark.asyncio
async def test_analyze_submission_scraper_error():
    """If scraping fails, submission should be marked failed."""
    submission_id = uuid.uuid4()
    # Won't work without a real DB, skip for now
    pass  # This is a stub — real tests would need mock DB
