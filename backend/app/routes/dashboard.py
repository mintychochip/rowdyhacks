"""Organizer dashboard routes."""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Submission, Hackathon, CheckResultModel, SubmissionStatus, Verdict, User, UserRole
from app.auth import decode_token

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


async def _get_organizer(db: AsyncSession, authorization: str | None = Header(alias="Authorization")):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401)
    try:
        payload = decode_token(authorization.removeprefix("Bearer "))
    except ValueError:
        raise HTTPException(status_code=401)
    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user or user.role != UserRole.organizer:
        raise HTTPException(status_code=403, detail="Organizer role required")
    return user


@router.get("")
async def get_dashboard(
    hackathon_id: str | None = Query(None),
    status: str | None = Query(None),
    verdict: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(_get_organizer),
):
    """Get paginated submissions list. Organizer only (auth check in main.py)."""
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
