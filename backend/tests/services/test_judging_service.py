"""Tests for JudgingService."""

import asyncio
import math
import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Hackathon,
    JudgeAssignment,
    JudgeRating,
    JudgingSession,
    JudgingSessionStatus,
    Rubric,
    RubricCriterion,
    Score,
    Submission,
    SubmissionStatus,
    User,
    UserRole,
)
from app.schemas import JudgingSessionCreate
from app.services.judging_service import JudgingService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def hackathon_and_organizer(db_session: AsyncSession):
    """Create a hackathon and an organizer user."""
    uid = uuid.uuid4().hex[:8]
    organizer = User(
        id=f"org-{uid}",
        email=f"org-{uid}@example.com",
        name="Test Organizer",
        role=UserRole.organizer,
    )
    db_session.add(organizer)

    now = datetime.now(UTC)
    hackathon = Hackathon(
        name=f"Test Hack {uid}",
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=1),
        organizer_id=organizer.id,
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)
    return hackathon, organizer


@pytest_asyncio.fixture
async def judge(db_session: AsyncSession):
    """Create a single judge user."""
    uid = uuid.uuid4().hex[:8]
    user = User(
        id=f"judge-{uid}",
        email=f"judge-{uid}@example.com",
        name="Test Judge",
        role=UserRole.judge,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def completed_submission(db_session: AsyncSession, hackathon_and_organizer):
    """Create a completed submission for the hackathon."""
    hackathon, _ = hackathon_and_organizer
    sub = Submission(
        devpost_url="https://devpost.com/test",
        project_title="Test Project",
        hackathon_id=hackathon.id,
        status=SubmissionStatus.completed,
        risk_score=20,
    )
    db_session.add(sub)
    await db_session.commit()
    await db_session.refresh(sub)
    return sub


@pytest_asyncio.fixture
async def session_with_rubric(db_session: AsyncSession, hackathon_and_organizer):
    """Create a judging session with a single-criterion rubric for the hackathon."""
    hackathon, _ = hackathon_and_organizer
    now = datetime.now(UTC)
    session = JudgingSession(
        hackathon_id=hackathon.id,
        start_time=now - timedelta(hours=1),
        end_time=now + timedelta(hours=2),
        per_project_seconds=300,
        leaderboard_public=False,
        status=JudgingSessionStatus.active,
    )
    db_session.add(session)
    await db_session.flush()

    rubric = Rubric(session_id=session.id, name="Test Rubric")
    db_session.add(rubric)
    await db_session.flush()

    criterion = RubricCriterion(
        rubric_id=rubric.id,
        name="Innovation",
        description="Originality",
        max_score=10,
        weight=100,
        sort_order=0,
    )
    db_session.add(criterion)
    await db_session.commit()
    await db_session.refresh(session)
    return session, rubric, [criterion]


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_session_success(db_session: AsyncSession, hackathon_and_organizer):
    """create_or_replace_session must create a session, rubric, and criteria."""
    hackathon, _ = hackathon_and_organizer
    service = JudgingService()

    body = JudgingSessionCreate(
        start_time=datetime.now(UTC) - timedelta(hours=1),
        end_time=datetime.now(UTC) + timedelta(hours=2),
        per_project_seconds=300,
        criteria=[{"name": "A", "description": "Desc", "max_score": 10, "weight": 100, "sort_order": 0}],
    )
    detail = await service.create_or_replace_session(db_session, hackathon.id, body)

    assert detail["hackathon_id"] == str(hackathon.id)
    assert detail["status"] == "pending"
    assert detail["rubric"] is not None
    assert len(detail["rubric"]["criteria"]) == 1
    assert detail["rubric"]["criteria"][0]["name"] == "A"


@pytest.mark.anyio
async def test_create_session_rejects_bad_weights(db_session: AsyncSession, hackathon_and_organizer):
    """create_or_replace_session must raise ValueError when weights do not sum to 100."""
    hackathon, _ = hackathon_and_organizer
    service = JudgingService()

    body = JudgingSessionCreate(
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC) + timedelta(hours=2),
        criteria=[
            {"name": "A", "max_score": 10, "weight": 40},
            {"name": "B", "max_score": 10, "weight": 40},
        ],
    )
    with pytest.raises(ValueError, match="100"):
        await service.create_or_replace_session(db_session, hackathon.id, body)


@pytest.mark.anyio
async def test_create_session_rejects_missing_hackathon(db_session: AsyncSession):
    """create_or_replace_session must raise ValueError for a non-existent hackathon."""
    service = JudgingService()
    body = JudgingSessionCreate(
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC) + timedelta(hours=2),
        criteria=[{"name": "A", "max_score": 10, "weight": 100}],
    )
    with pytest.raises(ValueError, match="Hackathon not found"):
        await service.create_or_replace_session(db_session, uuid.uuid4(), body)


@pytest.mark.anyio
async def test_get_session_returns_none(db_session: AsyncSession):
    """get_session must return None when no session exists."""
    service = JudgingService()
    result = await service.get_session(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.anyio
async def test_close_session_success(db_session: AsyncSession, session_with_rubric):
    """close_session must set status to closed."""
    session, _, _ = session_with_rubric
    service = JudgingService()
    result = await service.close_session(db_session, session.hackathon_id)
    assert result["status"] == "closed"

    refreshed = await db_session.get(JudgingSession, session.id)
    assert refreshed.status == JudgingSessionStatus.closed


@pytest.mark.anyio
async def test_close_session_not_found(db_session: AsyncSession):
    """close_session must raise ValueError when no session exists."""
    service = JudgingService()
    with pytest.raises(ValueError, match="No judging session"):
        await service.close_session(db_session, uuid.uuid4())


# ---------------------------------------------------------------------------
# Judge assignment
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_assign_judges_success(
    db_session: AsyncSession,
    session_with_rubric,
    judge,
    completed_submission,
):
    """assign_judges must create JudgeAssignment rows."""
    session, _, _ = session_with_rubric
    service = JudgingService()

    result = await service.assign_judges(
        db_session,
        session.hackathon_id,
        [judge.id],
        [completed_submission.id],
    )
    assert result["assigned"] == 1
    assert result["judges"] == 1
    assert result["submissions"] == 1

    rows = await db_session.execute(select(JudgeAssignment).where(JudgeAssignment.session_id == session.id))
    assignments = rows.scalars().all()
    assert len(assignments) == 1
    assert str(assignments[0].judge_id) == str(judge.id)

    # JudgeRating should be created
    rating_rows = await db_session.execute(
        select(JudgeRating).where(
            JudgeRating.judge_id == judge.id,
            JudgeRating.hackathon_id == session.hackathon_id,
        )
    )
    assert rating_rows.scalar_one_or_none() is not None


@pytest.mark.anyio
async def test_assign_judges_rejects_empty_ids(db_session: AsyncSession, session_with_rubric):
    """assign_judges must raise ValueError when judge_ids or submission_ids are empty."""
    session, _, _ = session_with_rubric
    service = JudgingService()
    with pytest.raises(ValueError, match="required"):
        await service.assign_judges(db_session, session.hackathon_id, [], [uuid.uuid4()])
    with pytest.raises(ValueError, match="required"):
        await service.assign_judges(db_session, session.hackathon_id, [uuid.uuid4()], [])


@pytest.mark.anyio
async def test_assign_judges_rejects_invalid_submissions(db_session: AsyncSession, session_with_rubric, judge):
    """assign_judges must raise ValueError for submissions not in the hackathon."""
    session, _, _ = session_with_rubric
    service = JudgingService()
    with pytest.raises(ValueError, match="Submissions not in hackathon"):
        await service.assign_judges(db_session, session.hackathon_id, [judge.id], [uuid.uuid4()])


@pytest.mark.anyio
async def test_list_assignments(db_session: AsyncSession, session_with_rubric, judge, completed_submission):
    """list_assignments must return serialized assignment rows."""
    session, _, _ = session_with_rubric
    service = JudgingService()

    await service.assign_judges(db_session, session.hackathon_id, [judge.id], [completed_submission.id])

    assignments = await service.list_assignments(db_session, session.hackathon_id)
    assert len(assignments) == 1
    assert assignments[0]["project_title"] == completed_submission.project_title

    # Filter by judge_id
    filtered = await service.list_assignments(db_session, session.hackathon_id, judge_id=str(judge.id))
    assert len(filtered) == 1

    # Exclude completed
    completed = await service.list_assignments(db_session, session.hackathon_id, include_completed=True)
    assert len(completed) == 1  # not completed yet, so same count


# ---------------------------------------------------------------------------
# Assignment open / detail / score
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_open_assignment_success(
    db_session: AsyncSession,
    session_with_rubric,
    judge,
    completed_submission,
):
    """open_assignment must set opened_at and create blank Score rows."""
    session, _, criteria = session_with_rubric
    service = JudgingService()

    await service.assign_judges(db_session, session.hackathon_id, [judge.id], [completed_submission.id])
    rows = await db_session.execute(select(JudgeAssignment).where(JudgeAssignment.session_id == session.id))
    assignment = rows.scalars().first()

    result = await service.open_assignment(db_session, assignment.id)
    assert result["opened"] is True
    assert result["opened_at"] is not None

    refreshed = await db_session.get(JudgeAssignment, assignment.id)
    assert refreshed.opened_at is not None

    score_rows = await db_session.execute(select(Score).where(Score.assignment_id == assignment.id))
    scores = score_rows.scalars().all()
    assert len(scores) == len(criteria)


@pytest.mark.anyio
async def test_open_assignment_not_found(db_session: AsyncSession):
    """open_assignment must raise ValueError for a missing assignment."""
    service = JudgingService()
    with pytest.raises(ValueError, match="Assignment not found"):
        await service.open_assignment(db_session, uuid.uuid4())


@pytest.mark.anyio
async def test_get_assignment_detail_success(
    db_session: AsyncSession,
    session_with_rubric,
    judge,
    completed_submission,
):
    """get_assignment_detail must return criteria and submission info."""
    session, _, criteria = session_with_rubric
    service = JudgingService()

    await service.assign_judges(db_session, session.hackathon_id, [judge.id], [completed_submission.id])
    rows = await db_session.execute(select(JudgeAssignment).where(JudgeAssignment.session_id == session.id))
    assignment = rows.scalars().first()

    detail = await service.get_assignment_detail(db_session, assignment.id)
    assert detail["submission"]["project_title"] == completed_submission.project_title
    assert len(detail["criteria"]) == len(criteria)


@pytest.mark.anyio
async def test_get_assignment_detail_enforces_time_window(db_session: AsyncSession, hackathon_and_organizer):
    """get_assignment_detail must raise PermissionError outside the judging window."""
    hackathon, _ = hackathon_and_organizer
    now = datetime.now(UTC)
    # Future session
    session = JudgingSession(
        hackathon_id=hackathon.id,
        start_time=now + timedelta(hours=1),
        end_time=now + timedelta(hours=3),
        per_project_seconds=300,
        status=JudgingSessionStatus.pending,
    )
    db_session.add(session)
    await db_session.flush()

    rubric = Rubric(session_id=session.id, name="R")
    db_session.add(rubric)
    await db_session.flush()

    assignment = JudgeAssignment(session_id=session.id, judge_id="judge-1", submission_id=uuid.uuid4())
    db_session.add(assignment)
    await db_session.commit()

    service = JudgingService()
    with pytest.raises(PermissionError, match="not opened yet"):
        await service.get_assignment_detail(db_session, assignment.id)


@pytest.mark.anyio
async def test_submit_scores_success(
    db_session: AsyncSession,
    session_with_rubric,
    judge,
    completed_submission,
):
    """submit_scores must persist scores and auto-complete when all criteria are scored."""
    session, _, criteria = session_with_rubric
    service = JudgingService()

    await service.assign_judges(db_session, session.hackathon_id, [judge.id], [completed_submission.id])
    rows = await db_session.execute(select(JudgeAssignment).where(JudgeAssignment.session_id == session.id))
    assignment = rows.scalars().first()

    await service.open_assignment(db_session, assignment.id)

    scores_data = [{"criterion_id": str(criteria[0].id), "score": 8}]
    result = await service.submit_scores(db_session, assignment.id, scores_data)
    assert result["is_completed"] is True
    assert result["is_late"] is False

    refreshed = await db_session.get(JudgeAssignment, assignment.id)
    assert refreshed.is_completed == 1
    assert refreshed.submitted_at is not None


@pytest.mark.anyio
async def test_submit_scores_rejects_completed_assignment(
    db_session: AsyncSession,
    session_with_rubric,
    judge,
    completed_submission,
):
    """submit_scores must raise ValueError when assignment is already completed."""
    session, _, criteria = session_with_rubric
    service = JudgingService()

    await service.assign_judges(db_session, session.hackathon_id, [judge.id], [completed_submission.id])
    rows = await db_session.execute(select(JudgeAssignment).where(JudgeAssignment.session_id == session.id))
    assignment = rows.scalars().first()
    assignment.is_completed = 1
    await db_session.commit()

    with pytest.raises(ValueError, match="already completed"):
        await service.submit_scores(db_session, assignment.id, [])


@pytest.mark.anyio
async def test_submit_scores_rejects_unknown_criterion(
    db_session: AsyncSession,
    session_with_rubric,
    judge,
    completed_submission,
):
    """submit_scores must raise ValueError for an unknown criterion_id."""
    session, _, _ = session_with_rubric
    service = JudgingService()

    await service.assign_judges(db_session, session.hackathon_id, [judge.id], [completed_submission.id])
    rows = await db_session.execute(select(JudgeAssignment).where(JudgeAssignment.session_id == session.id))
    assignment = rows.scalars().first()
    await service.open_assignment(db_session, assignment.id)

    with pytest.raises(ValueError, match="Unknown criterion"):
        await service.submit_scores(db_session, assignment.id, [{"criterion_id": str(uuid.uuid4()), "score": 5}])


@pytest.mark.anyio
async def test_submit_scores_rejects_out_of_range(
    db_session: AsyncSession,
    session_with_rubric,
    judge,
    completed_submission,
):
    """submit_scores must raise ValueError when score exceeds max_score."""
    session, _, criteria = session_with_rubric
    service = JudgingService()

    await service.assign_judges(db_session, session.hackathon_id, [judge.id], [completed_submission.id])
    rows = await db_session.execute(select(JudgeAssignment).where(JudgeAssignment.session_id == session.id))
    assignment = rows.scalars().first()
    await service.open_assignment(db_session, assignment.id)

    with pytest.raises(ValueError, match="out of range"):
        await service.submit_scores(db_session, assignment.id, [{"criterion_id": str(criteria[0].id), "score": 15}])


@pytest.mark.anyio
async def test_submit_scores_auto_submit_late(
    db_session: AsyncSession,
    hackathon_and_organizer,
    judge,
    completed_submission,
):
    """submit_scores must auto-submit and mark null scores as 0 when late."""
    hackathon, _ = hackathon_and_organizer
    now = datetime.now(UTC)
    session = JudgingSession(
        hackathon_id=hackathon.id,
        start_time=now - timedelta(hours=1),
        end_time=now + timedelta(hours=1),
        per_project_seconds=1,  # 1 second
        status=JudgingSessionStatus.active,
    )
    db_session.add(session)
    await db_session.flush()

    rubric = Rubric(session_id=session.id, name="R")
    db_session.add(rubric)
    await db_session.flush()

    criterion = RubricCriterion(rubric_id=rubric.id, name="C", max_score=10, weight=100, sort_order=0)
    db_session.add(criterion)
    await db_session.flush()

    assignment = JudgeAssignment(session_id=session.id, judge_id=judge.id, submission_id=completed_submission.id)
    db_session.add(assignment)
    await db_session.commit()

    service = JudgingService()
    await service.open_assignment(db_session, assignment.id)
    await asyncio.sleep(2)

    result = await service.submit_scores(db_session, assignment.id, [{"criterion_id": str(criterion.id), "score": 5}])
    assert result["is_late"] is True
    assert result["is_auto_submitted"] is True

    refreshed = await db_session.get(JudgeAssignment, assignment.id)
    assert refreshed.is_completed == 1


# ---------------------------------------------------------------------------
# Results / ELO
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_compute_results_no_scores(db_session: AsyncSession, session_with_rubric):
    """compute_results must return empty rankings when no scores exist."""
    session, _, _ = session_with_rubric
    service = JudgingService()
    result = await service.compute_results(db_session, session.hackathon_id)
    assert result["rankings"] == []
    assert "error" in result


@pytest.mark.anyio
async def test_compute_results_basic_elo(
    db_session: AsyncSession,
    hackathon_and_organizer,
    completed_submission,
    judge,
):
    """compute_results must produce meaningful ELO rankings after scoring."""
    hackathon, _ = hackathon_and_organizer
    now = datetime.now(UTC)
    session = JudgingSession(
        hackathon_id=hackathon.id,
        start_time=now - timedelta(hours=1),
        end_time=now + timedelta(hours=2),
        per_project_seconds=300,
        status=JudgingSessionStatus.active,
    )
    db_session.add(session)
    await db_session.flush()

    rubric = Rubric(session_id=session.id, name="R")
    db_session.add(rubric)
    await db_session.flush()

    criterion = RubricCriterion(rubric_id=rubric.id, name="C", max_score=10, weight=100, sort_order=0)
    db_session.add(criterion)
    await db_session.flush()

    # Create a second submission so pairwise ELO comparisons can happen
    sub2 = Submission(
        hackathon_id=hackathon.id,
        project_title="Second Project",
        devpost_url="https://devpost.com/second",
        status=SubmissionStatus.completed,
        risk_score=20,
    )
    db_session.add(sub2)
    await db_session.flush()

    a1 = JudgeAssignment(session_id=session.id, judge_id=judge.id, submission_id=completed_submission.id)
    a2 = JudgeAssignment(session_id=session.id, judge_id=judge.id, submission_id=sub2.id)
    db_session.add_all([a1, a2])
    await db_session.commit()

    service = JudgingService()
    for a in [a1, a2]:
        await service.open_assignment(db_session, a.id)

    await service.submit_scores(db_session, a1.id, [{"criterion_id": str(criterion.id), "score": 8}])
    await service.submit_scores(db_session, a2.id, [{"criterion_id": str(criterion.id), "score": 4}])

    result = await service.compute_results(db_session, hackathon.id)
    assert len(result["rankings"]) == 2
    # First submission scored higher, should rank #1
    assert result["rankings"][0]["project_title"] == completed_submission.project_title
    assert result["rankings"][0]["elo"] > 1500
    assert result["rankings"][0]["rank"] == 1
    # Second submission should be below baseline
    assert result["rankings"][1]["project_title"] == "Second Project"
    assert result["rankings"][1]["elo"] < 1500

    assert len(result["judge_stats"]) == 1
    assert result["judge_stats"][0]["mean"] == 60.0  # average of (8/10)*100 and (4/10)*100


@pytest.mark.anyio
async def test_compute_results_elo_corrects_severity(
    db_session: AsyncSession,
    hackathon_and_organizer,
):
    """ELO z-score normalization should resolve harsh vs generous judges."""
    hackathon, _ = hackathon_and_organizer
    now = datetime.now(UTC)
    session = JudgingSession(
        hackathon_id=hackathon.id,
        start_time=now - timedelta(hours=1),
        end_time=now + timedelta(hours=2),
        per_project_seconds=300,
        status=JudgingSessionStatus.active,
    )
    db_session.add(session)
    await db_session.flush()

    rubric = Rubric(session_id=session.id, name="R")
    db_session.add(rubric)
    await db_session.flush()

    criterion = RubricCriterion(rubric_id=rubric.id, name="Overall", max_score=10, weight=100, sort_order=0)
    db_session.add(criterion)
    await db_session.flush()

    # Two judges with opposite severity
    judge_harsh = User(id="harsh", email="h@example.com", name="Harsh", role=UserRole.judge)
    judge_generous = User(id="generous", email="g@example.com", name="Generous", role=UserRole.judge)
    db_session.add_all([judge_harsh, judge_generous])
    await db_session.flush()

    # Three submissions
    sub_a = Submission(
        hackathon_id=hackathon.id,
        project_title="Alpha",
        devpost_url="https://devpost.com/alpha",
        status=SubmissionStatus.completed,
        risk_score=20,
    )
    sub_b = Submission(
        hackathon_id=hackathon.id,
        project_title="Beta",
        devpost_url="https://devpost.com/beta",
        status=SubmissionStatus.completed,
        risk_score=20,
    )
    sub_g = Submission(
        hackathon_id=hackathon.id,
        project_title="Gamma",
        devpost_url="https://devpost.com/gamma",
        status=SubmissionStatus.completed,
        risk_score=20,
    )
    db_session.add_all([sub_a, sub_b, sub_g])
    await db_session.flush()

    service = JudgingService()

    # Assign both judges to all 3 submissions
    for j in [judge_harsh, judge_generous]:
        for s in [sub_a, sub_b, sub_g]:
            assignment = JudgeAssignment(session_id=session.id, judge_id=j.id, submission_id=s.id)
            db_session.add(assignment)
    await db_session.commit()

    # Score: Harsh prefers Alpha(5) > Beta(3) > Gamma(1)
    # Score: Generous prefers Beta(9) > Gamma(8) > Alpha(7)
    # Raw averages tie Alpha and Beta at 6.0 each.
    # Z-scores should push Beta to #1 because Generous's strong preference is preserved.
    scores = {
        (judge_harsh.id, sub_a.id): 5,
        (judge_harsh.id, sub_b.id): 3,
        (judge_harsh.id, sub_g.id): 1,
        (judge_generous.id, sub_a.id): 7,
        (judge_generous.id, sub_b.id): 9,
        (judge_generous.id, sub_g.id): 8,
    }

    for (jid, sid), val in scores.items():
        rows = await db_session.execute(
            select(JudgeAssignment).where(
                JudgeAssignment.session_id == session.id,
                JudgeAssignment.judge_id == jid,
                JudgeAssignment.submission_id == sid,
            )
        )
        a = rows.scalar_one()
        await service.open_assignment(db_session, a.id)
        await service.submit_scores(db_session, a.id, [{"criterion_id": str(criterion.id), "score": val}])

    result = await service.compute_results(db_session, hackathon.id)
    rankings = result["rankings"]
    assert len(rankings) == 3

    # Beta should win because z-score normalization preserves the generous judge's preference signal
    assert rankings[0]["project_title"] == "Beta"
    assert rankings[0]["elo"] > 1500
    assert rankings[2]["project_title"] == "Gamma"

    # Judge stats should reflect severity difference
    stats_by_name = {s["name"]: s for s in result["judge_stats"]}
    assert stats_by_name["Harsh"]["mean"] < stats_by_name["Generous"]["mean"]


# ---------------------------------------------------------------------------
# Queue
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_queue_no_submissions(db_session: AsyncSession, session_with_rubric):
    """get_queue must return empty queue when there are no completed submissions."""
    session, _, _ = session_with_rubric
    service = JudgingService()
    result = await service.get_queue(db_session, session.hackathon_id, "judge-1")
    assert result["queue"] == []


@pytest.mark.anyio
async def test_get_queue_no_scores_yet(
    db_session: AsyncSession,
    session_with_rubric,
    judge,
    completed_submission,
):
    """get_queue must return all submissions when no scores exist yet."""
    session, _, _ = session_with_rubric
    service = JudgingService()
    await service.assign_judges(db_session, session.hackathon_id, [judge.id], [completed_submission.id])

    result = await service.get_queue(db_session, session.hackathon_id, str(judge.id))
    assert len(result["queue"]) == 1
    assert result["queue"][0]["reasons"] == ["needs_coverage"]
    assert result["scored_by_you"] == 0


@pytest.mark.anyio
async def test_get_queue_excludes_already_scored(
    db_session: AsyncSession,
    session_with_rubric,
    judge,
    completed_submission,
):
    """get_queue must exclude submissions already scored by the requesting judge."""
    session, _, criteria = session_with_rubric
    service = JudgingService()
    await service.assign_judges(db_session, session.hackathon_id, [judge.id], [completed_submission.id])

    rows = await db_session.execute(select(JudgeAssignment).where(JudgeAssignment.session_id == session.id))
    assignment = rows.scalars().first()
    await service.open_assignment(db_session, assignment.id)
    await service.submit_scores(db_session, assignment.id, [{"criterion_id": str(criteria[0].id), "score": 8}])

    result = await service.get_queue(db_session, session.hackathon_id, str(judge.id))
    assert len(result["queue"]) == 0
    assert result["scored_by_you"] == 1


# ---------------------------------------------------------------------------
# Activate / Rerun
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_activate_session_auto_assigns(
    db_session: AsyncSession,
    hackathon_and_organizer,
    judge,
    completed_submission,
):
    """activate_session must set status to active and create assignments for all judges x submissions."""
    hackathon, _ = hackathon_and_organizer
    now = datetime.now(UTC)
    session = JudgingSession(
        hackathon_id=hackathon.id,
        start_time=now - timedelta(hours=1),
        end_time=now + timedelta(hours=2),
        per_project_seconds=300,
        status=JudgingSessionStatus.pending,
    )
    db_session.add(session)
    await db_session.flush()

    rubric = Rubric(session_id=session.id, name="R")
    db_session.add(rubric)
    await db_session.commit()

    service = JudgingService()

    # Because the in-memory DB is shared across tests, count actual judges in DB
    judges_result = await db_session.execute(select(User.id).where(User.role == UserRole.judge))
    judge_count = len(judges_result.all())

    result = await service.activate_session(db_session, hackathon.id)
    assert result["status"] == "active"
    assert result["auto_assigned"] == judge_count * 1  # 1 submission
    assert result["judges"] == judge_count
    assert result["submissions"] == 1

    # Second activation should not duplicate
    result2 = await service.activate_session(db_session, hackathon.id)
    assert result2["auto_assigned"] == 0


@pytest.mark.anyio
async def test_rerun_judging_flags_under_scored(
    db_session: AsyncSession,
    hackathon_and_organizer,
    judge,
    completed_submission,
):
    """rerun_judging must flag submissions with fewer than 3 judges and create new assignments."""
    hackathon, _ = hackathon_and_organizer
    now = datetime.now(UTC)
    session = JudgingSession(
        hackathon_id=hackathon.id,
        start_time=now - timedelta(hours=1),
        end_time=now + timedelta(hours=2),
        per_project_seconds=300,
        status=JudgingSessionStatus.active,
    )
    db_session.add(session)
    await db_session.flush()

    rubric = Rubric(session_id=session.id, name="R")
    db_session.add(rubric)
    await db_session.flush()

    criterion = RubricCriterion(rubric_id=rubric.id, name="C", max_score=10, weight=100, sort_order=0)
    db_session.add(criterion)
    await db_session.flush()

    assignment = JudgeAssignment(session_id=session.id, judge_id=judge.id, submission_id=completed_submission.id)
    db_session.add(assignment)
    await db_session.commit()

    # Score once (1 judge < 3)
    service = JudgingService()
    await service.open_assignment(db_session, assignment.id)
    await service.submit_scores(db_session, assignment.id, [{"criterion_id": str(criterion.id), "score": 7}])

    result = await service.rerun_judging(db_session, hackathon.id)
    assert result["flagged_submissions"] >= 1
    assert result["created"] >= 0


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_compute_raw_score():
    """_compute_raw_score must weight scores by criterion weight and max_score."""
    from unittest.mock import MagicMock

    c1 = MagicMock()
    c1.max_score = 10
    c1.weight = 40

    c2 = MagicMock()
    c2.max_score = 5
    c2.weight = 60

    s1 = MagicMock()
    s1.criterion_id = "cid1"
    s1.score = 10

    s2 = MagicMock()
    s2.criterion_id = "cid2"
    s2.score = 5

    criteria_map = {"cid1": c1, "cid2": c2}
    result = JudgingService._compute_raw_score([s1, s2], criteria_map)
    # (10/10)*40 + (5/5)*60 = 100
    assert result == 100.0


def test_elo_update():
    """_elo_update must adjust ratings according to the standard ELO formula."""
    new_a, new_b = JudgingService._elo_update(1500, 1500, 1.0)
    assert new_a > 1500
    assert new_b < 1500

    new_a, new_b = JudgingService._elo_update(1500, 1500, 0.5)
    assert math.isclose(new_a, 1500, abs_tol=0.1)
    assert math.isclose(new_b, 1500, abs_tol=0.1)


def test_expected_score():
    """_expected_score must return 0.5 for equal ratings and approach 1.0 for large gaps."""
    assert math.isclose(JudgingService._expected_score(1500, 1500), 0.5, abs_tol=0.01)
    assert JudgingService._expected_score(2000, 1500) > 0.9
    assert JudgingService._expected_score(1500, 2000) < 0.1
