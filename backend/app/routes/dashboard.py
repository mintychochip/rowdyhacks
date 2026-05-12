"""Organizer dashboard routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import require_organizer
from app.database import get_db
from app.models import Submission

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
async def get_dashboard(
    hackathon_id: str | None = Query(None),
    status: str | None = Query(None),
    verdict: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_organizer),
):
    """Get paginated submissions list. Organizer only.

    Behavior:
    1. Build a filtered count query based on optional hackathon_id, status, and verdict.
    2. Execute count to get total.
    3. Build the submissions query with the same filters, ordered by risk_score descending.
    4. Apply pagination offset and limit.
    5. Return submissions list, page, per_page, and total count.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.models.Submission, app.clerk_auth.require_organizer.
    Consumers: GET /api/dashboard, organizer submissions review.
    """
    query = select(Submission)
    count_query = select(func.count(Submission.id))

    if hackathon_id:
        query = query.where(Submission.hackathon_id == hackathon_id)
        count_query = count_query.where(Submission.hackathon_id == hackathon_id)
    if status:
        query = query.where(Submission.status == status)
        count_query = count_query.where(Submission.status == status)
    if verdict:
        query = query.where(Submission.verdict == verdict)
        count_query = count_query.where(Submission.verdict == verdict)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(Submission.risk_score.desc().nullslast())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    submissions = result.scalars().all()

    return {
        "submissions": [
            {
                "id": str(s.id),
                "devpost_url": s.devpost_url,
                "project_title": s.project_title,
                "status": s.status.value if s.status else None,
                "risk_score": s.risk_score,
                "verdict": s.verdict.value if s.verdict else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in submissions
        ],
        "page": page,
        "per_page": per_page,
        "total": total,
    }
