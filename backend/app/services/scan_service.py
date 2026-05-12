"""QR scan and check-in service.

Encapsulates the business logic for scanning QR tokens and performing
organizer-initiated check-ins, including state validation and token decoding.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import decode_qr_token
from app.models import Registration, RegistrationStatus


class ScanError(Exception):
    """Base exception for scan/check-in failures.

    Attributes:
        status_code: HTTP status code that should be returned to the client.
        error_code: Machine-readable error identifier.
        message: Human-readable error description.
    """

    def __init__(self, status_code: int, error_code: str, message: str):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        super().__init__(message)


class ScanService:
    """Service for QR scanning and registration check-in operations."""

    async def scan_qr_token(self, db: AsyncSession, token: str) -> dict:
        """Decode a QR token and check in the associated registration.

        Behavior:
        1. Decode and validate the QR JWT token.
        2. Extract reg_id from the token payload.
        3. Load the registration by ID.
        4. Validate registration state (accepted, not already checked in, not rejected).
        5. Update status to checked_in and set checked_in_at timestamp.
        6. Commit and return registration details.

        Raises: ScanError with appropriate status_code and error_code.
        Side Effects: Mutates Registration.status and Registration.checked_in_at; commits to DB.
        """
        try:
            payload = decode_qr_token(token)
        except ValueError as e:
            raise ScanError(401, "invalid_token", str(e)) from e

        reg_id = payload.get("reg_id")
        if not reg_id:
            raise ScanError(401, "invalid_token", "Missing registration ID in token")

        result = await db.execute(select(Registration).where(Registration.id == reg_id))
        reg = result.scalar_one_or_none()
        if not reg:
            raise ScanError(410, "registration_not_found", "Registration not found")

        if reg.status == RegistrationStatus.checked_in:
            raise ScanError(409, "already_checked_in", "Registration already checked in")
        if reg.status == RegistrationStatus.rejected:
            raise ScanError(410, "registration_revoked", "Registration has been revoked")
        if reg.status != RegistrationStatus.accepted:
            raise ScanError(409, "registration_not_active", "Registration is not active")

        reg.status = RegistrationStatus.checked_in
        reg.checked_in_at = datetime.now(UTC)
        await db.commit()

        return {
            "id": str(reg.id),
            "status": reg.status.value,
            "checked_in_at": reg.checked_in_at.isoformat(),
            "user_id": str(reg.user_id),
        }

    async def checkin_registration(
        self,
        db: AsyncSession,
        hackathon_id: UUID,
        registration_id: UUID,
    ) -> dict:
        """Organizer-initiated check-in for a specific registration.

        Behavior:
        1. Load the registration by id and hackathon_id.
        2. Raise ScanError(404) if the registration is not found.
        3. Raise ScanError(409) if the registration is not accepted.
        4. Update status to checked_in and set checked_in_at.
        5. Commit and return the updated registration details.

        Raises: ScanError with appropriate status_code and error_code.
        Side Effects: Mutates Registration.status and checked_in_at; commits to DB.
        """
        result = await db.execute(
            select(Registration).where(
                Registration.id == registration_id,
                Registration.hackathon_id == hackathon_id,
            )
        )
        reg = result.scalar_one_or_none()
        if not reg:
            raise ScanError(404, "registration_not_found", "Registration not found")

        if reg.status != RegistrationStatus.accepted:
            raise ScanError(
                409,
                "registration_not_active",
                f"Cannot check in a {reg.status.value} registration",
            )

        reg.status = RegistrationStatus.checked_in
        reg.checked_in_at = datetime.now(UTC)
        await db.commit()

        return {
            "id": str(reg.id),
            "status": reg.status.value,
            "checked_in_at": reg.checked_in_at.isoformat(),
            "user_id": str(reg.user_id),
        }
