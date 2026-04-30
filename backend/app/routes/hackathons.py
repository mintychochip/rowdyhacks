"""Hackathon management routes."""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Hackathon, Submission, SubmissionStatus, Verdict
from app.schemas import HackathonCreate
from app.checks.similarity import run_similarity

router = APIRouter(prefix="/api/hackathons", tags=["hackathons"])


@router.post("", status_code=201)
async def create_hackathon(body: HackathonCreate, db: AsyncSession = Depends(get_db)):
    """Create a new hackathon."""
    hackathon = Hackathon(
        name=body.name,
        start_date=body.start_date,
        end_date=body.end_date,
        organizer_id=uuid.uuid4(),  # TODO: use real user from auth
    )
    db.add(hackathon)
    await db.commit()
    await db.refresh(hackathon)
    return {"id": str(hackathon.id), "name": hackathon.name, "start_date": hackathon.start_date.isoformat(), "end_date": hackathon.end_date.isoformat()}


@router.get("")
async def list_hackathons(db: AsyncSession = Depends(get_db)):
    """List all hackathons."""
    result = await db.execute(select(Hackathon).order_by(Hackathon.created_at.desc()))
    hackathons = result.scalars().all()
    return [{"id": str(h.id), "name": h.name, "start_date": h.start_date.isoformat(), "end_date": h.end_date.isoformat()} for h in hackathons]


@router.get("/{hackathon_id}")
async def get_hackathon(hackathon_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get a single hackathon by ID."""
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    return {
        "id": str(hackathon.id),
        "name": hackathon.name,
        "start_date": hackathon.start_date.isoformat(),
        "end_date": hackathon.end_date.isoformat(),
        "organizer_id": str(hackathon.organizer_id),
        "created_at": hackathon.created_at.isoformat(),
        "description": hackathon.description,
        "schedule": hackathon.schedule,
        "wifi_ssid": hackathon.wifi_ssid,
        "wifi_password": hackathon.wifi_password,
        "discord_invite_url": hackathon.discord_invite_url,
        "discord_webhook_url": hackathon.discord_webhook_url,
    }


@router.get("/{hackathon_id}/stats")
async def get_hackathon_stats(hackathon_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get aggregate stats for a hackathon."""
    result = await db.execute(select(Submission).where(Submission.hackathon_id == hackathon_id))
    subs = result.scalars().all()

    total = len(subs)
    completed = [s for s in subs if s.status == SubmissionStatus.completed]
    avg_risk = sum(s.risk_score or 0 for s in completed) / len(completed) if completed else 0
    clean = sum(1 for s in completed if s.verdict == Verdict.clean)
    review = sum(1 for s in completed if s.verdict == Verdict.review)
    flagged = sum(1 for s in completed if s.verdict == Verdict.flagged)

    return {
        "total_submissions": total,
        "completed": len(completed),
        "avg_risk_score": round(avg_risk, 1),
        "by_verdict": {"clean": clean, "review": review, "flagged": flagged},
    }


@router.get("/{hackathon_id}/submissions")
async def get_hackathon_submissions(hackathon_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """List submissions for a hackathon."""
    result = await db.execute(
        select(Submission).where(Submission.hackathon_id == hackathon_id)
    )
    subs = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "project_title": s.project_title,
            "devpost_url": s.devpost_url,
            "github_url": s.github_url,
            "team_members": s.team_members,
            "risk_score": s.risk_score,
            "verdict": s.verdict.value if s.verdict else None,
        }
        for s in subs
    ]


@router.put("/{hackathon_id}")
async def update_hackathon(hackathon_id: uuid.UUID, body: dict, db: AsyncSession = Depends(get_db)):
    """Update hackathon settings (schedule, wifi, discord, webhook)."""
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    updated = []
    for key in ("description", "schedule", "wifi_ssid", "wifi_password", "discord_invite_url", "discord_webhook_url", "discord_application_channel_id"):
        if key in body and body[key] is not None:
            setattr(hackathon, key, body[key])
            updated.append(key)

    if updated:
        await db.commit()

    return {"id": str(hackathon_id), "updated": updated}


@router.post("/{hackathon_id}/similarity", status_code=200)
async def run_hackathon_similarity(hackathon_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Run cross-team similarity checks for all completed submissions.

    Detects duplicate GitHub URLs, same repo name patterns, and overlapping
    commit hashes. Stores results in the database and updates risk scores /
    verdicts on flagged submissions.
    """
    # Verify the hackathon exists
    hk_result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = hk_result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    # Run the batch check (manages its own DB session)
    summary = await run_similarity(hackathon_id)
    return summary
