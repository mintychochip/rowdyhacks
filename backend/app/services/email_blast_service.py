"""Bulk email/announcement blast service for hackathon organizers.

Provides targeted email delivery to different registrant cohorts
(accepted, waitlisted, checked-in, or track-specific) using the
existing email delivery infrastructure.
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.email_service import send_email_with_retry
from app.models import Registration, RegistrationStatus


class EmailBlastService:
    """Service for sending bulk emails to hackathon registrant cohorts.

    All send methods iterate over a targeted subset of registrations,
    extract the associated user email, and dispatch via
    ``send_email_with_retry``. Results are summarized and returned
    to the caller without blocking on each individual delivery.
    """

    async def send_bulk_email(
        self,
        db: AsyncSession,
        hackathon_id: uuid.UUID,
        subject: str,
        body: str,
        sender_id: str,
    ) -> dict[str, Any]:
        """Send an email to all accepted registrants of a hackathon.

        Behavior:
        1. Query registrations where status is ``accepted``.
        2. Eagerly load the associated User rows to read email addresses.
        3. Iterate over the results and dispatch one email per registrant.
        4. Count successes and failures and return a summary dict.

        Raises: None
        Side Effects: Triggers outbound emails via ``send_email_with_retry``.
        Dependencies: app.models.Registration, app.models.User, app.email_service.send_email_with_retry.
        Consumers: POST /api/hackathons/{id}/email-blast organizer route.
        """
        result = await db.execute(
            select(Registration)
            .options(selectinload(Registration.user))
            .where(
                Registration.hackathon_id == hackathon_id,
                Registration.status == RegistrationStatus.accepted,
            )
        )
        registrations = result.scalars().all()

        sent = 0
        failed = 0
        for reg in registrations:
            email = reg.user.email if reg.user else None
            if not email:
                failed += 1
                continue
            success = await send_email_with_retry(
                to_email=email,
                email_type="custom_blast",
                context={"subject": subject, "body": body, "name": reg.user.name or "Hacker"},
            )
            if success:
                sent += 1
            else:
                failed += 1

        return {"sent": sent, "failed": failed, "cohort": "accepted"}

    async def send_to_waitlist(
        self,
        db: AsyncSession,
        hackathon_id: uuid.UUID,
        subject: str,
        body: str,
        sender_id: str,
    ) -> dict[str, Any]:
        """Send an email to all waitlisted registrants of a hackathon.

        Behavior:
        1. Query registrations where status is ``waitlisted``.
        2. Eagerly load the associated User rows.
        3. Dispatch one email per waitlisted registrant.
        4. Return a summary dict with sent/failed counts.

        Raises: None
        Side Effects: Triggers outbound emails.
        Dependencies: app.models.Registration, app.models.User, app.email_service.send_email_with_retry.
        """
        result = await db.execute(
            select(Registration)
            .options(selectinload(Registration.user))
            .where(
                Registration.hackathon_id == hackathon_id,
                Registration.status == RegistrationStatus.waitlisted,
            )
        )
        registrations = result.scalars().all()

        sent = 0
        failed = 0
        for reg in registrations:
            email = reg.user.email if reg.user else None
            if not email:
                failed += 1
                continue
            success = await send_email_with_retry(
                to_email=email,
                email_type="custom_blast",
                context={"subject": subject, "body": body, "name": reg.user.name or "Hacker"},
            )
            if success:
                sent += 1
            else:
                failed += 1

        return {"sent": sent, "failed": failed, "cohort": "waitlist"}

    async def send_to_checked_in(
        self,
        db: AsyncSession,
        hackathon_id: uuid.UUID,
        subject: str,
        body: str,
        sender_id: str,
    ) -> dict[str, Any]:
        """Send an email to all checked-in participants of a hackathon.

        Behavior:
        1. Query registrations where status is ``checked_in``.
        2. Eagerly load the associated User rows.
        3. Dispatch one email per checked-in participant.
        4. Return a summary dict with sent/failed counts.

        Raises: None
        Side Effects: Triggers outbound emails.
        Dependencies: app.models.Registration, app.models.User, app.email_service.send_email_with_retry.
        """
        result = await db.execute(
            select(Registration)
            .options(selectinload(Registration.user))
            .where(
                Registration.hackathon_id == hackathon_id,
                Registration.status == RegistrationStatus.checked_in,
            )
        )
        registrations = result.scalars().all()

        sent = 0
        failed = 0
        for reg in registrations:
            email = reg.user.email if reg.user else None
            if not email:
                failed += 1
                continue
            success = await send_email_with_retry(
                to_email=email,
                email_type="custom_blast",
                context={"subject": subject, "body": body, "name": reg.user.name or "Hacker"},
            )
            if success:
                sent += 1
            else:
                failed += 1

        return {"sent": sent, "failed": failed, "cohort": "checked_in"}

    async def send_to_track(
        self,
        db: AsyncSession,
        hackathon_id: uuid.UUID,
        track_id: uuid.UUID,
        subject: str,
        body: str,
        sender_id: str,
    ) -> dict[str, Any]:
        """Send an email to participants registered for a specific track.

        Behavior:
        1. Query accepted registrations where ``track_id`` matches the given track.
        2. Eagerly load the associated User rows.
        3. Dispatch one email per matching registrant.
        4. Return a summary dict with sent/failed counts.

        Raises: None
        Side Effects: Triggers outbound emails.
        Dependencies: app.models.Registration, app.models.User, app.email_service.send_email_with_retry.
        """
        result = await db.execute(
            select(Registration)
            .options(selectinload(Registration.user))
            .where(
                Registration.hackathon_id == hackathon_id,
                Registration.track_id == track_id,
                Registration.status == RegistrationStatus.accepted,
            )
        )
        registrations = result.scalars().all()

        sent = 0
        failed = 0
        for reg in registrations:
            email = reg.user.email if reg.user else None
            if not email:
                failed += 1
                continue
            success = await send_email_with_retry(
                to_email=email,
                email_type="custom_blast",
                context={"subject": subject, "body": body, "name": reg.user.name or "Hacker"},
            )
            if success:
                sent += 1
            else:
                failed += 1

        return {"sent": sent, "failed": failed, "cohort": "track"}
