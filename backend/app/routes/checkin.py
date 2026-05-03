"""QR code check-in scan endpoint."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import decode_qr_token
from app.database import get_db
from app.models import Registration, RegistrationStatus

router = APIRouter(prefix="/api/checkin", tags=["checkin"])


@router.post("/scan")
async def scan_qr(
    token: str = Query(..., description="QR JWT token"),
    db: AsyncSession = Depends(get_db),
):
    """Scan a QR code to check in. Token is validated from JWT signature."""
    # Step 1: Validate QR token
    try:
        payload = decode_qr_token(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail={"error": "invalid_token", "message": str(e)})

    reg_id = payload.get("reg_id")
    if not reg_id:
        raise HTTPException(status_code=401, detail={"error": "invalid_token"})

    # Step 2: Load registration
    result = await db.execute(select(Registration).where(Registration.id == reg_id))
    reg = result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=410, detail={"error": "registration_not_found"})

    # Step 3: Validate state
    if reg.status == RegistrationStatus.checked_in:
        raise HTTPException(status_code=409, detail={"error": "already_checked_in"})
    if reg.status == RegistrationStatus.rejected:
        raise HTTPException(status_code=410, detail={"error": "registration_revoked"})
    if reg.status != RegistrationStatus.accepted:
        raise HTTPException(status_code=409, detail={"error": "registration_not_active"})

    # Step 4: Check in
    reg.status = RegistrationStatus.checked_in
    reg.checked_in_at = datetime.now(UTC)
    await db.commit()

    return {
        "id": str(reg.id),
        "status": reg.status.value,
        "checked_in_at": reg.checked_in_at.isoformat(),
    }
