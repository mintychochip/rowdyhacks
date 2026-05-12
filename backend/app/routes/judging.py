"""Judging routes: thin HTTP wrappers around JudgingService.

All business logic lives in app.services.judging_service. Routes handle
only auth, request validation, exception translation, and response formatting.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import require_organizer
from app.database import get_db
from app.schemas import JudgingSessionCreate, SubmitScoreRequest
from app.services.judging_service import JudgingService

router = APIRouter(prefix="/api", tags=["judging"])

# Shared service instance (stateless)
_judging_service = JudgingService()


def _handle_service_error(exc: Exception) -> None:
    """Translate domain exceptions from JudgingService into HTTPExceptions.

    Behavior:
    1. ValueError -> HTTPException(404 or 422 or 400 depending on message content).
    2. PermissionError -> HTTPException(403).
    3. Re-raise any other exception as a 500.

    This helper centralizes exception mapping so route handlers stay thin.
    """
    if isinstance(exc, PermissionError):
        raise HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, ValueError):
        msg = str(exc).lower()
        if "not found" in msg or "no judging session" in msg or "no rubric" in msg:
            raise HTTPException(status_code=404, detail=str(exc))
        if "already completed" in msg:
            raise HTTPException(status_code=400, detail=str(exc))
        raise HTTPException(status_code=422, detail=str(exc))
    raise exc


@router.post("/hackathons/{hackathon_id}/judging/session", status_code=201)
async def create_judging_session(
    hackathon_id: uuid.UUID,
    body: JudgingSessionCreate,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_organizer),
):
    """Create or replace a judging session with rubric criteria (organizer only)."""
    try:
        return await _judging_service.create_or_replace_session(db, hackathon_id, body)
    except (ValueError, PermissionError) as exc:
        _handle_service_error(exc)


@router.get("/hackathons/{hackathon_id}/judging/session")
async def get_judging_session_route(
    hackathon_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get the judging session configuration for a hackathon."""
    try:
        session = await _judging_service.get_session(db, hackathon_id)
        if not session:
            raise ValueError("No judging session configured for this hackathon")
        return _judging_service._session_detail(session, session.rubric)
    except (ValueError, PermissionError) as exc:
        _handle_service_error(exc)


@router.post("/hackathons/{hackathon_id}/judging/assign", status_code=201)
async def assign_judges(
    hackathon_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """Assign judges to submissions for a hackathon judging session."""
    try:
        judge_ids = [uuid.UUID(j) for j in body.get("judge_ids", [])]
        submission_ids = [uuid.UUID(s) for s in body.get("submission_ids", [])]
        return await _judging_service.assign_judges(db, hackathon_id, judge_ids, submission_ids)
    except (ValueError, PermissionError) as exc:
        _handle_service_error(exc)


@router.get("/hackathons/{hackathon_id}/judging/assignments")
async def list_judge_assignments(
    hackathon_id: uuid.UUID,
    judge_id: str | None = None,
    include_completed: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """List judge assignments for a hackathon judging session."""
    try:
        return await _judging_service.list_assignments(db, hackathon_id, judge_id, include_completed)
    except (ValueError, PermissionError) as exc:
        _handle_service_error(exc)


@router.get("/judging/assignments/{assignment_id}")
async def get_assignment_detail(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get full assignment detail including submission info, rubric criteria, and existing scores."""
    try:
        return await _judging_service.get_assignment_detail(db, assignment_id)
    except (ValueError, PermissionError) as exc:
        _handle_service_error(exc)


@router.post("/judging/assignments/{assignment_id}/open")
async def open_assignment(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Mark a judge assignment as opened and initialize blank score records."""
    try:
        return await _judging_service.open_assignment(db, assignment_id)
    except (ValueError, PermissionError) as exc:
        _handle_service_error(exc)


@router.post("/judging/assignments/{assignment_id}/score")
async def submit_scores(
    assignment_id: uuid.UUID,
    body: SubmitScoreRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit or update scores for a judge assignment."""
    try:
        scores_data = [{"criterion_id": s.criterion_id, "score": s.score} for s in body.scores]
        return await _judging_service.submit_scores(db, assignment_id, scores_data)
    except (ValueError, PermissionError) as exc:
        _handle_service_error(exc)


@router.get("/hackathons/{hackathon_id}/judging/results")
async def get_judging_results(
    hackathon_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Compute and return ELO rankings for a hackathon."""
    try:
        return await _judging_service.compute_results(db, hackathon_id)
    except (ValueError, PermissionError) as exc:
        _handle_service_error(exc)


@router.get("/hackathons/{hackathon_id}/judging/queue")
async def get_judging_queue(
    hackathon_id: uuid.UUID,
    judge_id: str,
    min_judges: int = 3,
    db: AsyncSession = Depends(get_db),
):
    """Return a priority-ordered list of submissions that need more judging."""
    try:
        return await _judging_service.get_queue(db, hackathon_id, judge_id, min_judges)
    except (ValueError, PermissionError) as exc:
        _handle_service_error(exc)


@router.post("/hackathons/{hackathon_id}/judging/rerun")
async def rerun_judging(
    hackathon_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Create new assignments for projects flagged by the ELO uncertainty engine."""
    try:
        return await _judging_service.rerun_judging(db, hackathon_id)
    except (ValueError, PermissionError) as exc:
        _handle_service_error(exc)


@router.post("/hackathons/{hackathon_id}/judging/activate")
async def activate_judging(
    hackathon_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Activate a judging session and auto-assign all judges to completed submissions."""
    try:
        return await _judging_service.activate_session(db, hackathon_id)
    except (ValueError, PermissionError) as exc:
        _handle_service_error(exc)


@router.post("/hackathons/{hackathon_id}/judging/close")
async def close_judging(
    hackathon_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Manually close a judging session to prevent further scoring."""
    try:
        return await _judging_service.close_session(db, hackathon_id)
    except (ValueError, PermissionError) as exc:
        _handle_service_error(exc)
