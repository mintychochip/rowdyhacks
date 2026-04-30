"""Hacker Dashboard endpoint — live event view for participants."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Registration, Hackathon
from app.routes.registrations import _get_current_user_payload

router = APIRouter(prefix="/api/hackathons", tags=["hacker-dashboard"])


@router.get("/{hackathon_id}/hacker-dashboard")
async def get_hacker_dashboard(
    hackathon_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Get the hacker dashboard for the current user's registration at a hackathon.

    Returns hackathon details (schedule, wifi, discord) + registration (QR, scan_count, scans).
    """
    payload = _get_current_user_payload(authorization)

    # Load hackathon
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    # Load user's registration for this hackathon
    reg_result = await db.execute(
        select(Registration)
        .where(Registration.hackathon_id == hackathon_id, Registration.user_id == payload["sub"])
        .options(selectinload(Registration.scans))
        .options(selectinload(Registration.user))
    )
    reg = reg_result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found. Register for this hackathon first.")

    # Count scans
    scan_count = len(reg.scans) if reg.scans else 0

    # Build scan list
    scans = sorted(
        [
            {
                "id": str(s.id),
                "scan_type": s.scan_type,
                "scanned_at": s.scanned_at.isoformat(),
            }
            for s in (reg.scans or [])
        ],
        key=lambda x: x["scanned_at"],
        reverse=True,
    )

    return {
        "hackathon": {
            "id": str(hackathon.id),
            "name": hackathon.name,
            "start_date": hackathon.start_date.isoformat(),
            "end_date": hackathon.end_date.isoformat(),
            "description": hackathon.description,
            "schedule": hackathon.schedule,
            "wifi_ssid": hackathon.wifi_ssid,
            "wifi_password": hackathon.wifi_password,
            "discord_invite_url": hackathon.discord_invite_url,
        },
        "registration": {
            "id": str(reg.id),
            "status": reg.status.value,
            "team_name": reg.team_name,
            "team_members": reg.team_members,
            "linkedin_url": reg.linkedin_url,
            "github_url": reg.github_url,
            "resume_url": reg.resume_url,
            "experience_level": reg.experience_level,
            "t_shirt_size": reg.t_shirt_size,
            "phone": reg.phone,
            "dietary_restrictions": reg.dietary_restrictions,
            "what_build": reg.what_build,
            "why_participate": reg.why_participate,
            "qr_token": reg.qr_token,
            "registered_at": reg.registered_at.isoformat(),
            "accepted_at": reg.accepted_at.isoformat() if reg.accepted_at else None,
            "checked_in_at": reg.checked_in_at.isoformat() if reg.checked_in_at else None,
            "scan_count": scan_count,
            "scans": scans,
        },
    }
