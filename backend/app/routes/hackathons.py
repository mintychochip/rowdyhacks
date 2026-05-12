"""Hackathon management routes."""

import asyncio
import re
import uuid
from uuid import UUID
from datetime import UTC, datetime

import httpx
from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import cache_delete_pattern, cached
from app.checks.similarity import run_similarity
from app.clerk_auth import require_clerk_user_with_db
from app.database import get_db
from app.models import (
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
from app.services.analytics_service import AnalyticsService
from app.services.announcement_service import AnnouncementService
from app.services.email_blast_service import EmailBlastService
from app.services.registration_service import RegistrationService

router = APIRouter(prefix="/api/hackathons", tags=["hackathons"])

HK_CACHE_TTL = 300  # 5 minutes
HK_CACHE_PFX = "hackathons"


async def _ensure_organizer(user: User, hackathon: Hackathon, db: AsyncSession):
    """Verify the requesting user is the primary or co-organizer of a hackathon.

    Behavior:
    1. Return immediately if the user is the primary organizer.
    2. Query HackathonOrganizer for a matching (hackathon_id, user_id) row.
    3. Return if a co-organizer record exists.
    4. Raise 403 if neither condition is met.

    Raises: HTTPException(403) if user lacks organizer privileges.
    Side Effects: None (read-only).
    Dependencies: app.models.HackathonOrganizer, app.models.UserRole.
    Consumers: Internal helper used by multiple hackathon route guards.
    """
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
    body: HackathonCreate,
    auth: dict = Depends(require_clerk_user_with_db),
    db: AsyncSession = Depends(get_db),
):
    """Create a new hackathon (organizer-only, one per portal).

    Behavior:
    1. Verify the user is an organizer.
    2. Reject if a hackathon already exists (portal limit).
    3. Build and persist a Hackathon record from the request body.
    4. Seed default tracks for the hackathon.
    5. Index hackathon data for the assistant.
    6. Bust the hackathon list cache.
    7. Return the created hackathon summary.

    Raises: HTTPException(403) if not organizer, HTTPException(400) if hackathon already exists.
    Side Effects: Inserts Hackathon and Track rows; mutates cache; triggers assistant indexing.
    Dependencies: app.models.Hackathon, app.models.UserRole, app.routes.tracks.seed_tracks, app.cache.cache_delete_pattern.
    Consumers: POST /api/hackathons, organizer setup wizard.
    """
    user = auth["user"]
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

    # Index hackathon data for assistant
    try:
        from app.assistant.indexer import DocumentIndexer

        indexer = DocumentIndexer(db)
        await indexer.index_hackathon(hackathon)
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Failed to index hackathon: {e}")

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
    """List all hackathons with caching.

    Behavior:
    1. Query all Hackathon records ordered by created_at descending.
    2. Return serialized summaries with participant counts and deadlines.

    Raises: None
    Side Effects: None (read-only, cached).
    Dependencies: app.models.Hackathon, app.cache.cached.
    Consumers: GET /api/hackathons, public hackathon listing.
    """
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
    """Get a single hackathon by ID with caching.

    Behavior:
    1. Query the Hackathon record by UUID.
    2. Return 404 if not found.
    3. Return full hackathon details including schedule, venue, and Discord info.

    Raises: HTTPException(404) if hackathon not found.
    Side Effects: None (read-only, cached).
    Dependencies: app.models.Hackathon, app.cache.cached.
    Consumers: GET /api/hackathons/{hackathon_id}, hackathon detail page.
    """
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
    """Get aggregate statistics for a hackathon.

    Behavior:
    1. Load all submissions for the hackathon and compute totals, completion rate, average risk, and verdict breakdown.
    2. Load registration status counts from the database.
    3. Compute check-in rate from accepted vs checked-in counts.
    4. Return the aggregated stats object.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.models.Submission, app.models.Registration, app.models.Verdict, app.models.SubmissionStatus, sqlalchemy.func.count.
    Consumers: GET /api/hackathons/{hackathon_id}/stats, organizer dashboard.
    """
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
    auth: dict = Depends(require_clerk_user_with_db),
    db: AsyncSession = Depends(get_db),
):
    """Get meal and swag planning counts for accepted participants (organizer only).

    Behavior:
    1. Verify the hackathon exists and the user is an organizer.
    2. Query all accepted and checked-in registrations.
    3. Aggregate counts for t-shirt sizes, dietary restrictions, and experience levels.
    4. Return the aggregated planning data.

    Raises: HTTPException(404) if hackathon not found, HTTPException(403) if not organizer.
    Side Effects: None (read-only).
    Dependencies: app.models.Hackathon, app.models.Registration, app.models.RegistrationStatus.
    Consumers: GET /api/hackathons/{hackathon_id}/swag-counts, organizer logistics panel.
    """
    user = auth["user"]
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
    """List all submissions for a hackathon.

    Behavior:
    1. Query Submission rows for the hackathon.
    2. Return serialized summaries with project titles, URLs, team info, risk scores, and verdicts.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.models.Submission.
    Consumers: GET /api/hackathons/{hackathon_id}/submissions, submissions browser.
    """
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
    auth: dict = Depends(require_clerk_user_with_db),
    db: AsyncSession = Depends(get_db),
):
    """Update hackathon settings (organizer only).

    Behavior:
    1. Verify the hackathon exists and the user is an organizer.
    2. Apply updates only to allowed fields from the request body.
    3. Commit changes and bust relevant caches if any field was updated.
    4. Return the updated field list.

    Raises: HTTPException(404) if hackathon not found, HTTPException(403) if not organizer.
    Side Effects: Mutates Hackathon fields; deletes cache keys.
    Dependencies: app.models.Hackathon, app.cache.cache_delete_pattern.
    Consumers: PUT /api/hackathons/{hackathon_id}, organizer settings form.
    """
    user = auth["user"]
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

    Behavior:
    1. Verify the hackathon exists; return 404 if not found.
    2. Delegate to run_similarity(hackathon_id) for batch analysis.
    3. Return the similarity summary.

    Raises: HTTPException(404) if hackathon not found.
    Side Effects: run_similarity manages its own DB session for mutations.
    Dependencies: app.checks.similarity.run_similarity, app.models.Hackathon.
    Consumers: POST /api/hackathons/{hackathon_id}/similarity, organizer fraud panel.
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
    auth: dict = Depends(require_clerk_user_with_db),
    db: AsyncSession = Depends(get_db),
):
    """Bulk accept pending registrations with capacity and waitlist handling (organizer only).

    Behavior:
    1. Verify the hackathon exists and the user is an organizer.
    2. For each pending registration ID:
       a. Skip if not pending or not in this hackathon.
       b. If at capacity and waitlist enabled, move to waitlisted.
       c. If at capacity and waitlist disabled, skip.
       d. Otherwise accept, increment current_participants, and set accepted_at.
    3. Commit and return accepted and waitlisted counts.

    Raises: HTTPException(404) if hackathon not found, HTTPException(403) if not organizer.
    Side Effects: Mutates Registration rows and Hackathon.current_participants.
    Dependencies: app.models.Hackathon, app.models.Registration, app.models.RegistrationStatus.
    Consumers: POST /api/hackathons/{hackathon_id}/registrations/bulk-accept, organizer registration panel.
    """
    user = auth["user"]
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    await _ensure_organizer(user, hackathon, db)

    service = RegistrationService()
    return await service.bulk_accept(db, hackathon_id, registration_ids)


@router.post("/{hackathon_id}/registrations/bulk-reject", status_code=200)
async def bulk_reject_registrations(
    hackathon_id: uuid.UUID,
    registration_ids: list[uuid.UUID],
    auth: dict = Depends(require_clerk_user_with_db),
    db: AsyncSession = Depends(get_db),
):
    """Bulk reject pending or waitlisted registrations (organizer only).

    Behavior:
    1. Verify the hackathon exists and the user is an organizer.
    2. Delegate to RegistrationService.bulk_reject.
    3. Return the rejected count.

    Raises: HTTPException(404) if hackathon not found, HTTPException(403) if not organizer.
    Side Effects: Mutates Registration.status.
    Dependencies: app.services.registration_service.RegistrationService.
    Consumers: POST /api/hackathons/{hackathon_id}/registrations/bulk-reject, organizer registration panel.
    """
    user = auth["user"]
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    await _ensure_organizer(user, hackathon, db)

    service = RegistrationService()
    return await service.bulk_reject(db, hackathon_id, registration_ids)


@router.post("/{hackathon_id}/registrations/bulk-waitlist", status_code=200)
async def bulk_waitlist_registrations(
    hackathon_id: uuid.UUID,
    registration_ids: list[uuid.UUID],
    auth: dict = Depends(require_clerk_user_with_db),
    db: AsyncSession = Depends(get_db),
):
    """Bulk waitlist pending registrations (organizer only).

    Behavior:
    1. Verify the hackathon exists and the user is an organizer.
    2. Delegate to RegistrationService.bulk_waitlist.
    3. Return the waitlisted count.

    Raises: HTTPException(404) if hackathon not found, HTTPException(403) if not organizer, HTTPException(400) if waitlist disabled.
    Side Effects: Mutates Registration.status.
    Dependencies: app.services.registration_service.RegistrationService.
    Consumers: POST /api/hackathons/{hackathon_id}/registrations/bulk-waitlist, organizer registration panel.
    """
    user = auth["user"]
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    await _ensure_organizer(user, hackathon, db)

    service = RegistrationService()
    return await service.bulk_waitlist(db, hackathon_id, registration_ids)


@router.get("/{hackathon_id}/registrations/export")
async def export_registrations_csv(
    hackathon_id: uuid.UUID,
    auth: dict = Depends(require_clerk_user_with_db),
    db: AsyncSession = Depends(get_db),
):
    """Export all hackathon registrations to CSV (organizer only).

    Behavior:
    1. Verify the hackathon exists and the user is an organizer.
    2. Delegate to RegistrationService.export_registrations_csv.
    3. Return the CSV as a StreamingResponse download.

    Raises: HTTPException(404) if hackathon not found, HTTPException(403) if not organizer.
    Side Effects: None (read-only, generates CSV in memory).
    Dependencies: app.services.registration_service.RegistrationService, fastapi.responses.StreamingResponse.
    Consumers: GET /api/hackathons/{hackathon_id}/registrations/export, organizer data export.
    """
    user = auth["user"]
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    await _ensure_organizer(user, hackathon, db)

    service = RegistrationService()
    bytes_io, filename = await service.export_registrations_csv(db, hackathon_id)

    return StreamingResponse(
        bytes_io,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# --- Announcements ---


@router.post("/{hackathon_id}/announcements", status_code=201)
async def create_announcement(
    hackathon_id: uuid.UUID,
    body: AnnouncementCreate,
    auth: dict = Depends(require_clerk_user_with_db),
    db: AsyncSession = Depends(get_db),
):
    """Create and broadcast an announcement to all hackathon participants (organizer only).

    Behavior:
    1. Verify the hackathon exists and the user is an organizer.
    2. Create an Announcement record from the request body.
    3. Persist and return the announcement.

    Raises: HTTPException(404) if hackathon not found, HTTPException(403) if not organizer.
    Side Effects: Inserts Announcement row.
    Dependencies: app.models.Hackathon, app.models.Announcement, app.schemas.AnnouncementCreate, app.schemas.AnnouncementResponse.
    Consumers: POST /api/hackathons/{hackathon_id}/announcements, organizer communication panel.
    """
    user = auth["user"]
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    await _ensure_organizer(user, hackathon, db)

    service = AnnouncementService()
    announcement = await service.create_announcement(db, hackathon_id, user.id, body.title, body.content, body.priority)

    return AnnouncementResponse.model_validate(announcement)


@router.get("/{hackathon_id}/announcements")
async def list_announcements(
    hackathon_id: uuid.UUID,
    auth: dict = Depends(require_clerk_user_with_db),
    db: AsyncSession = Depends(get_db),
):
    """List announcements for a hackathon with role-based filtering.

    Behavior:
    1. Verify the user has access (organizer or registered participant).
    2. Load all announcements for the hackathon.
    3. Filter out draft announcements for non-organizers.
    4. Order by sent_at descending and return.

    Raises: HTTPException(403) if user lacks access.
    Side Effects: None (read-only).
    Dependencies: app.models.Hackathon, app.models.Registration, app.models.Announcement, app.schemas.AnnouncementResponse.
    Consumers: GET /api/hackathons/{hackathon_id}/announcements, participant and organizer announcement feeds.
    """
    user = auth["user"]

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

    service = AnnouncementService()
    announcements = await service.list_announcements(db, hackathon_id, is_organizer)

    return [AnnouncementResponse.model_validate(a) for a in announcements]


# --- Conflict of Interest (Judge) ---


@router.post("/{hackathon_id}/conflicts-of-interest", status_code=201)
async def declare_conflict_of_interest(
    hackathon_id: uuid.UUID,
    body: ConflictOfInterestCreate,
    auth: dict = Depends(require_clerk_user_with_db),
    db: AsyncSession = Depends(get_db),
):
    """Declare a conflict of interest for a submission (judge only).

    Behavior:
    1. Verify the user is a judge.
    2. Verify the hackathon and submission exist.
    3. Reject if a conflict already exists for this judge and submission.
    4. Create and persist the ConflictOfInterest record.
    5. Return the created conflict.

    Raises: HTTPException(403) if not a judge, HTTPException(404) if hackathon or submission not found, HTTPException(409) if conflict already declared.
    Side Effects: Inserts ConflictOfInterest row.
    Dependencies: app.models.Hackathon, app.models.Submission, app.models.ConflictOfInterest, app.models.UserRole, app.schemas.ConflictOfInterestCreate, app.schemas.ConflictOfInterestResponse.
    Consumers: POST /api/hackathons/{hackathon_id}/conflicts-of-interest, judge dashboard.
    """
    user = auth["user"]

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
    hackathon_id: uuid.UUID,
    auth: dict = Depends(require_clerk_user_with_db),
    db: AsyncSession = Depends(get_db),
):
    """List all conflicts of interest for a hackathon (organizer only).

    Behavior:
    1. Verify the hackathon exists and the user is an organizer.
    2. Query all ConflictOfInterest rows for the hackathon.
    3. Return serialized conflict records.

    Raises: HTTPException(404) if hackathon not found, HTTPException(403) if not organizer.
    Side Effects: None (read-only).
    Dependencies: app.models.Hackathon, app.models.ConflictOfInterest, app.schemas.ConflictOfInterestResponse.
    Consumers: GET /api/hackathons/{hackathon_id}/conflicts-of-interest, organizer judging panel.
    """
    user = auth["user"]

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
    auth: dict = Depends(require_clerk_user_with_db),
    db: AsyncSession = Depends(get_db),
):
    """Remove a conflict of interest declaration.

    Behavior:
    1. Load the conflict record by ID and hackathon ID.
    2. Verify the requesting user is either the hackathon organizer or the judge who created the conflict.
    3. Delete the record and commit.
    4. Return confirmation.

    Raises: HTTPException(404) if conflict not found, HTTPException(403) if user unauthorized.
    Side Effects: Deletes ConflictOfInterest row.
    Dependencies: app.models.Hackathon, app.models.ConflictOfInterest, app.models.UserRole.
    Consumers: DELETE /api/hackathons/{hackathon_id}/conflicts-of-interest/{coi_id}, organizer or judge dashboard.
    """
    user = auth["user"]

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
    hackathon_id: uuid.UUID,
    auth: dict = Depends(require_clerk_user_with_db),
    db: AsyncSession = Depends(get_db),
):
    """List all organizers for a hackathon (primary + co-organizers).

    Behavior:
    1. Verify the hackathon exists and the user is an organizer.
    2. Load the primary organizer user record.
    3. Load all co-organizers joined with their user records.
    4. Return a consolidated list with roles and metadata.

    Raises: HTTPException(404) if hackathon not found, HTTPException(403) if not organizer.
    Side Effects: None (read-only).
    Dependencies: app.models.Hackathon, app.models.HackathonOrganizer, app.models.User.
    Consumers: GET /api/hackathons/{hackathon_id}/organizers, organizer team management page.
    """
    user = auth["user"]

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
    auth: dict = Depends(require_clerk_user_with_db),
    db: AsyncSession = Depends(get_db),
):
    """Add a co-organizer to the hackathon (primary organizer only).

    Behavior:
    1. Verify the hackathon exists and the requesting user is the primary organizer.
    2. Require an email in the request body.
    3. Lookup the target user by email.
    4. Reject if target is the primary organizer or already a co-organizer.
    5. Create a HackathonOrganizer record and commit.
    6. Return the new co-organizer summary.

    Raises: HTTPException(404) if hackathon or user not found, HTTPException(403) if not primary organizer, HTTPException(400) for self-add, HTTPException(409) if already co-organizer.
    Side Effects: Inserts HackathonOrganizer row.
    Dependencies: app.models.Hackathon, app.models.HackathonOrganizer, app.models.User.
    Consumers: POST /api/hackathons/{hackathon_id}/organizers, organizer team management page.
    """
    user = auth["user"]

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
    user_id: str,
    auth: dict = Depends(require_clerk_user_with_db),
    db: AsyncSession = Depends(get_db),
):
    """Remove a co-organizer from the hackathon (primary organizer only).

    Behavior:
    1. Verify the hackathon exists and the requesting user is the primary organizer.
    2. Reject if attempting to remove the primary organizer.
    3. Find and delete the HackathonOrganizer record for the target user.
    4. Commit and return confirmation.

    Raises: HTTPException(404) if hackathon or co-organizer not found, HTTPException(403) if not primary organizer, HTTPException(400) if attempting self-removal.
    Side Effects: Deletes HackathonOrganizer row.
    Dependencies: app.models.Hackathon, app.models.HackathonOrganizer.
    Consumers: DELETE /api/hackathons/{hackathon_id}/organizers/{user_id}, organizer team management page.
    """
    current_user = auth["user"]

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
    auth: dict = Depends(require_clerk_user_with_db),
    db: AsyncSession = Depends(get_db),
):
    """Scrape a Devpost hackathon gallery and import project URLs for analysis (organizer only).

    Behavior:
    1. Verify the user is an organizer and the hackathon exists with a configured Devpost URL.
    2. Paginate through the Devpost project gallery up to 20 pages.
    3. Extract all unique project URLs using regex and CSS selectors.
    4. Skip URLs already imported for this hackathon.
    5. Create pending Submission records with anonymous tokens.
    6. Trigger background analysis for each new submission.
    7. Return import counts (found, imported, skipped).

    Raises: HTTPException(403) if not organizer, HTTPException(404) if hackathon not found or no Devpost URL, HTTPException(404) if no projects found, HTTPException(502) if gallery fetch fails.
    Side Effects: Inserts Submission rows; spawns background asyncio tasks.
    Dependencies: app.models.Hackathon, app.models.Submission, app.models.SubmissionStatus, app.analyzer.analyze_submission, app.auth.create_anonymous_token, httpx.AsyncClient, bs4.BeautifulSoup.
    Consumers: POST /api/hackathons/{hackathon_id}/import-devpost, organizer submission import tool.
    """
    user = auth["user"]
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
                if page == 1:
                    raise HTTPException(status_code=502, detail=f"Failed to fetch Devpost gallery: {e}")
                break

            soup = BeautifulSoup(resp.text, "lxml")
            page_urls: set[str] = set()

            for link in soup.select("a[href*='/software/']"):
                href = link.get("href", "")
                match = DEVPOST_PROJECT_RE.search(href)
                if match:
                    full_url = f"https://devpost.com/software/{match.group(1)}"
                    page_urls.add(full_url)

            for link in soup.select("[class*='gallery-item'] a, [class*='link-to-software']"):
                href = link.get("href", "")
                match = DEVPOST_PROJECT_RE.search(href)
                if match:
                    full_url = f"https://devpost.com/software/{match.group(1)}"
                    page_urls.add(full_url)

            if not page_urls:
                break

            found_urls.update(page_urls)
            page += 1

            if page > 20:
                break

    if not found_urls:
        raise HTTPException(
            status_code=404,
            detail="No project URLs found on the gallery. Make sure the Devpost URL is a valid hackathon page.",
        )

    from app.services.submission_service import SubmissionService

    submission_service = SubmissionService()
    from app.models import Submission

    imported = 0
    skipped = 0

    for url in found_urls:
        existing = await db.execute(
            select(Submission).where(
                Submission.devpost_url == url,
                Submission.hackathon_id == hackathon_id,
            )
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue

        sub = await submission_service.create_submission(db, url=url, hackathon_id=hackathon_id)
        asyncio.create_task(submission_service.analyze_submission(sub.id))
        imported += 1

    return {
        "hackathon_id": str(hackathon_id),
        "gallery_url": gallery_url,
        "found": len(found_urls),
        "imported": imported,
        "skipped": skipped,
    }


async def _bust_hackathon_list_cache():
    """Invalidate the cached hackathon list.

    Side Effects:
        Deletes Redis keys matching the hackathon list cache prefix.
    """
    await cache_delete_pattern(f"{HK_CACHE_PFX}:list_hackathons:*")


async def _bust_hackathon_cache(hackathon_id: str):
    """Invalidate cached data for a specific hackathon.

    Behavior:
    1. Delete Redis cache keys for the hackathon detail endpoint pattern.
    2. Delete Redis cache keys for the hackathon list endpoint pattern.
    3. Delete Redis cache keys for the tracks listing endpoint pattern.

    Raises: None
    Side Effects: Deletes Redis keys.
    Dependencies: app.cache.cache_delete_pattern.
    Consumers: Hackathon mutation routes (create, update, delete).
    """
    await cache_delete_pattern(f"{HK_CACHE_PFX}:get_hackathon:*")
    await cache_delete_pattern(f"{HK_CACHE_PFX}:list_hackathons:*")
    await cache_delete_pattern("tracks:list_tracks:*")


@router.get("/{hackathon_id}/prizes/awarded")
async def list_awarded_prizes(
    hackathon_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List all awarded prizes for a hackathon.

    Behavior:
    1. Fetch awarded prizes via PrizeService.list_awarded_prizes.
    2. Return serialized list with prize and team details.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.services.prize_service.PrizeService.
    Consumers: GET /api/hackathons/{hackathon_id}/prizes/awarded.
    """
    from app.services.prize_service import PrizeService

    service = PrizeService()
    awards = await service.list_awarded_prizes(db, UUID(hackathon_id))
    return [
        {
            "id": str(award.id),
            "prize_id": str(award.prize_id),
            "prize_name": award.prize.name if award.prize else None,
            "team_id": str(award.team_id),
            "team_name": award.team.name if award.team else None,
            "awarded_at": award.awarded_at.isoformat() if award.awarded_at else None,
            "awarded_by": award.awarded_by,
        }
        for award in awards
    ]


class EmailBlastRequest(BaseModel):
    """Request body for sending a bulk email blast to a registrant cohort."""

    subject: str
    body: str
    cohort: str = "accepted"  # accepted, waitlist, checked_in, track
    track_id: str | None = None


@router.post("/{hackathon_id}/email-blast")
async def email_blast(
    hackathon_id: str,
    body: EmailBlastRequest,
    auth: dict = Depends(require_clerk_user_with_db),
    db: AsyncSession = Depends(get_db),
):
    """Send a bulk email to a registrant cohort (organizer only).

    Behavior:
    1. Load the hackathon and verify the caller is an organizer.
    2. Instantiate EmailBlastService and dispatch to the correct cohort method.
    3. Return the delivery summary with sent and failed counts.

    Raises: HTTPException(404) if hackathon not found. HTTPException(403) if not organizer.
    Side Effects: Triggers outbound emails via EmailBlastService.
    Dependencies: app.services.email_blast_service.EmailBlastService.
    Consumers: POST /api/hackathons/{id}/email-blast, organizer communications panel.
    """
    user = auth["user"]
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    await _ensure_organizer(user, hackathon, db)

    service = EmailBlastService()
    h_id = UUID(hackathon_id)
    sender_id = user.id

    if body.cohort == "accepted":
        summary = await service.send_bulk_email(db, h_id, body.subject, body.body, sender_id)
    elif body.cohort == "waitlist":
        summary = await service.send_to_waitlist(db, h_id, body.subject, body.body, sender_id)
    elif body.cohort == "checked_in":
        summary = await service.send_to_checked_in(db, h_id, body.subject, body.body, sender_id)
    elif body.cohort == "track":
        if not body.track_id:
            raise HTTPException(status_code=400, detail="track_id is required for track cohort")
        summary = await service.send_to_track(db, h_id, UUID(body.track_id), body.subject, body.body, sender_id)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown cohort: {body.cohort}")

    return summary


@router.get("/{hackathon_id}/analytics")
async def get_hackathon_analytics(
    hackathon_id: uuid.UUID,
    auth: dict = Depends(require_clerk_user_with_db),
    db: AsyncSession = Depends(get_db),
):
    """Get analytics metrics for a hackathon (organizer only).

    Behavior:
    1. Verify the user is an organizer.
    2. Load the hackathon.
    3. Aggregate all metrics via AnalyticsService.
    4. Return the combined analytics payload.

    Raises: HTTPException(403) if not organizer, HTTPException(404) if hackathon not found.
    """
    user = auth["user"]
    if user.role != UserRole.organizer:
        raise HTTPException(status_code=403, detail="Organizer access required")

    hackathon_result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = hackathon_result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    service = AnalyticsService()
    metrics = await service.get_all_metrics(db, hackathon_id)
    return {"hackathon_id": str(hackathon_id), **metrics}


@router.get("/{hackathon_id}/audit-log")
async def get_hackathon_audit_log(
    hackathon_id: uuid.UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    auth: dict = Depends(require_clerk_user_with_db),
    db: AsyncSession = Depends(get_db),
):
    """Get audit log entries for a hackathon (organizer only).

    Behavior:
    1. Verify the user is an organizer.
    2. Query AuditLog rows for the hackathon, ordered by created_at desc.
    3. Return paginated results.

    Raises: HTTPException(403) if not organizer.
    """
    user = auth["user"]
    if user.role != UserRole.organizer:
        raise HTTPException(status_code=403, detail="Organizer access required")

    from app.models import AuditLog

    total_result = await db.execute(select(func.count(AuditLog.id)).where(AuditLog.hackathon_id == hackathon_id))
    total = total_result.scalar() or 0

    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.hackathon_id == hackathon_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    logs = result.scalars().all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "logs": [
            {
                "id": str(log.id),
                "user_id": log.user_id,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "details_json": log.details_json,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
    }
