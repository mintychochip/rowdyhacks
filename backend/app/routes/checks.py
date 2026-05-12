"""Routes for submitting and retrieving analysis checks."""

import asyncio
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import is_clerk_token, decode_clerk_token, extract_clerk_user_id
from app.database import get_db
from app.models import Hackathon
from app.schemas import SubmitRequest
from app.scraper import is_devpost_url, is_github_url
from app.services.submission_service import SubmissionService

router = APIRouter(prefix="/api/check", tags=["checks"])

submission_service = SubmissionService()

# Rate limiting
_rate_limit_store: dict[str, list[float]] = {}
RATE_LIMIT = 10  # requests per minute
RATE_WINDOW = 60  # seconds


def _check_rate_limit(client_ip: str) -> bool:
    """Check if the client IP is within the rate limit window.

    Behavior:
    1. Get the current UTC timestamp.
    2. Initialize the client's request list if not present.
    3. Remove entries older than the configured RATE_WINDOW.
    4. Return False if the request count exceeds RATE_LIMIT.
    5. Otherwise append the current timestamp and return True.

    Raises: None
    Side Effects: Mutates the in-memory _rate_limit_store dict.
    Dependencies: None
    Consumers: Internal helper used by submit_for_check.
    """
    now = datetime.now(UTC).timestamp()
    if client_ip not in _rate_limit_store:
        _rate_limit_store[client_ip] = []
    # Clean old entries
    _rate_limit_store[client_ip] = [t for t in _rate_limit_store[client_ip] if now - t < RATE_WINDOW]
    if len(_rate_limit_store[client_ip]) >= RATE_LIMIT:
        return False
    _rate_limit_store[client_ip].append(now)
    return True


def _extract_client_ip(request: Request) -> str:
    """Extract the client IP from request headers.

    Behavior:
    1. Check the X-Forwarded-For header for the original client IP.
    2. Fall back to the request client's host attribute.
    3. Default to 127.0.0.1 if no IP can be determined.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: fastapi.Request.
    Consumers: Internal helper used by submit_for_check.
    """
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
    """Submit a Devpost or GitHub URL for automated integrity analysis.

    Behavior:
    1. Extract client IP and enforce rate limiting (10/min).
    2. Validate the URL is a Devpost or GitHub link.
    3. Auto-link to the existing hackathon if none specified.
    4. Create a pending Submission with an anonymous access token.
    5. Persist the submission to the database.
    6. Trigger background analysis via SubmissionService.analyze_submission.

    Raises: HTTPException(429) if rate limited, HTTPException(400) if URL invalid.
    Side Effects: Inserts Submission row; spawns background asyncio task.
    Dependencies: app.services.submission_service.SubmissionService, app.scraper.is_devpost_url, app.scraper.is_github_url.
    Consumers: POST /api/check, public submission form.
    """
    # Rate limit
    client_ip = _extract_client_ip(request)
    if not _check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")

    # Validate URL
    if not is_devpost_url(body.url) and not is_github_url(body.url):
        raise HTTPException(status_code=400, detail="Invalid URL. Must be a Devpost or GitHub URL.")

    # Auto-link to existing hackathon if none specified
    if not body.hackathon_id:
        existing = await db.execute(select(Hackathon).limit(1))
        hk = existing.scalar_one_or_none()
        hackathon_id = hk.id if hk else None
    else:
        hackathon_id = body.hackathon_id

    sub = await submission_service.create_submission(db, url=body.url, hackathon_id=hackathon_id)

    # Trigger analysis in background
    asyncio.create_task(submission_service.analyze_submission(sub.id))

    from app.services.event_service import publish_event

    await publish_event(
        db,
        "submission.submitted",
        {"submission_id": str(sub.id), "hackathon_id": str(hackathon_id), "url": body.url},
    )

    return {"id": str(sub.id), "access_token": sub.access_token, "status": "pending"}


@router.get("/{submission_id}")
async def get_check_status(
    submission_id: uuid.UUID,
    request: Request,
    token: str | None = None,
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Get submission status, metadata, and all check results.

    Behavior:
    1. Load the submission with eager-loaded check_results.
    2. Return 404 if the submission does not exist.
    3. Return the submission state including progress, risk score, verdict, and detailed check results.

    Raises: HTTPException(404) if submission not found.
    Side Effects: None (read-only).
    Dependencies: app.services.submission_service.SubmissionService.
    Consumers: GET /api/check/{submission_id}, status polling UI.
    """
    sub = await submission_service.get_submission(db, submission_id)
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
        "check_progress": sub.check_progress,
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
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Get full analysis report JSON for a submission.

    Behavior:
    1. Load the submission with eager-loaded check_results.
    2. Return 404 if the submission does not exist.
    3. Determine if the requester is an organizer via Clerk JWT.
    4. Enforce access control (organizer bypass, token match, or public if no token set).
    5. Return submission metadata, check results, and scoring weights.

    Raises: HTTPException(404) if submission not found, HTTPException(403) if access denied.
    Side Effects: None (read-only).
    Dependencies: app.clerk_auth.is_clerk_token, app.clerk_auth.decode_clerk_token, app.models.Submission, app.models.User, app.services.submission_service.SubmissionService.
    Consumers: GET /api/check/{submission_id}/report, report viewer.
    """
    report = await submission_service.get_submission_report(db, submission_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    sub = await submission_service.get_submission(db, submission_id)

    # Check if user is organizer (bypasses token check)
    is_organizer = False
    if authorization and authorization.startswith("Bearer "):
        jwt_token = authorization.removeprefix("Bearer ")
        if is_clerk_token(jwt_token):
            try:
                payload = await decode_clerk_token(jwt_token)
                user_id = extract_clerk_user_id(payload)
                if user_id:
                    from app.models import User

                    result = await db.execute(select(User).where(User.id == user_id))
                    user = result.scalar_one_or_none()
                    if user and user.role.value == "organizer":
                        is_organizer = True
            except Exception:
                pass

    # Token check (skip if organizer)
    if not is_organizer and sub.access_token and sub.access_token != token:
        raise HTTPException(status_code=403, detail="Access denied")

    return report


@router.post("/{submission_id}/retry")
async def retry_check(
    submission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retry analysis for a failed or completed submission.

    Behavior:
    1. Load the submission by ID; 404 if not found.
    2. Delete all existing CheckResult rows for the submission.
    3. Reset submission status to pending and clear risk_score, verdict, completed_at, stage, and check_progress.
    4. Commit the reset.
    5. Trigger a new background analysis task.

    Raises: HTTPException(404) if submission not found.
    Side Effects: Deletes CheckResult rows; mutates Submission fields; spawns background asyncio task.
    Dependencies: app.services.submission_service.SubmissionService.
    Consumers: POST /api/check/{submission_id}/retry, organizer dashboard.
    """
    sub = await submission_service.reset_submission(db, submission_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    asyncio.create_task(submission_service.analyze_submission(sub.id))
    return {"id": str(sub.id), "status": "pending"}
