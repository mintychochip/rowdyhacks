"""Participant registration routes."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Header, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.discord_bot import post_application_to_discord
from app.models import Registration, RegistrationStatus, Hackathon, User, UserRole
from app.schemas import RegistrationCreate
from app.auth import decode_token

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
    """Verify the current user is the organizer of the given hackathon and return it."""
    result = await db.execute(
        select(Hackathon).where(Hackathon.id == hackathon_id)
    )
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    # Verify caller is an organizer and owns this hackathon
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user or user.role != UserRole.organizer or hackathon.organizer_id != user.id:
        raise HTTPException(status_code=403, detail="Only the hackathon organizer can perform this action")
    return hackathon


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
                detail=f"Invalid status '{status}'. Must be one of: pending, accepted, rejected, checked_in",
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
    """Accept a pending registration (organizer only)."""
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
            detail=f"Cannot accept registration with status '{reg.status.value}'; only pending registrations can be accepted",
        )

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

    # Check for duplicate registration
    existing = await db.execute(
        select(Registration).where(
            and_(Registration.hackathon_id == hackathon_id, Registration.user_id == user.id)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already registered for this hackathon")

    reg = Registration(
        hackathon_id=hackathon_id,
        user_id=user.id,
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
    await db.commit()
    await db.refresh(reg)

    # Discord notification via background task
    background_tasks.add_task(post_application_to_discord, str(reg.id))

    return _registration_to_response(reg, user)


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


@router.get("/registrations/{registration_id}/wallet/apple")
async def download_apple_pass(
    registration_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Download Apple Wallet .pkpass. Own registration only."""
    payload = _get_current_user_payload(authorization)
    user = await _get_user(db, payload["sub"])

    query = (
        select(Registration)
        .where(and_(Registration.id == registration_id, Registration.user_id == user.id))
    )
    result = await db.execute(query)
    reg = result.scalar_one_or_none()
    if not reg or reg.status != RegistrationStatus.accepted:
        raise HTTPException(status_code=404, detail="Not found or not accepted")

    from app.wallet.apple import generate_apple_pass
    from app.config import settings

    hackathon_result = await db.execute(select(Hackathon).where(Hackathon.id == reg.hackathon_id))
    hackathon = hackathon_result.scalar_one()

    qr_url = f"{settings.base_url}/api/checkin/scan?token={reg.qr_token}"
    pkpass = generate_apple_pass(
        registration_id=str(reg.id),
        participant_name=user.name,
        team_name=reg.team_name,
        hackathon_name=hackathon.name,
        start_date=hackathon.start_date.strftime("%Y-%m-%d"),
        end_date=hackathon.end_date.strftime("%Y-%m-%d"),
        qr_url=qr_url,
    )
    if not pkpass:
        raise HTTPException(status_code=503, detail="Wallet pass generation not configured")

    from fastapi.responses import Response
    return Response(
        content=pkpass,
        media_type="application/vnd.apple.pkpass",
        headers={"Content-Disposition": f'attachment; filename="checkin-{reg.id}.pkpass"'},
    )


@router.get("/registrations/{registration_id}/wallet/google")
async def get_google_wallet_link(
    registration_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Get Google Wallet save URL. Own registration only."""
    payload = _get_current_user_payload(authorization)
    user = await _get_user(db, payload["sub"])

    query = (
        select(Registration)
        .where(and_(Registration.id == registration_id, Registration.user_id == user.id))
    )
    result = await db.execute(query)
    reg = result.scalar_one_or_none()
    if not reg or reg.status != RegistrationStatus.accepted:
        raise HTTPException(status_code=404, detail="Not found or not accepted")

    from app.wallet.google import build_google_wallet_pass_object, get_google_wallet_save_url
    from app.config import settings

    hackathon_result = await db.execute(select(Hackathon).where(Hackathon.id == reg.hackathon_id))
    hackathon = hackathon_result.scalar_one()

    qr_url = f"{settings.base_url}/api/checkin/scan?token={reg.qr_token}"
    pass_obj = build_google_wallet_pass_object(
        registration_id=str(reg.id),
        participant_name=user.name,
        team_name=reg.team_name,
        hackathon_name=hackathon.name,
        start_date=hackathon.start_date.strftime("%Y-%m-%d"),
        end_date=hackathon.end_date.strftime("%Y-%m-%d"),
        qr_url=qr_url,
    )
    if not pass_obj:
        raise HTTPException(status_code=503, detail="Wallet pass generation not configured")

    save_url = get_google_wallet_save_url(pass_obj)
    if not save_url:
        raise HTTPException(status_code=503, detail="Wallet pass generation not configured")

    return {"save_url": save_url}
