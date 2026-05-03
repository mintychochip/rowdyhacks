"""Participant registration routes."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Header, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.discord_bot import post_application_to_discord
from app.models import Registration, RegistrationStatus, Hackathon, User, UserRole, HackathonOrganizer
from app.schemas import RegistrationCreate
from app.auth import decode_token, create_qr_token
from app.email_service import send_email
from app.waitlist import promote_from_waitlist, auto_waitlist_if_full, get_waitlist_position

router = APIRouter(prefix="/api", tags=["registrations"])


def _get_current_user_payload(authorization: str | None):
    """Extract and validate the current user from Bearer token. Returns payload dict."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization.removeprefix("Bearer ")
    try:
        return decode_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def _get_user(db: AsyncSession, user_id: str) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def _registration_to_response(r: Registration, user: User | None = None) -> dict:
    return {
        "id": str(r.id),
        "hackathon_id": str(r.hackathon_id),
        "user_id": str(r.user_id),
        "status": r.status.value,
        "team_name": r.team_name,
        "team_members": r.team_members,
        "linkedin_url": r.linkedin_url,
        "github_url": r.github_url,
        "resume_url": r.resume_url,
        "experience_level": r.experience_level,
        "t_shirt_size": r.t_shirt_size,
        "phone": r.phone,
        "dietary_restrictions": r.dietary_restrictions,
        "what_build": r.what_build,
        "why_participate": r.why_participate,
        "age": r.age,
        "school": r.school,
        "major": r.major,
        "pronouns": r.pronouns,
        "skills": r.skills,
        "emergency_contact_name": r.emergency_contact_name,
        "emergency_contact_phone": r.emergency_contact_phone,
        "qr_token": r.qr_token,
        "pass_serial_apple": r.pass_serial_apple,
        "pass_id_google": r.pass_id_google,
        "registered_at": r.registered_at.isoformat(),
        "accepted_at": r.accepted_at.isoformat() if r.accepted_at else None,
        "checked_in_at": r.checked_in_at.isoformat() if r.checked_in_at else None,
        "user_name": user.name if user else None,
        "user_email": user.email if user else None,
    }


async def _ensure_hackathon_organizer(
    db: AsyncSession, user_id: str, hackathon_id: uuid.UUID,
) -> Hackathon:
    """Verify the current user is the organizer or co-organizer of the given hackathon."""
    result = await db.execute(
        select(Hackathon).where(Hackathon.id == hackathon_id)
    )
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    # Verify caller is an organizer and owns this hackathon (or is co-organizer)
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user or user.role != UserRole.organizer:
        raise HTTPException(status_code=403, detail="Only organizers can perform this action")
    
    # Primary organizer check
    if hackathon.organizer_id == user.id:
        return hackathon
    
    # Co-organizer check
    co_result = await db.execute(
        select(HackathonOrganizer).where(
            and_(HackathonOrganizer.hackathon_id == hackathon_id, HackathonOrganizer.user_id == user_id)
        )
    )
    if co_result.scalar_one_or_none():
        return hackathon
    
    raise HTTPException(status_code=403, detail="Only the hackathon organizer can perform this action")


@router.get("/hackathons/{hackathon_id}/registrations")
async def list_hackathon_registrations(
    hackathon_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    status: str | None = Query(None, description="Filter by status: pending, accepted, rejected, checked_in"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Organizer view: list all registrations for a hackathon."""
    payload = _get_current_user_payload(authorization)
    await _ensure_hackathon_organizer(db, payload["sub"], hackathon_id)

    filters = [Registration.hackathon_id == hackathon_id]
    if status:
        try:
            filters.append(Registration.status == RegistrationStatus(status))
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid status '{status}'. Must be one of: pending, accepted, rejected, waitlisted, checked_in",
            )

    count_query = select(func.count(Registration.id)).where(*filters)
    total = (await db.execute(count_query)).scalar() or 0

    query = (
        select(Registration)
        .where(*filters)
        .options(selectinload(Registration.user))
        .order_by(Registration.registered_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    registrations = result.scalars().all()

    return {
        "registrations": [
            _registration_to_response(r, r.user) for r in registrations
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/hackathons/{hackathon_id}/registrations/{registration_id}/accept", status_code=200)
async def accept_registration(
    hackathon_id: uuid.UUID,
    registration_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Accept a pending or waitlisted registration (organizer only)."""
    payload = _get_current_user_payload(authorization)
    hackathon = await _ensure_hackathon_organizer(db, payload["sub"], hackathon_id)

    result = await db.execute(
        select(Registration)
        .where(and_(
            Registration.id == registration_id,
            Registration.hackathon_id == hackathon_id,
        ))
        .options(selectinload(Registration.user))
    )
    reg = result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")

    if reg.status not in (RegistrationStatus.pending, RegistrationStatus.waitlisted):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot accept registration with status '{reg.status.value}'; only pending or waitlisted registrations can be accepted",
        )
    
    # Check capacity (if not already accepted/waitlisted)
    if reg.status == RegistrationStatus.pending:
        if hackathon.max_participants and hackathon.current_participants >= hackathon.max_participants:
            raise HTTPException(status_code=400, detail="Hackathon is at capacity. Consider enabling waitlist.")
        hackathon.current_participants += 1

    reg.status = RegistrationStatus.accepted
    reg.accepted_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(reg)

    return _registration_to_response(reg, reg.user)


@router.post("/hackathons/{hackathon_id}/registrations/{registration_id}/reject", status_code=200)
async def reject_registration(
    hackathon_id: uuid.UUID,
    registration_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Reject a pending registration (organizer only)."""
    payload = _get_current_user_payload(authorization)
    await _ensure_hackathon_organizer(db, payload["sub"], hackathon_id)

    result = await db.execute(
        select(Registration)
        .where(and_(
            Registration.id == registration_id,
            Registration.hackathon_id == hackathon_id,
        ))
        .options(selectinload(Registration.user))
    )
    reg = result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")

    if reg.status != RegistrationStatus.pending:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot reject registration with status '{reg.status.value}'; only pending registrations can be rejected",
        )

    reg.status = RegistrationStatus.rejected
    await db.commit()
    await db.refresh(reg)

    return _registration_to_response(reg, reg.user)


@router.post("/hackathons/{hackathon_id}/registrations/{registration_id}/checkin", status_code=200)
async def checkin_registration(
    hackathon_id: uuid.UUID,
    registration_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Check in a registration (organizer action). Only accepted registrations can be checked in."""
    payload = _get_current_user_payload(authorization)
    await _ensure_hackathon_organizer(db, payload["sub"], hackathon_id)

    result = await db.execute(
        select(Registration)
        .where(and_(
            Registration.id == registration_id,
            Registration.hackathon_id == hackathon_id,
        ))
        .options(selectinload(Registration.user))
    )
    reg = result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")

    if reg.status != RegistrationStatus.accepted:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot check in registration with status '{reg.status.value}'; only accepted registrations can be checked in",
        )

    reg.status = RegistrationStatus.checked_in
    reg.checked_in_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(reg)

    return _registration_to_response(reg, reg.user)


@router.post("/hackathons/{hackathon_id}/register", status_code=201)
async def register_for_hackathon(
    hackathon_id: uuid.UUID,
    body: RegistrationCreate,
    background_tasks: BackgroundTasks,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Register current user for a hackathon."""
    payload = _get_current_user_payload(authorization)
    user = await _get_user(db, payload["sub"])

    # Verify hackathon exists
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    # Check application deadline
    if hackathon.application_deadline and datetime.now(timezone.utc) > hackathon.application_deadline:
        raise HTTPException(status_code=400, detail="Application deadline has passed")

    # Check for duplicate registration
    existing = await db.execute(
        select(Registration).where(
            and_(Registration.hackathon_id == hackathon_id, Registration.user_id == user.id)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already registered for this hackathon")

    # Check if should auto-waitlist
    should_waitlist = await auto_waitlist_if_full(hackathon_id, db)
    if should_waitlist:
        if not hackathon.waitlist_enabled:
            raise HTTPException(status_code=400, detail="Hackathon is at capacity")
        initial_status = RegistrationStatus.waitlisted
    else:
        initial_status = RegistrationStatus.pending

    reg = Registration(
        hackathon_id=hackathon_id,
        user_id=user.id,
        status=initial_status,
        team_name=body.team_name,
        team_members=body.team_members,
        linkedin_url=body.linkedin_url,
        github_url=body.github_url,
        resume_url=body.resume_url,
        experience_level=body.experience_level,
        t_shirt_size=body.t_shirt_size,
        phone=body.phone,
        dietary_restrictions=body.dietary_restrictions,
        what_build=body.what_build,
        why_participate=body.why_participate,
        age=body.age,
        school=body.school,
        major=body.major,
        pronouns=body.pronouns,
        skills=body.skills,
        emergency_contact_name=body.emergency_contact_name,
        emergency_contact_phone=body.emergency_contact_phone,
    )
    db.add(reg)
    
    # Update current_participants count if waitlisted
    if initial_status == RegistrationStatus.waitlisted:
        hackathon.current_participants += 1
    
    await db.commit()
    await db.refresh(reg)

    # Discord notification via background task
    background_tasks.add_task(post_application_to_discord, str(reg.id))

    response = _registration_to_response(reg, user)

    # If waitlisted, add position info
    if reg.status == RegistrationStatus.waitlisted:
        position = await get_waitlist_position(reg.id, hackathon_id, db)
        response["waitlist_info"] = {"estimated_position": position}

    return response


@router.get("/registrations")
async def list_my_registrations(
    authorization: str = Header(alias="Authorization"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List registrations for the current user. RLS: own registrations only."""
    payload = _get_current_user_payload(authorization)
    user = await _get_user(db, payload["sub"])

    # RLS: only current user's registrations
    count_query = select(func.count(Registration.id)).where(Registration.user_id == user.id)
    total = (await db.execute(count_query)).scalar()

    query = (
        select(Registration)
        .where(Registration.user_id == user.id)
        .options(selectinload(Registration.user))
        .order_by(Registration.registered_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    registrations = result.scalars().all()

    return {
        "registrations": [
            _registration_to_response(r, r.user) for r in registrations
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/registrations/{registration_id}")
async def get_registration(
    registration_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Get a single registration. RLS: own only."""
    payload = _get_current_user_payload(authorization)
    user = await _get_user(db, payload["sub"])

    query = (
        select(Registration)
        .where(and_(Registration.id == registration_id, Registration.user_id == user.id))
        .options(selectinload(Registration.user))
    )
    result = await db.execute(query)
    reg = result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")

    return _registration_to_response(reg, reg.user)


@router.post("/{registration_id}/accept-offer")
async def accept_offer(
    registration_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Participant accepts an offered spot from waitlist promotion."""
    # Authenticate
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization.removeprefix("Bearer ")
    payload = decode_token(token)
    user_id = payload.get("sub")

    # Lock registration row to prevent race conditions
    result = await db.execute(
        select(Registration)
        .where(Registration.id == registration_id)
        .where(Registration.user_id == user_id)
        .with_for_update()
    )
    reg = result.scalar_one_or_none()

    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    if reg.status != RegistrationStatus.offered:
        raise HTTPException(status_code=409, detail=f"Cannot accept a {reg.status.value} registration")
    if reg.offer_expires_at and reg.offer_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Offer has expired")

    # Check capacity one more time
    hackathon = await db.get(Hackathon, reg.hackathon_id)
    accepted_count = await db.execute(
        select(func.count(Registration.id))
        .where(Registration.hackathon_id == reg.hackathon_id)
        .where(Registration.status == RegistrationStatus.accepted)
    )

    if accepted_count.scalar() >= hackathon.max_participants:
        # Someone else took the spot
        reg.status = RegistrationStatus.waitlisted
        reg.offer_expires_at = None
        await db.commit()
        raise HTTPException(status_code=409, detail="Spot no longer available")

    # Accept the offer
    reg.status = RegistrationStatus.accepted
    reg.accepted_at = datetime.now(timezone.utc)
    reg.offer_expires_at = None

    # Generate QR token
    reg.qr_token = create_qr_token(
        registration_id=str(reg.id),
        user_id=str(reg.user_id),
        hackathon_id=str(reg.hackathon_id),
        hackathon_end=hackathon.end_date,
    )

    await db.commit()

    # Send confirmation email
    user = await db.get(User, reg.user_id)
    if user:
        await send_email(
            to_email=user.email,
            email_type="status_accepted",
            context={
                "name": user.name,
                "hackathon_name": hackathon.name,
                "start_date": hackathon.start_date.strftime("%Y-%m-%d"),
                "end_date": hackathon.end_date.strftime("%Y-%m-%d"),
                "venue": hackathon.venue_address or "TBD",
            },
            registration_id=reg.id,
            hackathon_id=hackathon.id,
            db=db
        )

    return {
        "id": str(reg.id),
        "status": reg.status.value,
        "qr_token": reg.qr_token,
        "accepted_at": reg.accepted_at.isoformat()
    }


@router.post("/{registration_id}/decline-offer")
async def decline_offer(
    registration_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Participant declines an offered spot. Returns to waitlist with lower priority."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization.removeprefix("Bearer ")
    payload = decode_token(token)
    user_id = payload.get("sub")

    result = await db.execute(
        select(Registration)
        .where(Registration.id == registration_id)
        .where(Registration.user_id == user_id)
    )
    reg = result.scalar_one_or_none()

    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    if reg.status != RegistrationStatus.offered:
        raise HTTPException(status_code=409, detail=f"Cannot decline a {reg.status.value} registration")

    # Decline - return to waitlist with incremented declined_count
    reg.status = RegistrationStatus.waitlisted
    reg.offer_expires_at = None
    reg.declined_count = (reg.declined_count or 0) + 1

    # Trigger promotion of next person
    await db.flush()
    await promote_from_waitlist(reg.hackathon_id, db)

    await db.commit()

    return {"id": str(reg.id), "status": reg.status.value, "declined_count": reg.declined_count}

