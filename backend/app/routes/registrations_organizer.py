"""Organizer registration management routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth import require_organizer
from app.database import get_db
from app.models import Hackathon, HackathonOrganizer, Registration, RegistrationStatus, User
from app.services.registration_service import RegistrationService
from app.services.scan_service import ScanError, ScanService

router = APIRouter(prefix="/api/hackathons", tags=["organizer-registrations"])

scan_service = ScanService()


async def _verify_organizer_owns_hackathon(user: User, hackathon_id: uuid.UUID, db: AsyncSession) -> Hackathon:
    """Verify the organizer owns the hackathon or is a co-organizer.

    Behavior:
    1. Query the hackathon by id and organizer_id.
    2. Return the hackathon if the user is the primary organizer.
    3. Check HackathonOrganizer for co-organizer status.
    4. Return the hackathon if the user is a co-organizer.
    5. Raise 404 if neither condition is met.

    Raises: HTTPException(404) if hackathon not found or user lacks access.
    Side Effects: None (read-only).
    Dependencies: app.models.Hackathon, app.models.HackathonOrganizer.
    Consumers: Internal helper used by organizer registration routes.
    """
    # Primary organizer check
    query = select(Hackathon).where(and_(Hackathon.id == hackathon_id, Hackathon.organizer_id == user.id))
    result = await db.execute(query)
    hackathon = result.scalar_one_or_none()
    if hackathon:
        return hackathon

    # Co-organizer check
    co_query = select(HackathonOrganizer).where(
        and_(HackathonOrganizer.hackathon_id == hackathon_id, HackathonOrganizer.user_id == user.id)
    )
    co_result = await db.execute(co_query)
    if co_result.scalar_one_or_none():
        hackathon_result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
        hackathon = hackathon_result.scalar_one_or_none()
        if hackathon:
            return hackathon

    raise HTTPException(status_code=404, detail="Hackathon not found")


@router.get("/{hackathon_id}/registrations", operation_id="organizer_list_hackathon_registrations")
async def list_hackathon_registrations(
    hackathon_id: uuid.UUID,
    current_user: User = Depends(require_organizer),
    status: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List registrations for a hackathon. Organizer only, RLS: own hackathons only.

    Behavior:
    1. Verify the organizer owns the hackathon.
    2. Build filtered count and list queries by hackathon_id and optional status.
    3. Fetch registrations with pagination.
    4. Load associated users for name/email enrichment.
    5. Return the registration list with pagination metadata.

    Raises: HTTPException(404) if hackathon not found or not owned.
    Side Effects: None (read-only).
    Dependencies: app.models.Registration, app.models.User, app.auth.require_organizer.
    Consumers: GET /api/hackathons/{hackathon_id}/registrations, organizer dashboard.
    """
    user = current_user
    await _verify_organizer_owns_hackathon(user, hackathon_id, db)

    service = RegistrationService()
    result = await service.list_registrations_for_hackathon(db, hackathon_id, status=status, offset=offset, limit=limit)

    # Add review note aggregates
    from app.services.registration_note_service import RegistrationNoteService

    note_service = RegistrationNoteService(db)
    for reg in result["registrations"]:
        rid = reg["id"]
        aggregates = await note_service.get_aggregates_for_registration(uuid.UUID(rid))
        reg["review_notes_count"] = aggregates["review_notes_count"]
        reg["average_rating"] = aggregates["average_rating"]

    return result


@router.post("/{hackathon_id}/registrations/{registration_id}/accept", operation_id="organizer_accept_registration")
async def accept_registration(
    hackathon_id: uuid.UUID,
    registration_id: uuid.UUID,
    current_user: User = Depends(require_organizer),
    db: AsyncSession = Depends(get_db),
):
    """Approve a registration and generate QR token. Organizer only.

    Behavior:
    1. Verify the organizer owns the hackathon.
    2. Load the registration by id and hackathon_id.
    3. Raise 404 if the registration is not found.
    4. Raise 409 if the registration is not pending.
    5. Generate a QR token and update status to accepted.
    6. Commit and publish a registration.accepted event.
    7. Return the updated registration details.

    Raises: HTTPException(404) if hackathon or registration not found. HTTPException(409) if registration not pending.
    Side Effects: Mutates Registration status, qr_token, accepted_at; publishes event.
    Dependencies: app.auth.create_qr_token, app.models.Registration, app.services.event_service.publish_event.
    Consumers: POST /api/hackathons/{hackathon_id}/registrations/{registration_id}/accept, organizer dashboard.
    """
    user = current_user
    hackathon = await _verify_organizer_owns_hackathon(user, hackathon_id, db)

    service = RegistrationService()
    reg = await service.accept_registration(db, hackathon_id, registration_id, hackathon=hackathon, generate_qr=True)

    from app.services.event_service import publish_event

    await publish_event(
        db,
        "registration.accepted",
        {"registration_id": str(reg.id), "hackathon_id": str(hackathon_id), "user_id": str(reg.user_id)},
    )

    return {
        "id": str(reg.id),
        "status": reg.status.value,
        "qr_token": reg.qr_token,
        "accepted_at": reg.accepted_at.isoformat(),
    }


@router.post("/{hackathon_id}/registrations/{registration_id}/reject", operation_id="organizer_reject_registration")
async def reject_registration(
    hackathon_id: uuid.UUID,
    registration_id: uuid.UUID,
    current_user: User = Depends(require_organizer),
    db: AsyncSession = Depends(get_db),
):
    """Reject a registration. Organizer only.

    Behavior:
    1. Verify the organizer owns the hackathon.
    2. Load the registration by id and hackathon_id.
    3. Raise 404 if the registration is not found.
    4. Raise 409 if the registration is not pending or accepted.
    5. Update status to rejected and invalidate the QR token.
    6. If the registration was accepted, promote from waitlist.
    7. Commit and return the updated registration details.

    Raises: HTTPException(404) if hackathon or registration not found. HTTPException(409) if registration not rejectable.
    Side Effects: Mutates Registration status and qr_token; may trigger waitlist promotion.
    Dependencies: app.models.Registration, app.waitlist.promote_from_waitlist.
    Consumers: POST /api/hackathons/{hackathon_id}/registrations/{registration_id}/reject, organizer dashboard.
    """
    user = current_user
    await _verify_organizer_owns_hackathon(user, hackathon_id, db)

    service = RegistrationService()
    reg = await service.reject_registration(db, hackathon_id, registration_id, promote_waitlist=True)

    return {"id": str(reg.id), "status": reg.status.value}


@router.post("/{hackathon_id}/registrations/{registration_id}/checkin", operation_id="organizer_checkin_registration")
async def checkin_registration(
    hackathon_id: uuid.UUID,
    registration_id: uuid.UUID,
    current_user: User = Depends(require_organizer),
    db: AsyncSession = Depends(get_db),
):
    """Check in a registration. Organizer only.

    Behavior:
    1. Verify the organizer owns the hackathon.
    2. Load the registration by id and hackathon_id.
    3. Raise 404 if the registration is not found.
    4. Raise 409 if the registration is not accepted.
    5. Update status to checked_in and set checked_in_at.
    6. Commit and publish a registration.checked_in event.
    7. Return the updated registration details.

    Raises: HTTPException(404) if hackathon or registration not found. HTTPException(409) if registration not accepted.
    Side Effects: Mutates Registration status and checked_in_at; publishes event.
    Dependencies: app.services.scan_service.ScanService, app.services.event_service.publish_event.
    Consumers: POST /api/hackathons/{hackathon_id}/registrations/{registration_id}/checkin, organizer dashboard.
    """
    user = current_user
    await _verify_organizer_owns_hackathon(user, hackathon_id, db)

    try:
        result = await scan_service.checkin_registration(db, hackathon_id, registration_id)
    except ScanError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e

    from app.services.event_service import publish_event

    await publish_event(
        db,
        "registration.checked_in",
        {"registration_id": result["id"], "hackathon_id": str(hackathon_id), "user_id": result["user_id"]},
    )

    return result


@router.post("/{hackathon_id}/registrations/{registration_id}/waitlist")
async def move_to_waitlist(
    hackathon_id: uuid.UUID,
    registration_id: uuid.UUID,
    current_user: User = Depends(require_organizer),
    db: AsyncSession = Depends(get_db),
):
    """Move a pending registration to waitlist. Organizer only.

    Behavior:
    1. Verify the organizer owns the hackathon.
    2. Load the registration by id and hackathon_id.
    3. Raise 404 if the registration is not found.
    4. Raise 409 if the registration is not pending.
    5. Update status to waitlisted.
    6. Commit and return the updated registration details.

    Raises: HTTPException(404) if hackathon or registration not found. HTTPException(409) if registration not pending.
    Side Effects: Mutates Registration status.
    Dependencies: app.models.Registration.
    Consumers: POST /api/hackathons/{hackathon_id}/registrations/{registration_id}/waitlist, organizer dashboard.
    """
    user = current_user
    await _verify_organizer_owns_hackathon(user, hackathon_id, db)

    service = RegistrationService()
    reg = await service.waitlist_registration(db, hackathon_id, registration_id)

    return {"id": str(reg.id), "status": reg.status.value}


@router.post("/{hackathon_id}/registrations/{registration_id}/unwaitlist")
async def remove_from_waitlist(
    hackathon_id: uuid.UUID,
    registration_id: uuid.UUID,
    current_user: User = Depends(require_organizer),
    db: AsyncSession = Depends(get_db),
):
    """Move a waitlisted registration back to pending. Organizer only.

    Behavior:
    1. Verify the organizer owns the hackathon.
    2. Delegate to RegistrationService.unwaitlist_registration.
    3. Return the updated registration details.

    Raises: HTTPException(404) if hackathon or registration not found. HTTPException(409) if registration not waitlisted.
    Side Effects: Mutates Registration status and declined_count.
    Dependencies: app.services.registration_service.RegistrationService.
    Consumers: POST /api/hackathons/{hackathon_id}/registrations/{registration_id}/unwaitlist, organizer dashboard.
    """
    user = current_user
    await _verify_organizer_owns_hackathon(user, hackathon_id, db)

    service = RegistrationService()
    reg = await service.unwaitlist_registration(db, hackathon_id, registration_id)

    return {"id": str(reg.id), "status": reg.status.value}


@router.post("/{hackathon_id}/waitlist/promote")
async def manual_promote_waitlist(
    hackathon_id: uuid.UUID,
    current_user: User = Depends(require_organizer),
    db: AsyncSession = Depends(get_db),
):
    """Manually promote top waitlisted person to offered. Organizer only.

    Behavior:
    1. Verify the organizer owns the hackathon.
    2. Delegate to RegistrationService.manual_promote_waitlist.
    3. Return the promoted registration details.

    Raises: HTTPException(404) if hackathon not found. HTTPException(409) if no one to promote or at capacity.
    Side Effects: Mutates Registration status and offer_expires_at via waitlist promotion.
    Dependencies: app.services.registration_service.RegistrationService.
    Consumers: POST /api/hackathons/{hackathon_id}/waitlist/promote, organizer dashboard.
    """
    user = current_user
    await _verify_organizer_owns_hackathon(user, hackathon_id, db)

    service = RegistrationService()
    promoted = await service.manual_promote_waitlist(db, hackathon_id)

    return {
        "id": str(promoted.id),
        "status": promoted.status.value,
        "offer_expires_at": promoted.offer_expires_at.isoformat(),
    }


@router.get("/{hackathon_id}/registrations/dietary-report")
async def get_dietary_report(
    hackathon_id: uuid.UUID,
    current_user: User = Depends(require_organizer),
    db: AsyncSession = Depends(get_db),
):
    """Return aggregated dietary restrictions for accepted registrations. Organizer only.

    Behavior:
    1. Verify the organizer owns the hackathon.
    2. Query accepted registrations with their users.
    3. Aggregate counts by dietary restriction value.
    4. Return both summary and individual entries.

    Raises: HTTPException(404) if hackathon not found or not owned.
    Side Effects: None (read-only).
    Dependencies: app.models.Registration, app.models.User, app.auth.require_organizer.
    Consumers: GET /api/hackathons/{hackathon_id}/registrations/dietary-report, organizer dashboard.
    """
    user = current_user
    await _verify_organizer_owns_hackathon(user, hackathon_id, db)

    result = await db.execute(
        select(Registration, User)
        .join(User, Registration.user_id == User.id)
        .where(Registration.hackathon_id == hackathon_id)
        .where(Registration.status == RegistrationStatus.accepted)
    )
    rows = result.all()

    summary: dict[str, int] = {}
    participants = []
    for reg, user_obj in rows:
        restriction = reg.dietary_restrictions or "None"
        summary[restriction] = summary.get(restriction, 0) + 1
        participants.append(
            {
                "user_id": user_obj.id,
                "name": user_obj.name,
                "email": user_obj.email,
                "dietary_restrictions": restriction,
            }
        )

    return {
        "total": len(rows),
        "summary": summary,
        "participants": participants,
    }


@router.get("/{hackathon_id}/registrations/emergency-contacts")
async def get_emergency_contacts(
    hackathon_id: uuid.UUID,
    current_user: User = Depends(require_organizer),
    db: AsyncSession = Depends(get_db),
):
    """Return emergency contact info for all accepted participants. Organizer only.

    Behavior:
    1. Verify the organizer owns the hackathon.
    2. Query accepted registrations with their users.
    3. Return name, phone, emergency contact name and phone for each.

    Raises: HTTPException(404) if hackathon not found or not owned.
    Side Effects: None (read-only).
    Dependencies: app.models.Registration, app.models.User, app.auth.require_organizer.
    Consumers: GET /api/hackathons/{hackathon_id}/registrations/emergency-contacts, organizer dashboard.
    """
    user = current_user
    await _verify_organizer_owns_hackathon(user, hackathon_id, db)

    result = await db.execute(
        select(Registration, User)
        .join(User, Registration.user_id == User.id)
        .where(Registration.hackathon_id == hackathon_id)
        .where(Registration.status == RegistrationStatus.accepted)
    )
    rows = result.all()

    contacts = []
    for reg, user_obj in rows:
        contacts.append(
            {
                "user_id": user_obj.id,
                "name": user_obj.name,
                "email": user_obj.email,
                "phone": reg.phone,
                "emergency_contact_name": reg.emergency_contact_name,
                "emergency_contact_phone": reg.emergency_contact_phone,
            }
        )

    return {
        "total": len(contacts),
        "contacts": contacts,
    }


@router.get("/{hackathon_id}/waitlist")
async def list_waitlist(
    hackathon_id: uuid.UUID,
    current_user: User = Depends(require_organizer),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List waitlisted registrations with position. Organizer only.

    Behavior:
    1. Verify the organizer owns the hackathon.
    2. Delegate to RegistrationService.list_waitlist.
    3. Return the waitlist with pagination metadata.

    Raises: HTTPException(404) if hackathon not found or not owned.
    Side Effects: None (read-only).
    Dependencies: app.services.registration_service.RegistrationService, app.auth.require_organizer.
    Consumers: GET /api/hackathons/{hackathon_id}/waitlist, organizer dashboard.
    """
    user = current_user
    await _verify_organizer_owns_hackathon(user, hackathon_id, db)

    service = RegistrationService()
    return await service.list_waitlist(db, hackathon_id, offset=offset, limit=limit)
