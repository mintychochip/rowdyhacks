"""QR code check-in scan endpoint."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.scan_service import ScanError, ScanService

router = APIRouter(prefix="/api/checkin", tags=["checkin"])

scan_service = ScanService()


@router.post("/scan")
async def scan_qr(
    token: str = Query(..., description="QR JWT token"),
    db: AsyncSession = Depends(get_db),
):
    """Scan a QR code to check in a registered participant.

    Behavior:
    1. Decode and validate the QR JWT token.
    2. Extract reg_id from the token payload.
    3. Load the registration by ID.
    4. Validate registration state (accepted, not already checked in, not rejected).
    5. Update status to checked_in and set checked_in_at timestamp.
    6. Commit and return registration details.

    Raises: HTTPException(401) for invalid token, HTTPException(410) for missing or revoked registration, HTTPException(409) for already checked in or not active.
    Side Effects: Mutates Registration.status and Registration.checked_in_at; commits to DB.
    Dependencies: app.services.scan_service.ScanService.
    Consumers: POST /api/checkin/scan, check-in scanner UI.
    """
    try:
        return await scan_service.scan_qr_token(db, token)
    except ScanError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": e.error_code, "message": e.message},
        ) from e
