"""Hackathon management routes."""
import uuid
import csv
import io
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import (
    Hackathon, Submission, SubmissionStatus, Verdict, Registration, RegistrationStatus,
    Announcement, ConflictOfInterest, User, UserRole
)
from app.schemas import (
    HackathonCreate, AnnouncementCreate, AnnouncementResponse,
    ConflictOfInterestCreate, ConflictOfInterestResponse
)
from app.checks.similarity import run_similarity
from app.auth import decode_token

router = APIRouter(prefix="/api/hackathons", tags=["hackathons"])


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


async def _ensure_organizer(user: User, hackathon: Hackathon):
    """Verify user is the organizer of the hackathon."""
    if user.role != UserRole.organizer or hackathon.organizer_id != user.id:
        raise HTTPException(status_code=403, detail="Only the hackathon organizer can perform this action")


@router.post("", status_code=201)
async def create_hackathon(
    body: HackathonCreate,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db)
):
    """Create a new hackathon."""
    user = await _get_current_user(db, authorization)
    if user.role != UserRole.organizer:
        raise HTTPException(status_code=403, detail="Only organizers can create hackathons")
    
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
        schedule=body.schedule,
    )
    db.add(hackathon)
    await db.commit()
    await db.refresh(hackathon)
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
async def list_hackathons(db: AsyncSession = Depends(get_db)):
    """List all hackathons."""
    result = await db.execute(select(Hackathon).order_by(Hackathon.created_at.desc()))
    hackathons = result.scalars().all()
    return [{
        "id": str(h.id),
        "name": h.name,
        "start_date": h.start_date.isoformat(),
        "end_date": h.end_date.isoformat(),
        "application_deadline": h.application_deadline.isoformat() if h.application_deadline else None,
        "max_participants": h.max_participants,
        "current_participants": h.current_participants,
        "waitlist_enabled": h.waitlist_enabled,
    } for h in hackathons]


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
    hackathon_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db)
):
    """Get meal and swag planning counts (organizer only)."""
    user = await _get_current_user(db, authorization)
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")
    
    await _ensure_organizer(user, hackathon)
    
    # Get all accepted/checked_in registrations
    reg_result = await db.execute(
        select(Registration).where(
            and_(
                Registration.hackathon_id == hackathon_id,
                Registration.status.in_([RegistrationStatus.accepted, RegistrationStatus.checked_in])
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
async def update_hackathon(
    hackathon_id: uuid.UUID,
    body: dict,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db)
):
    """Update hackathon settings (schedule, wifi, discord, webhook, deadline, capacity)."""
    user = await _get_current_user(db, authorization)
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")
    
    await _ensure_organizer(user, hackathon)

    updated = []
    allowed_fields = (
        "description", "schedule", "venue_address", "parking_info",
        "wifi_ssid", "wifi_password", "discord_invite_url", "discord_webhook_url",
        "discord_application_channel_id", "application_deadline", "max_participants",
        "waitlist_enabled"
    )
    for key in allowed_fields:
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


# --- Bulk Operations ---

@router.post("/{hackathon_id}/registrations/bulk-accept", status_code=200)
async def bulk_accept_registrations(
    hackathon_id: uuid.UUID,
    registration_ids: list[uuid.UUID],
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db)
):
    """Bulk accept pending registrations."""
    user = await _get_current_user(db, authorization)
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")
    
    await _ensure_organizer(user, hackathon)
    
    accepted_count = 0
    waitlisted_count = 0
    
    for reg_id in registration_ids:
        reg_result = await db.execute(
            select(Registration).where(
                and_(Registration.id == reg_id, Registration.hackathon_id == hackathon_id)
            )
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
            reg.accepted_at = datetime.now(timezone.utc)
            hackathon.current_participants += 1
            accepted_count += 1
    
    await db.commit()
    return {"accepted": accepted_count, "waitlisted": waitlisted_count}


@router.post("/{hackathon_id}/registrations/bulk-reject", status_code=200)
async def bulk_reject_registrations(
    hackathon_id: uuid.UUID,
    registration_ids: list[uuid.UUID],
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db)
):
    """Bulk reject pending/waitlisted registrations."""
    user = await _get_current_user(db, authorization)
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")
    
    await _ensure_organizer(user, hackathon)
    
    rejected_count = 0
    
    for reg_id in registration_ids:
        reg_result = await db.execute(
            select(Registration).where(
                and_(Registration.id == reg_id, Registration.hackathon_id == hackathon_id)
            )
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
    db: AsyncSession = Depends(get_db)
):
    """Bulk waitlist pending registrations."""
    user = await _get_current_user(db, authorization)
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")
    
    await _ensure_organizer(user, hackathon)
    
    if not hackathon.waitlist_enabled:
        raise HTTPException(status_code=400, detail="Waitlist is not enabled for this hackathon")
    
    waitlisted_count = 0
    
    for reg_id in registration_ids:
        reg_result = await db.execute(
            select(Registration).where(
                and_(Registration.id == reg_id, Registration.hackathon_id == hackathon_id)
            )
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
    hackathon_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db)
):
    """Export all registrations to CSV (organizer only)."""
    user = await _get_current_user(db, authorization)
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")
    
    await _ensure_organizer(user, hackathon)
    
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
    writer.writerow([
        "ID", "Status", "Registered At", "Accepted At", "Checked In At",
        "Name", "Email", "Team Name", "Team Members",
        "School", "Major", "Age", "Pronouns", "Experience Level",
        "Skills", "T-Shirt Size", "Dietary Restrictions",
        "Phone", "Emergency Contact Name", "Emergency Contact Phone",
        "LinkedIn", "GitHub", "Resume URL",
        "What They Will Build", "Why Participate"
    ])
    
    # Data
    for reg, user in rows:
        writer.writerow([
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
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=registrations-{hackathon_id}.csv"}
    )


# --- Announcements ---

@router.post("/{hackathon_id}/announcements", status_code=201)
async def create_announcement(
    hackathon_id: uuid.UUID,
    body: AnnouncementCreate,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db)
):
    """Create and send an announcement to all hackathon participants (organizer only)."""
    user = await _get_current_user(db, authorization)
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")
    
    await _ensure_organizer(user, hackathon)
    
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
    hackathon_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db)
):
    """List announcements for a hackathon. Organizers see all, participants see accepted ones."""
    user = await _get_current_user(db, authorization)
    
    # Check if user has access to this hackathon
    reg_result = await db.execute(
        select(Registration).where(
            and_(Registration.hackathon_id == hackathon_id, Registration.user_id == user.id)
        )
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
    db: AsyncSession = Depends(get_db)
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
            and_(
                ConflictOfInterest.judge_id == user.id,
                ConflictOfInterest.submission_id == body.submission_id
            )
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
    hackathon_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db)
):
    """List all conflicts of interest for a hackathon (organizer only)."""
    user = await _get_current_user(db, authorization)
    
    hack_result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = hack_result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")
    
    await _ensure_organizer(user, hackathon)
    
    result = await db.execute(
        select(ConflictOfInterest).where(ConflictOfInterest.hackathon_id == hackathon_id)
    )
    cois = result.scalars().all()
    
    return [ConflictOfInterestResponse.model_validate(c) for c in cois]


@router.delete("/{hackathon_id}/conflicts-of-interest/{coi_id}", status_code=200)
async def remove_conflict_of_interest(
    hackathon_id: uuid.UUID,
    coi_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db)
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
