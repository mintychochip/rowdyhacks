"""Organizer registration management routes."""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_qr_token, decode_token
from app.database import get_db
from app.models import Hackathon, HackathonOrganizer, Registration, RegistrationStatus, User
from app.waitlist import promote_from_waitlist

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
                "user_role": users[str(r.user_id)].role.value if str(r.user_id) in users else None,
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
    reg.accepted_at = datetime.now(UTC)

    await db.commit()

    return {
        "id": str(reg.id),
        "status": reg.status.value,
        "qr_token": qr_token,
        "accepted_at": reg.accepted_at.isoformat(),
    }


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

    was_accepted = reg.status == RegistrationStatus.accepted
    reg.status = RegistrationStatus.rejected
    reg.qr_token = None  # invalidate QR

    # If rejecting an accepted registration, promote from waitlist
    if was_accepted:
        await db.flush()
        await promote_from_waitlist(hackathon_id, db)

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
    reg.checked_in_at = datetime.now(UTC)
    await db.commit()

    return {"id": str(reg.id), "status": reg.status.value, "checked_in_at": reg.checked_in_at.isoformat()}


@router.post("/{hackathon_id}/registrations/{registration_id}/waitlist")
async def move_to_waitlist(
    hackathon_id: uuid.UUID,
    registration_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Move a pending registration to waitlist. Organizer only."""
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
        raise HTTPException(status_code=409, detail=f"Cannot waitlist a {reg.status.value} registration")

    reg.status = RegistrationStatus.waitlisted
    await db.commit()

    return {"id": str(reg.id), "status": reg.status.value}


@router.post("/{hackathon_id}/registrations/{registration_id}/unwaitlist")
async def remove_from_waitlist(
    hackathon_id: uuid.UUID,
    registration_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Move a waitlisted registration back to pending. Organizer only."""
    user = await _get_organizer(authorization, db)
    hackathon = await _verify_organizer_owns_hackathon(user, hackathon_id, db)

    query = select(Registration).where(
        and_(Registration.id == registration_id, Registration.hackathon_id == hackathon_id)
    )
    result = await db.execute(query)
    reg = result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    if reg.status != RegistrationStatus.waitlisted:
        raise HTTPException(status_code=409, detail=f"Cannot unwaitlist a {reg.status.value} registration")

    reg.status = RegistrationStatus.pending
    reg.declined_count = 0
    await db.commit()

    return {"id": str(reg.id), "status": reg.status.value}


@router.post("/{hackathon_id}/waitlist/promote")
async def manual_promote_waitlist(
    hackathon_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Manually promote top waitlisted person to offered. Organizer only."""
    user = await _get_organizer(authorization, db)
    hackathon = await _verify_organizer_owns_hackathon(user, hackathon_id, db)

    promoted = await promote_from_waitlist(hackathon_id, db)
    if not promoted:
        raise HTTPException(status_code=409, detail="No one to promote or hackathon at capacity")

    return {
        "id": str(promoted.id),
        "status": promoted.status.value,
        "offer_expires_at": promoted.offer_expires_at.isoformat(),
    }


@router.get("/{hackathon_id}/waitlist")
async def list_waitlist(
    hackathon_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List waitlisted registrations with position. Organizer only."""
    user = await _get_organizer(authorization, db)
    hackathon = await _verify_organizer_owns_hackathon(user, hackathon_id, db)

    # Get waitlist ordered by priority
    result = await db.execute(
        select(Registration)
        .where(Registration.hackathon_id == hackathon_id)
        .where(Registration.status == RegistrationStatus.waitlisted)
        .order_by(Registration.declined_count.asc(), Registration.registered_at.asc())
        .offset(offset)
        .limit(limit)
    )
    registrations = result.scalars().all()

    # Get users
    user_ids = [r.user_id for r in registrations]
    users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
    users = {str(u.id): u for u in users_result.scalars().all()}

    # Calculate positions (1-indexed)
    base_position = offset + 1
    return {
        "waitlist": [
            {
                "id": str(r.id),
                "position": base_position + idx,
                "user_name": users.get(str(r.user_id)).name if str(r.user_id) in users else None,
                "user_email": users.get(str(r.user_id)).email if str(r.user_id) in users else None,
                "registered_at": r.registered_at.isoformat(),
                "declined_count": r.declined_count or 0,
                "dietary_restrictions": r.dietary_restrictions,
                "t_shirt_size": r.t_shirt_size,
            }
            for idx, r in enumerate(registrations)
        ],
        "total": len(registrations),
        "offset": offset,
        "limit": limit,
    }
