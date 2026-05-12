"""Tests for SubmissionService."""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CheckResultModel, Submission, SubmissionStatus, Verdict
from app.services.submission_service import SubmissionService


@pytest.mark.anyio
async def test_create_submission(db_session: AsyncSession):
    """create_submission must insert a pending Submission with an access_token."""
    service = SubmissionService()
    sub = await service.create_submission(
        db=db_session,
        url="https://devpost.com/software/test-submission",
        hackathon_id=None,
    )

    assert sub.id is not None
    assert sub.devpost_url == "https://devpost.com/software/test-submission"
    assert sub.status == SubmissionStatus.pending
    assert sub.access_token is not None
    assert len(sub.access_token) > 0

    fetched = await db_session.execute(select(Submission).where(Submission.id == sub.id))
    row = fetched.scalar_one_or_none()
    assert row is not None
    assert row.devpost_url == sub.devpost_url


@pytest.mark.anyio
async def test_get_submission_with_results(db_session: AsyncSession):
    """get_submission must eagerly load check_results."""
    service = SubmissionService()
    sub = await service.create_submission(db_session, "https://devpost.com/software/x", hackathon_id=None)
    await db_session.commit()

    # Add a check result
    cr = CheckResultModel(
        submission_id=sub.id,
        check_category="test",
        check_name="dummy_check",
        score=50,
        status="pass",
    )
    db_session.add(cr)
    await db_session.commit()

    fetched = await service.get_submission(db_session, sub.id)
    assert fetched is not None
    assert fetched.id == sub.id
    assert len(fetched.check_results) == 1
    assert fetched.check_results[0].check_name == "dummy_check"


@pytest.mark.anyio
async def test_get_submission_missing(db_session: AsyncSession):
    """get_submission must return None for a missing ID."""
    service = SubmissionService()
    result = await service.get_submission(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.anyio
async def test_reset_submission(db_session: AsyncSession):
    """reset_submission must clear scoring fields and delete check results."""
    service = SubmissionService()
    sub = await service.create_submission(db_session, "https://devpost.com/software/y", hackathon_id=None)
    sub.status = SubmissionStatus.completed
    sub.risk_score = 75
    sub.verdict = Verdict.flagged
    await db_session.commit()

    cr = CheckResultModel(
        submission_id=sub.id,
        check_category="test",
        check_name="dummy_check",
        score=50,
        status="pass",
    )
    db_session.add(cr)
    await db_session.commit()

    reset = await service.reset_submission(db_session, sub.id)
    assert reset is not None
    assert reset.status == SubmissionStatus.pending
    assert reset.risk_score is None
    assert reset.verdict is None
    assert reset.completed_at is None
    assert reset.stage is None
    assert reset.check_progress is None

    # Verify check results deleted
    result = await db_session.execute(select(CheckResultModel).where(CheckResultModel.submission_id == sub.id))
    assert result.scalar_one_or_none() is None


@pytest.mark.anyio
async def test_reset_submission_missing(db_session: AsyncSession):
    """reset_submission must return None for a missing ID."""
    service = SubmissionService()
    result = await service.reset_submission(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.anyio
async def test_get_submission_report(db_session: AsyncSession):
    """get_submission_report must build a report dict with weights."""
    service = SubmissionService()
    sub = await service.create_submission(db_session, "https://devpost.com/software/z", hackathon_id=None)
    sub.status = SubmissionStatus.completed
    sub.risk_score = 30
    sub.verdict = Verdict.clean
    await db_session.commit()

    cr = CheckResultModel(
        submission_id=sub.id,
        check_category="similarity",
        check_name="code_similarity",
        score=20,
        status="pass",
    )
    db_session.add(cr)
    await db_session.commit()

    report = await service.get_submission_report(db_session, sub.id)
    assert report is not None
    assert report["submission"]["id"] == str(sub.id)
    assert report["submission"]["risk_score"] == 30
    assert report["submission"]["verdict"] == "clean"
    assert len(report["check_results"]) == 1
    assert report["check_results"][0]["check_name"] == "code_similarity"
    assert "weights" in report


@pytest.mark.anyio
async def test_get_submission_report_missing(db_session: AsyncSession):
    """get_submission_report must return None for a missing ID."""
    service = SubmissionService()
    report = await service.get_submission_report(db_session, uuid.uuid4())
    assert report is None
