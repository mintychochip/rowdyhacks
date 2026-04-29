"""Routes for submitting and retrieving analysis checks."""
import uuid
import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Submission, SubmissionStatus
from app.schemas import SubmitRequest
from app.scraper import is_devpost_url, is_github_url
from app.auth import create_anonymous_token
from app.analyzer import analyze_submission
from app.checks import WEIGHTS

router = APIRouter(prefix="/api/check", tags=["checks"])

# Rate limiting
_rate_limit_store: dict[str, list[float]] = {}
RATE_LIMIT = 10  # requests per minute
RATE_WINDOW = 60  # seconds


def _check_rate_limit(client_ip: str) -> bool:
    now = datetime.now(timezone.utc).timestamp()
    if client_ip not in _rate_limit_store:
        _rate_limit_store[client_ip] = []
    # Clean old entries
    _rate_limit_store[client_ip] = [t for t in _rate_limit_store[client_ip] if now - t < RATE_WINDOW]
    if len(_rate_limit_store[client_ip]) >= RATE_LIMIT:
        return False
    _rate_limit_store[client_ip].append(now)
    return True


def _extract_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "127.0.0.1"


@router.post("", status_code=201)
async def submit_for_check(
    body: SubmitRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Submit a Devpost or GitHub URL for analysis."""
    # Rate limit
    client_ip = _extract_client_ip(request)
    if not _check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")

    # Validate URL
    if not is_devpost_url(body.url) and not is_github_url(body.url):
        raise HTTPException(status_code=400, detail="Invalid URL. Must be a Devpost or GitHub URL.")

    # Create submission (always re-analyze)
    access_token = create_anonymous_token()
    sub = Submission(
        devpost_url=body.url,
        status=SubmissionStatus.pending,
        access_token=access_token,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)

    # Trigger analysis in background
    asyncio.create_task(analyze_submission(sub.id))

    return {"id": str(sub.id), "access_token": access_token, "status": "pending"}


@router.get("/{submission_id}")
async def get_check_status(
    submission_id: uuid.UUID,
    request: Request,
    token: str | None = None,
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Get submission status and check results."""
    result = await db.execute(
        select(Submission).where(Submission.id == submission_id).options(selectinload(Submission.check_results))
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Auth: anonymous token (query param) or Bearer JWT
    resolved_token = token or request.query_params.get("token")
    if not resolved_token and authorization:
        if authorization.startswith("Bearer "):
            resolved_token = authorization.removeprefix("Bearer ")

    # Token validation skipped for MVP — results are publicly accessible by ID

    return {
        "id": str(sub.id),
        "devpost_url": sub.devpost_url,
        "github_url": sub.github_url,
        "project_title": sub.project_title,
        "status": sub.status.value,
        "stage": sub.stage,
        "risk_score": sub.risk_score,
        "verdict": sub.verdict.value if sub.verdict else None,
        "created_at": sub.created_at.isoformat(),
        "completed_at": sub.completed_at.isoformat() if sub.completed_at else None,
        "check_results": [
            {
                "id": str(cr.id),
                "check_category": cr.check_category,
                "check_name": cr.check_name,
                "score": cr.score,
                "status": cr.status,
                "details": cr.details,
                "evidence": cr.evidence,
            }
            for cr in (sub.check_results or [])
        ],
    }


@router.get("/{submission_id}/report")
async def get_check_report(
    submission_id: uuid.UUID,
    token: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get full report JSON for a submission."""
    result = await db.execute(
        select(Submission).where(Submission.id == submission_id).options(selectinload(Submission.check_results))
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    if sub.access_token and sub.access_token != token:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "submission": {
            "id": str(sub.id),
            "devpost_url": sub.devpost_url,
            "github_url": sub.github_url,
            "project_title": sub.project_title,
            "project_description": sub.project_description,
            "claimed_tech": sub.claimed_tech,
            "team_members": sub.team_members,
            "status": sub.status.value,
            "risk_score": sub.risk_score,
            "verdict": sub.verdict.value if sub.verdict else None,
        },
        "check_results": [
            {
                "check_category": cr.check_category,
                "check_name": cr.check_name,
                "score": cr.score,
                "status": cr.status,
                "details": cr.details,
                "evidence": cr.evidence,
            }
            for cr in (sub.check_results or [])
        ],
        "weights": WEIGHTS,
    }


@router.post("/{submission_id}/retry")
async def retry_check(
    submission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retry a failed submission."""
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Delete old check results
    from app.models import CheckResultModel
    from sqlalchemy import delete as sqla_delete
    await db.execute(sqla_delete(CheckResultModel).where(CheckResultModel.submission_id == submission_id))

    sub.status = SubmissionStatus.pending
    sub.risk_score = None
    sub.verdict = None
    sub.completed_at = None
    await db.commit()

    asyncio.create_task(analyze_submission(sub.id))
    return {"id": str(sub.id), "status": "pending"}
