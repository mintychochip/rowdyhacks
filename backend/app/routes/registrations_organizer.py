"""Organizer registration management routes."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Registration, RegistrationStatus, Hackathon, User, HackathonOrganizer
from app.auth import decode_token, create_qr_token

router = APIRouter(prefix="/api/hackathons", tags=["organizer-registrations"])


async def _get_organizer(authorization: str | None, db: AsyncSession) -> User:
    """Extract current user and verify organizer role."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Organizer authentication required")
    token = authorization.removeprefix("Bearer ")
    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if user.role.value != "organizer":
        raise HTTPException(status_code=403, detail="Organizer role required")
    return user


async def _verify_organizer_owns_hackathon(user: User, hackathon_id: uuid.UUID, db: AsyncSession) -> Hackathon:
    """Verify the organizer owns the hackathon or is a co-organizer."""
    # Primary organizer check
    query = select(Hackathon).where(
        and_(Hackathon.id == hackathon_id, Hackathon.organizer_id == user.id)
    )
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
        # Load the hackathon for the co-organizer
        hackathon_result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
        hackathon = hackathon_result.scalar_one_or_none()
        if hackathon:
            return hackathon
    
    raise HTTPException(status_code=404, detail="Hackathon not found")


@router.get("/{hackathon_id}/registrations")
async def list_hackathon_registrations(
    hackathon_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    status: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List registrations for a hackathon. Organizer only, RLS: own hackathons only."""
    user = await _get_organizer(authorization, db)
    hackathon = await _verify_organizer_owns_hackathon(user, hackathon_id, db)

    count_query = select(func.count(Registration.id)).where(Registration.hackathon_id == hackathon_id)
    query = select(Registration).where(Registration.hackathon_id == hackathon_id)

    if status:
        query = query.where(Registration.status == status)
        count_query = count_query.where(Registration.status == status)

    total = (await db.execute(count_query)).scalar()
    query = query.order_by(Registration.registered_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    registrations = result.scalars().all()

    # Fetch users for name/email
    user_ids = [r.user_id for r in registrations]
    users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
    users = {str(u.id): u for u in users_result.scalars().all()}

    return {
        "registrations": [
            {
                "id": str(r.id),
                "hackathon_id": str(r.hackathon_id),
                "user_id": str(r.user_id),
                "status": r.status.value,
                "team_name": r.team_name,
                "team_members": r.team_members,
                "registered_at": r.registered_at.isoformat(),
                "accepted_at": r.accepted_at.isoformat() if r.accepted_at else None,
                "checked_in_at": r.checked_in_at.isoformat() if r.checked_in_at else None,
                "user_name": users[str(r.user_id)].name if str(r.user_id) in users else None,
                "user_email": users[str(r.user_id)].email if str(r.user_id) in users else None,
            }
            for r in registrations
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/{hackathon_id}/registrations/{registration_id}/accept")
async def accept_registration(
    hackathon_id: uuid.UUID,
    registration_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Approve a registration and generate QR token. Organizer only."""
    user = await _get_organizer(authorization, db)
    hackathon = await _verify_organizer_owns_hackathon(user, hackathon_id, db)

    query = select(Registration).where(
        and_(Registration.id == registration_id, Registration.hackathon_id == hackathon_id)
    )
    result = await db.execute(query)
    reg = result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    if reg.status != RegistrationStatus.pending:
        raise HTTPException(status_code=409, detail=f"Cannot accept a {reg.status.value} registration")

    # Generate QR token
    qr_token = create_qr_token(
        registration_id=str(reg.id),
        user_id=str(reg.user_id),
        hackathon_id=str(hackathon.id),
        hackathon_end=hackathon.end_date,
    )
    reg.qr_token = qr_token
    reg.status = RegistrationStatus.accepted
    reg.accepted_at = datetime.now(timezone.utc)

    # Generate wallet passes (best-effort)
    try:
        from app.wallet.apple import generate_apple_pass
        from app.config import settings

        qr_url = f"{settings.base_url}/api/checkin/scan?token={qr_token}"
        user_result = await db.execute(select(User).where(User.id == reg.user_id))
        participant = user_result.scalar_one()

        apple_pass = generate_apple_pass(
            registration_id=str(reg.id),
            participant_name=participant.name,
            team_name=reg.team_name,
            hackathon_name=hackathon.name,
            start_date=hackathon.start_date.strftime("%Y-%m-%d"),
            end_date=hackathon.end_date.strftime("%Y-%m-%d"),
            qr_url=qr_url,
        )
        if apple_pass:
            reg.pass_serial_apple = str(reg.id)

        from app.wallet.google import build_google_wallet_pass_object, get_google_wallet_save_url
        google_pass = build_google_wallet_pass_object(
            registration_id=str(reg.id),
            participant_name=participant.name,
            team_name=reg.team_name,
            hackathon_name=hackathon.name,
            start_date=hackathon.start_date.strftime("%Y-%m-%d"),
            end_date=hackathon.end_date.strftime("%Y-%m-%d"),
            qr_url=qr_url,
        )
        if google_pass:
            save_url = get_google_wallet_save_url(google_pass)
            if save_url:
                reg.pass_id_google = f"{settings.google_wallet_issuer_id}.{reg.id}"
    except Exception:
        pass  # Wallet pass generation is best-effort, don't fail acceptance

    await db.commit()

    return {"id": str(reg.id), "status": reg.status.value, "qr_token": qr_token, "accepted_at": reg.accepted_at.isoformat()}


@router.post("/{hackathon_id}/registrations/{registration_id}/reject")
async def reject_registration(
    hackathon_id: uuid.UUID,
    registration_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Reject a registration. Organizer only."""
    user = await _get_organizer(authorization, db)
    hackathon = await _verify_organizer_owns_hackathon(user, hackathon_id, db)

    query = select(Registration).where(
        and_(Registration.id == registration_id, Registration.hackathon_id == hackathon_id)
    )
    result = await db.execute(query)
    reg = result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    if reg.status not in (RegistrationStatus.pending, RegistrationStatus.accepted):
        raise HTTPException(status_code=409, detail=f"Cannot reject a {reg.status.value} registration")

    reg.status = RegistrationStatus.rejected
    reg.qr_token = None  # invalidate QR
    await db.commit()

    return {"id": str(reg.id), "status": reg.status.value}


@router.post("/{hackathon_id}/registrations/{registration_id}/checkin")
async def checkin_registration(
    hackathon_id: uuid.UUID,
    registration_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Check in a registration. Organizer only."""
    user = await _get_organizer(authorization, db)
    hackathon = await _verify_organizer_owns_hackathon(user, hackathon_id, db)

    query = select(Registration).where(
        and_(Registration.id == registration_id, Registration.hackathon_id == hackathon_id)
    )
    result = await db.execute(query)
    reg = result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    if reg.status != RegistrationStatus.accepted:
        raise HTTPException(status_code=409, detail=f"Cannot check in a {reg.status.value} registration")

    reg.status = RegistrationStatus.checked_in
    reg.checked_in_at = datetime.now(timezone.utc)
    await db.commit()

    return {"id": str(reg.id), "status": reg.status.value, "checked_in_at": reg.checked_in_at.isoformat()}
