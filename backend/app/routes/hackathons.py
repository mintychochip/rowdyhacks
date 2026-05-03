"""Hackathon management routes."""

import asyncio
import csv
import io
import re
import uuid
from datetime import UTC, datetime

import httpx
from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import decode_token
from app.cache import cache_delete_pattern, cached
from app.checks.similarity import run_similarity
from app.database import get_db
from app.models import (
    Announcement,
    ConflictOfInterest,
    Hackathon,
    HackathonOrganizer,
    Registration,
    RegistrationStatus,
    Submission,
    SubmissionStatus,
    User,
    UserRole,
    Verdict,
)
from app.routes.tracks import seed_tracks
from app.schemas import (
    AnnouncementCreate,
    AnnouncementResponse,
    ConflictOfInterestCreate,
    ConflictOfInterestResponse,
    HackathonCreate,
)

router = APIRouter(prefix="/api/hackathons", tags=["hackathons"])

HK_CACHE_TTL = 300  # 5 minutes
HK_CACHE_PFX = "hackathons"


def _get_current_user_payload(authorization: str | None):
    """Extract and validate the current user from Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization.removeprefix("Bearer ")
    try:
        return decode_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def _get_current_user(db: AsyncSession, authorization: str | None) -> User:
    """Get the current authenticated user."""
    payload = _get_current_user_payload(authorization)
    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def _ensure_organizer(user: User, hackathon: Hackathon, db: AsyncSession):
    """Verify user is the organizer or a co-organizer of the hackathon."""
    # Primary organizer check
    if user.role == UserRole.organizer and hackathon.organizer_id == user.id:
        return

    # Co-organizer check
    result = await db.execute(
        select(HackathonOrganizer).where(
            and_(HackathonOrganizer.hackathon_id == hackathon.id, HackathonOrganizer.user_id == user.id)
        )
    )
    if result.scalar_one_or_none():
        return

    raise HTTPException(status_code=403, detail="Only the hackathon organizer can perform this action")


@router.post("", status_code=201)
async def create_hackathon(
    body: HackathonCreate, authorization: str = Header(alias="Authorization"), db: AsyncSession = Depends(get_db)
):
    """Create a new hackathon."""
    user = await _get_current_user(db, authorization)
    if user.role != UserRole.organizer:
        raise HTTPException(status_code=403, detail="Only organizers can create hackathons")

    # Only one hackathon per portal
    existing = await db.execute(select(Hackathon).limit(1))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="A hackathon already exists. Only one hackathon is supported.")

    hackathon = Hackathon(
        name=body.name,
        start_date=body.start_date,
        end_date=body.end_date,
        organizer_id=user.id,
        description=body.description,
        application_deadline=body.application_deadline,
        max_participants=body.max_participants,
        waitlist_enabled=body.waitlist_enabled,
        venue_address=body.venue_address,
        parking_info=body.parking_info,
        wifi_ssid=body.wifi_ssid,
        wifi_password=body.wifi_password,
        discord_invite_url=body.discord_invite_url,
        devpost_url=body.devpost_url,
        schedule=body.schedule,
    )
    db.add(hackathon)
    await db.commit()
    await db.refresh(hackathon)

    # Seed default tracks
    for track in seed_tracks(hackathon.id):
        db.add(track)
    await db.commit()

    await _bust_hackathon_list_cache()

    return {
        "id": str(hackathon.id),
        "name": hackathon.name,
        "start_date": hackathon.start_date.isoformat(),
        "end_date": hackathon.end_date.isoformat(),
        "application_deadline": hackathon.application_deadline.isoformat() if hackathon.application_deadline else None,
        "max_participants": hackathon.max_participants,
        "waitlist_enabled": hackathon.waitlist_enabled,
    }


@router.get("")
@cached(ttl_seconds=HK_CACHE_TTL, key_prefix=HK_CACHE_PFX)
async def list_hackathons(db: AsyncSession = Depends(get_db)):
    """List all hackathons."""
    result = await db.execute(select(Hackathon).order_by(Hackathon.created_at.desc()))
    hackathons = result.scalars().all()
    return [
        {
            "id": str(h.id),
            "name": h.name,
            "start_date": h.start_date.isoformat(),
            "end_date": h.end_date.isoformat(),
            "application_deadline": h.application_deadline.isoformat() if h.application_deadline else None,
            "max_participants": h.max_participants,
            "current_participants": h.current_participants,
            "waitlist_enabled": h.waitlist_enabled,
        }
        for h in hackathons
    ]


@router.get("/{hackathon_id}")
@cached(ttl_seconds=HK_CACHE_TTL, key_prefix=HK_CACHE_PFX)
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
        "application_deadline": hackathon.application_deadline.isoformat() if hackathon.application_deadline else None,
        "max_participants": hackathon.max_participants,
        "current_participants": hackathon.current_participants,
        "waitlist_enabled": hackathon.waitlist_enabled,
        "organizer_id": str(hackathon.organizer_id),
        "created_at": hackathon.created_at.isoformat(),
        "description": hackathon.description,
        "schedule": hackathon.schedule,
        "venue_address": hackathon.venue_address,
        "parking_info": hackathon.parking_info,
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

    # Registration stats
    reg_result = await db.execute(
        select(Registration.status, func.count(Registration.id))
        .where(Registration.hackathon_id == hackathon_id)
        .group_by(Registration.status)
    )
    reg_stats = {status.value: count for status, count in reg_result.all()}

    # Check-in stats
    checked_in = reg_stats.get(RegistrationStatus.checked_in.value, 0)
    accepted = reg_stats.get(RegistrationStatus.accepted.value, 0)

    return {
        "total_submissions": total,
        "completed": len(completed),
        "avg_risk_score": round(avg_risk, 1),
        "by_verdict": {"clean": clean, "review": review, "flagged": flagged},
        "registrations": {
            "pending": reg_stats.get(RegistrationStatus.pending.value, 0),
            "accepted": accepted,
            "rejected": reg_stats.get(RegistrationStatus.rejected.value, 0),
            "waitlisted": reg_stats.get(RegistrationStatus.waitlisted.value, 0),
            "checked_in": checked_in,
        },
        "check_in_rate": round(checked_in / accepted * 100, 1) if accepted > 0 else 0,
    }


@router.get("/{hackathon_id}/swag-counts")
async def get_swag_counts(
    hackathon_id: uuid.UUID, authorization: str = Header(alias="Authorization"), db: AsyncSession = Depends(get_db)
):
    """Get meal and swag planning counts (organizer only)."""
    user = await _get_current_user(db, authorization)
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    await _ensure_organizer(user, hackathon, db)

    # Get all accepted/checked_in registrations
    reg_result = await db.execute(
        select(Registration).where(
            and_(
                Registration.hackathon_id == hackathon_id,
                Registration.status.in_([RegistrationStatus.accepted, RegistrationStatus.checked_in]),
            )
        )
    )
    regs = reg_result.scalars().all()

    # T-shirt sizes
    tshirt_counts = {}
    dietary_counts = {}
    experience_counts = {}

    for reg in regs:
        if reg.t_shirt_size:
            tshirt_counts[reg.t_shirt_size] = tshirt_counts.get(reg.t_shirt_size, 0) + 1
        if reg.dietary_restrictions:
            dietary_counts[reg.dietary_restrictions] = dietary_counts.get(reg.dietary_restrictions, 0) + 1
        if reg.experience_level:
            experience_counts[reg.experience_level] = experience_counts.get(reg.experience_level, 0) + 1

    return {
        "total_accepted": len(regs),
        "t_shirt_sizes": tshirt_counts,
        "dietary_restrictions": dietary_counts,
        "experience_levels": experience_counts,
    }


@router.get("/{hackathon_id}/submissions")
async def get_hackathon_submissions(hackathon_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """List submissions for a hackathon."""
    result = await db.execute(select(Submission).where(Submission.hackathon_id == hackathon_id))
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
async def update_hackathon(
    hackathon_id: uuid.UUID,
    body: dict,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Update hackathon settings (schedule, wifi, discord, webhook, deadline, capacity)."""
    user = await _get_current_user(db, authorization)
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    await _ensure_organizer(user, hackathon, db)

    updated = []
    allowed_fields = (
        "description",
        "schedule",
        "venue_address",
        "parking_info",
        "wifi_ssid",
        "wifi_password",
        "discord_invite_url",
        "discord_webhook_url",
        "discord_application_channel_id",
        "application_deadline",
        "max_participants",
        "waitlist_enabled",
    )
    for key in allowed_fields:
        if key in body and body[key] is not None:
            setattr(hackathon, key, body[key])
            updated.append(key)

    if updated:
        await db.commit()
        await _bust_hackathon_cache(str(hackathon_id))

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


# --- Bulk Operations ---


@router.post("/{hackathon_id}/registrations/bulk-accept", status_code=200)
async def bulk_accept_registrations(
    hackathon_id: uuid.UUID,
    registration_ids: list[uuid.UUID],
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Bulk accept pending registrations."""
    user = await _get_current_user(db, authorization)
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    await _ensure_organizer(user, hackathon, db)

    accepted_count = 0
    waitlisted_count = 0

    for reg_id in registration_ids:
        reg_result = await db.execute(
            select(Registration).where(and_(Registration.id == reg_id, Registration.hackathon_id == hackathon_id))
        )
        reg = reg_result.scalar_one_or_none()
        if not reg or reg.status != RegistrationStatus.pending:
            continue

        # Check capacity
        if hackathon.max_participants and hackathon.current_participants >= hackathon.max_participants:
            if hackathon.waitlist_enabled:
                reg.status = RegistrationStatus.waitlisted
                waitlisted_count += 1
            else:
                continue
        else:
            reg.status = RegistrationStatus.accepted
            reg.accepted_at = datetime.now(UTC)
            hackathon.current_participants += 1
            accepted_count += 1

    await db.commit()
    return {"accepted": accepted_count, "waitlisted": waitlisted_count}


@router.post("/{hackathon_id}/registrations/bulk-reject", status_code=200)
async def bulk_reject_registrations(
    hackathon_id: uuid.UUID,
    registration_ids: list[uuid.UUID],
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Bulk reject pending/waitlisted registrations."""
    user = await _get_current_user(db, authorization)
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    await _ensure_organizer(user, hackathon, db)

    rejected_count = 0

    for reg_id in registration_ids:
        reg_result = await db.execute(
            select(Registration).where(and_(Registration.id == reg_id, Registration.hackathon_id == hackathon_id))
        )
        reg = reg_result.scalar_one_or_none()
        if not reg or reg.status not in (RegistrationStatus.pending, RegistrationStatus.waitlisted):
            continue

        # If was accepted/waitlisted, decrement counter
        if reg.status == RegistrationStatus.waitlisted:
            pass  # wasn't counted in current_participants

        reg.status = RegistrationStatus.rejected
        rejected_count += 1

    await db.commit()
    return {"rejected": rejected_count}


@router.post("/{hackathon_id}/registrations/bulk-waitlist", status_code=200)
async def bulk_waitlist_registrations(
    hackathon_id: uuid.UUID,
    registration_ids: list[uuid.UUID],
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Bulk waitlist pending registrations."""
    user = await _get_current_user(db, authorization)
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    await _ensure_organizer(user, hackathon, db)

    if not hackathon.waitlist_enabled:
        raise HTTPException(status_code=400, detail="Waitlist is not enabled for this hackathon")

    waitlisted_count = 0

    for reg_id in registration_ids:
        reg_result = await db.execute(
            select(Registration).where(and_(Registration.id == reg_id, Registration.hackathon_id == hackathon_id))
        )
        reg = reg_result.scalar_one_or_none()
        if not reg or reg.status != RegistrationStatus.pending:
            continue

        reg.status = RegistrationStatus.waitlisted
        waitlisted_count += 1

    await db.commit()
    return {"waitlisted": waitlisted_count}


@router.get("/{hackathon_id}/registrations/export")
async def export_registrations_csv(
    hackathon_id: uuid.UUID, authorization: str = Header(alias="Authorization"), db: AsyncSession = Depends(get_db)
):
    """Export all registrations to CSV (organizer only)."""
    user = await _get_current_user(db, authorization)
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    await _ensure_organizer(user, hackathon, db)

    # Get all registrations with user info
    reg_result = await db.execute(
        select(Registration, User)
        .join(User, Registration.user_id == User.id)
        .where(Registration.hackathon_id == hackathon_id)
        .order_by(Registration.registered_at.desc())
    )
    rows = reg_result.all()

    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(
        [
            "ID",
            "Status",
            "Registered At",
            "Accepted At",
            "Checked In At",
            "Name",
            "Email",
            "Team Name",
            "Team Members",
            "School",
            "Major",
            "Age",
            "Pronouns",
            "Experience Level",
            "Skills",
            "T-Shirt Size",
            "Dietary Restrictions",
            "Phone",
            "Emergency Contact Name",
            "Emergency Contact Phone",
            "LinkedIn",
            "GitHub",
            "Resume URL",
            "What They Will Build",
            "Why Participate",
        ]
    )

    # Data
    for reg, user in rows:
        writer.writerow(
            [
                str(reg.id),
                reg.status.value,
                reg.registered_at.isoformat(),
                reg.accepted_at.isoformat() if reg.accepted_at else "",
                reg.checked_in_at.isoformat() if reg.checked_in_at else "",
                user.name,
                user.email,
                reg.team_name or "",
                ", ".join(reg.team_members) if reg.team_members else "",
                reg.school or "",
                reg.major or "",
                reg.age or "",
                reg.pronouns or "",
                reg.experience_level or "",
                ", ".join(reg.skills) if reg.skills else "",
                reg.t_shirt_size or "",
                reg.dietary_restrictions or "",
                reg.phone or "",
                reg.emergency_contact_name or "",
                reg.emergency_contact_phone or "",
                reg.linkedin_url or "",
                reg.github_url or "",
                reg.resume_url or "",
                (reg.what_build or "")[:200],
                (reg.why_participate or "")[:200],
            ]
        )

    output.seek(0)

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=registrations-{hackathon_id}.csv"},
    )


# --- Announcements ---


@router.post("/{hackathon_id}/announcements", status_code=201)
async def create_announcement(
    hackathon_id: uuid.UUID,
    body: AnnouncementCreate,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Create and send an announcement to all hackathon participants (organizer only)."""
    user = await _get_current_user(db, authorization)
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    await _ensure_organizer(user, hackathon, db)

    announcement = Announcement(
        hackathon_id=hackathon_id,
        title=body.title,
        content=body.content,
        priority=body.priority,
        sent_by=user.id,
    )
    db.add(announcement)
    await db.commit()
    await db.refresh(announcement)

    # TODO: Send to Discord webhook if configured

    return AnnouncementResponse.model_validate(announcement)


@router.get("/{hackathon_id}/announcements")
async def list_announcements(
    hackathon_id: uuid.UUID, authorization: str = Header(alias="Authorization"), db: AsyncSession = Depends(get_db)
):
    """List announcements for a hackathon. Organizers see all, participants see accepted ones."""
    user = await _get_current_user(db, authorization)

    # Check if user has access to this hackathon
    reg_result = await db.execute(
        select(Registration).where(and_(Registration.hackathon_id == hackathon_id, Registration.user_id == user.id))
    )
    registration = reg_result.scalar_one_or_none()

    # Organizer can see all
    hack_result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = hack_result.scalar_one_or_none()

    is_organizer = hackathon and hackathon.organizer_id == user.id and user.role == UserRole.organizer

    if not is_organizer and not registration:
        raise HTTPException(status_code=403, detail="Not authorized to view announcements for this hackathon")

    # Build query
    query = select(Announcement).where(Announcement.hackathon_id == hackathon_id)

    # Non-organizers only see non-draft announcements
    if not is_organizer:
        query = query.where(Announcement.priority != "draft")

    query = query.order_by(desc(Announcement.sent_at))

    result = await db.execute(query)
    announcements = result.scalars().all()

    return [AnnouncementResponse.model_validate(a) for a in announcements]


# --- Conflict of Interest (Judge) ---


@router.post("/{hackathon_id}/conflicts-of-interest", status_code=201)
async def declare_conflict_of_interest(
    hackathon_id: uuid.UUID,
    body: ConflictOfInterestCreate,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Declare a conflict of interest for a submission (judge only)."""
    user = await _get_current_user(db, authorization)

    if user.role != UserRole.judge:
        raise HTTPException(status_code=403, detail="Only judges can declare conflicts of interest")

    # Verify hackathon exists
    hack_result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = hack_result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    # Verify submission exists
    sub_result = await db.execute(select(Submission).where(Submission.id == body.submission_id))
    submission = sub_result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Check if already declared
    existing = await db.execute(
        select(ConflictOfInterest).where(
            and_(ConflictOfInterest.judge_id == user.id, ConflictOfInterest.submission_id == body.submission_id)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Conflict of interest already declared for this submission")

    coi = ConflictOfInterest(
        judge_id=user.id,
        hackathon_id=hackathon_id,
        submission_id=body.submission_id,
        reason=body.reason,
    )
    db.add(coi)
    await db.commit()
    await db.refresh(coi)

    return ConflictOfInterestResponse.model_validate(coi)


@router.get("/{hackathon_id}/conflicts-of-interest")
async def list_conflicts_of_interest(
    hackathon_id: uuid.UUID, authorization: str = Header(alias="Authorization"), db: AsyncSession = Depends(get_db)
):
    """List all conflicts of interest for a hackathon (organizer only)."""
    user = await _get_current_user(db, authorization)

    hack_result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = hack_result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    await _ensure_organizer(user, hackathon, db)

    result = await db.execute(select(ConflictOfInterest).where(ConflictOfInterest.hackathon_id == hackathon_id))
    cois = result.scalars().all()

    return [ConflictOfInterestResponse.model_validate(c) for c in cois]


@router.delete("/{hackathon_id}/conflicts-of-interest/{coi_id}", status_code=200)
async def remove_conflict_of_interest(
    hackathon_id: uuid.UUID,
    coi_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Remove a conflict of interest declaration (organizer or the judge who created it)."""
    user = await _get_current_user(db, authorization)

    coi_result = await db.execute(
        select(ConflictOfInterest).where(
            and_(ConflictOfInterest.id == coi_id, ConflictOfInterest.hackathon_id == hackathon_id)
        )
    )
    coi = coi_result.scalar_one_or_none()
    if not coi:
        raise HTTPException(status_code=404, detail="Conflict of interest not found")

    # Can delete if organizer or the judge who created it
    hack_result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = hack_result.scalar_one_or_none()
    is_organizer = hackathon and hackathon.organizer_id == user.id and user.role == UserRole.organizer

    if not is_organizer and coi.judge_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to remove this conflict of interest")

    await db.delete(coi)
    await db.commit()

    return {"deleted": True}


# --- Co-Organizer Management ---


@router.get("/{hackathon_id}/organizers")
async def list_organizers(
    hackathon_id: uuid.UUID, authorization: str = Header(alias="Authorization"), db: AsyncSession = Depends(get_db)
):
    """List all organizers for a hackathon (primary + co-organizers)."""
    user = await _get_current_user(db, authorization)

    hackathon_result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = hackathon_result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    # Only organizers can view the organizer list
    await _ensure_organizer(user, hackathon, db)

    # Get primary organizer
    primary_result = await db.execute(select(User).where(User.id == hackathon.organizer_id))
    primary = primary_result.scalar_one()

    organizers = [
        {
            "user_id": str(primary.id),
            "email": primary.email,
            "name": primary.name,
            "role": "primary",
            "added_at": hackathon.created_at.isoformat(),
        }
    ]

    # Get co-organizers
    co_result = await db.execute(
        select(HackathonOrganizer, User)
        .join(User, HackathonOrganizer.user_id == User.id)
        .where(HackathonOrganizer.hackathon_id == hackathon_id)
    )
    for co_org, co_user in co_result.all():
        organizers.append(
            {
                "user_id": str(co_user.id),
                "email": co_user.email,
                "name": co_user.name,
                "role": "co-organizer",
                "added_at": co_org.added_at.isoformat(),
                "added_by": str(co_org.added_by) if co_org.added_by else None,
            }
        )

    return {"organizers": organizers}


@router.post("/{hackathon_id}/organizers", status_code=201)
async def add_organizer(
    hackathon_id: uuid.UUID,
    body: dict,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Add a co-organizer to the hackathon (primary organizer only)."""
    user = await _get_current_user(db, authorization)

    hackathon_result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = hackathon_result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    # Only the primary organizer can add co-organizers
    if hackathon.organizer_id != user.id:
        raise HTTPException(status_code=403, detail="Only the primary organizer can add co-organizers")

    email = body.get("email")
    if not email:
        raise HTTPException(status_code=422, detail="email is required")

    # Find user by email
    user_result = await db.execute(select(User).where(User.email == email))
    target_user = user_result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Can't add yourself
    if target_user.id == user.id:
        raise HTTPException(status_code=400, detail="You are already the primary organizer")

    # Check if already an organizer
    if target_user.id == hackathon.organizer_id:
        raise HTTPException(status_code=409, detail="User is already the primary organizer")

    existing = await db.execute(
        select(HackathonOrganizer).where(
            and_(HackathonOrganizer.hackathon_id == hackathon_id, HackathonOrganizer.user_id == target_user.id)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="User is already a co-organizer")

    # Add co-organizer
    co_org = HackathonOrganizer(
        hackathon_id=hackathon_id,
        user_id=target_user.id,
        added_by=user.id,
    )
    db.add(co_org)
    await db.commit()

    return {
        "user_id": str(target_user.id),
        "email": target_user.email,
        "name": target_user.name,
        "role": "co-organizer",
        "added_at": datetime.now(UTC).isoformat(),
    }


@router.delete("/{hackathon_id}/organizers/{user_id}")
async def remove_organizer(
    hackathon_id: uuid.UUID,
    user_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Remove a co-organizer (primary organizer only)."""
    current_user = await _get_current_user(db, authorization)

    hackathon_result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = hackathon_result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    # Only the primary organizer can remove co-organizers
    if hackathon.organizer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the primary organizer can remove co-organizers")

    # Can't remove yourself
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot remove the primary organizer")

    # Find and delete the co-organizer record
    result = await db.execute(
        select(HackathonOrganizer).where(
            and_(HackathonOrganizer.hackathon_id == hackathon_id, HackathonOrganizer.user_id == user_id)
        )
    )
    co_org = result.scalar_one_or_none()
    if not co_org:
        raise HTTPException(status_code=404, detail="Co-organizer not found")

    await db.delete(co_org)
    await db.commit()

    return {"deleted": True}


# ── Devpost Import ─────────────────────────────────────────────

DEVPOST_PROJECT_RE = re.compile(r"/software/([^/?#]+)")


@router.post("/{hackathon_id}/import-devpost")
async def import_devpost_submissions(
    hackathon_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Scrape the Devpost hackathon gallery and import project URLs for analysis."""
    user = await _get_current_user(db, authorization)
    if user.role != UserRole.organizer:
        raise HTTPException(status_code=403, detail="Only organizers can import")

    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")
    if not hackathon.devpost_url:
        raise HTTPException(status_code=400, detail="No Devpost URL configured. Set it in hackathon settings first.")

    gallery_url = hackathon.devpost_url.rstrip("/") + "/project-gallery"
    found_urls: set[str] = set()
    page = 1

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        while True:
            try:
                resp = await client.get(
                    f"{gallery_url}?page={page}" if page > 1 else gallery_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    },
                )
                resp.raise_for_status()
            except httpx.HTTPError as e:
                # If page 1 fails, report error. Later pages failing is fine.
                if page == 1:
                    raise HTTPException(status_code=502, detail=f"Failed to fetch Devpost gallery: {e}")
                break

            soup = BeautifulSoup(resp.text, "lxml")
            page_urls: set[str] = set()

            # Find all project links on the gallery page
            for link in soup.select("a[href*='/software/']"):
                href = link.get("href", "")
                match = DEVPOST_PROJECT_RE.search(href)
                if match:
                    full_url = f"https://devpost.com/software/{match.group(1)}"
                    page_urls.add(full_url)

            # Also try gallery-item links
            for link in soup.select("[class*='gallery-item'] a, [class*='link-to-software']"):
                href = link.get("href", "")
                match = DEVPOST_PROJECT_RE.search(href)
                if match:
                    full_url = f"https://devpost.com/software/{match.group(1)}"
                    page_urls.add(full_url)

            if not page_urls:
                break  # No more projects found

            found_urls.update(page_urls)
            page += 1

            # Safety limit — 20 pages max
            if page > 20:
                break

    if not found_urls:
        raise HTTPException(
            status_code=404,
            detail="No project URLs found on the gallery. Make sure the Devpost URL is a valid hackathon page.",
        )

    # Create submissions for new URLs
    from app.analyzer import analyze_submission
    from app.auth import create_anonymous_token
    from app.models import Submission, SubmissionStatus

    imported = 0
    skipped = 0

    for url in found_urls:
        # Check if already exists for this hackathon
        existing = await db.execute(
            select(Submission).where(
                Submission.devpost_url == url,
                Submission.hackathon_id == hackathon_id,
            )
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue

        sub = Submission(
            devpost_url=url,
            hackathon_id=hackathon_id,
            status=SubmissionStatus.pending,
            access_token=create_anonymous_token(),
        )
        db.add(sub)
        await db.commit()
        await db.refresh(sub)

        # Queue analysis
        asyncio.create_task(analyze_submission(sub.id))
        imported += 1

    return {
        "hackathon_id": str(hackathon_id),
        "gallery_url": gallery_url,
        "found": len(found_urls),
        "imported": imported,
        "skipped": skipped,
    }


# ── Cache helpers ───────────────────────────────────────────


async def _bust_hackathon_list_cache():
    await cache_delete_pattern(f"{HK_CACHE_PFX}:list_hackathons:*")


async def _bust_hackathon_cache(hackathon_id: str):
    await cache_delete_pattern(f"{HK_CACHE_PFX}:get_hackathon:*")
    await cache_delete_pattern(f"{HK_CACHE_PFX}:list_hackathons:*")
    await cache_delete_pattern("tracks:list_tracks:*")
