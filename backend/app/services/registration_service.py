"""Registration management service.

Encapsulates all business logic for hackathon registrations, including
participant signup, organizer acceptance/rejection, waitlist management,
check-in, bulk operations, and CSV export.
"""

import csv
import io
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import create_qr_token
from app.models import Hackathon, Registration, RegistrationAnswer, RegistrationStatus, User
from app.waitlist import promote_from_waitlist


def _safe_load_answers(r: Registration) -> list[dict]:
    """Safely serialize registration answers without triggering async lazy loads.

    Behavior:
    1. Try to iterate over the answers collection.
    2. If lazy loading fails (e.g., in sync context or detached object), return [].
    3. Return the serialized answer list on success.

    Side Effects: None (read-only, guarded against IO).
    """
    try:
        return [
            {
                "question_id": str(a.question_id),
                "question_text": a.question.question_text if a.question else None,
                "question_type": a.question.question_type.value if a.question else None,
                "value": a.answer_value,
            }
            for a in (getattr(r, "answers", None) or [])
        ]
    except Exception:
        return []


class RegistrationService:
    """Service for managing hackathon registrations."""

    @staticmethod
    def registration_to_response(r: Registration, user: User | None = None) -> dict:
        """Serialize a Registration model to a response dict.

        Behavior:
        1. Extract all fields from the Registration ORM instance.
        2. Add user_name and user_email if the optional User is provided.
        3. Return the assembled dict.

        Side Effects: None (read-only).
        Dependencies: None.
        """
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
            "user_role": user.role.value if user else None,
            "answers": _safe_load_answers(r),
        }

    async def list_registrations_for_hackathon(
        self,
        db: AsyncSession,
        hackathon_id: uuid.UUID,
        status: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> dict:
        """List registrations for a hackathon with optional status filter.

        Behavior:
        1. Build count and list queries filtered by hackathon_id.
        2. Validate the optional status filter.
        3. Fetch registrations with eager-loaded users.
        4. Return the registration list with pagination metadata.

        Raises: HTTPException(422) if invalid status filter.
        Side Effects: None (read-only).
        """
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
            .options(selectinload(Registration.answers).selectinload(RegistrationAnswer.question))
            .order_by(Registration.registered_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(query)
        registrations = result.scalars().all()

        return {
            "registrations": [self.registration_to_response(r, r.user) for r in registrations],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def list_registrations_for_user(
        self,
        db: AsyncSession,
        user_id: str,
        offset: int = 0,
        limit: int = 20,
    ) -> dict:
        """List registrations for a specific user.

        Behavior:
        1. Count and query registrations filtered by user_id.
        2. Fetch registrations with eager-loaded users.
        3. Return the registration list with pagination metadata.

        Raises: None.
        Side Effects: None (read-only).
        """
        count_query = select(func.count(Registration.id)).where(Registration.user_id == user_id)
        total = (await db.execute(count_query)).scalar()

        query = (
            select(Registration)
            .where(Registration.user_id == user_id)
            .options(selectinload(Registration.user))
            .options(selectinload(Registration.answers).selectinload(RegistrationAnswer.question))
            .order_by(Registration.registered_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(query)
        registrations = result.scalars().all()

        return {
            "registrations": [self.registration_to_response(r, r.user) for r in registrations],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def get_registration(
        self,
        db: AsyncSession,
        registration_id: uuid.UUID,
        user_id: str | None = None,
    ) -> Registration:
        """Load a single registration by ID with optional user filtering.

        Behavior:
        1. Build a query by registration id and optional user_id.
        2. Eager-load the associated user.
        3. Raise 404 if the registration is not found.
        4. Return the Registration instance.

        Raises: HTTPException(404) if registration not found.
        Side Effects: None (read-only).
        """
        query = (
            select(Registration)
            .where(Registration.id == registration_id)
            .options(selectinload(Registration.user))
            .options(selectinload(Registration.answers).selectinload(RegistrationAnswer.question))
        )
        if user_id:
            query = query.where(Registration.user_id == user_id)

        result = await db.execute(query)
        reg = result.scalar_one_or_none()
        if not reg:
            raise HTTPException(status_code=404, detail="Registration not found")
        return reg

    async def create_registration(
        self,
        db: AsyncSession,
        hackathon_id: uuid.UUID,
        user_id: str,
        body,
    ) -> Registration:
        """Create a new registration for a user on a hackathon.

        Behavior:
        1. Check for duplicate registration and raise 409 if found.
        2. Determine if auto-waitlist is needed based on capacity.
        3. Create a Registration with the appropriate initial status.
        4. Commit and refresh.
        5. Return the registration.

        Raises: HTTPException(400) if at capacity without waitlist.
                HTTPException(409) if already registered.
        Side Effects: Inserts Registration row; may increment Hackathon.current_participants.
        """
        from app.waitlist import auto_waitlist_if_full

        # Check for duplicate registration
        existing = await db.execute(
            select(Registration).where(and_(Registration.hackathon_id == hackathon_id, Registration.user_id == user_id))
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Already registered for this hackathon")

        # Check if should auto-waitlist
        should_waitlist = await auto_waitlist_if_full(hackathon_id, db)
        if should_waitlist:
            hackathon = await db.get(Hackathon, hackathon_id)
            if not hackathon or not hackathon.waitlist_enabled:
                raise HTTPException(status_code=400, detail="Hackathon is at capacity")
            initial_status = RegistrationStatus.waitlisted
        else:
            initial_status = RegistrationStatus.pending

        reg = Registration(
            hackathon_id=hackathon_id,
            user_id=user_id,
            status=initial_status,
            team_name=getattr(body, "team_name", None),
            team_members=getattr(body, "team_members", None),
            linkedin_url=getattr(body, "linkedin_url", None),
            github_url=getattr(body, "github_url", None),
            resume_url=getattr(body, "resume_url", None),
            experience_level=getattr(body, "experience_level", None),
            t_shirt_size=getattr(body, "t_shirt_size", None),
            phone=getattr(body, "phone", None),
            dietary_restrictions=getattr(body, "dietary_restrictions", None),
            what_build=getattr(body, "what_build", None),
            why_participate=getattr(body, "why_participate", None),
            age=getattr(body, "age", None),
            school=getattr(body, "school", None),
            major=getattr(body, "major", None),
            pronouns=getattr(body, "pronouns", None),
            skills=getattr(body, "skills", None),
            emergency_contact_name=getattr(body, "emergency_contact_name", None),
            emergency_contact_phone=getattr(body, "emergency_contact_phone", None),
        )
        db.add(reg)

        if initial_status == RegistrationStatus.waitlisted:
            hackathon = await db.get(Hackathon, hackathon_id)
            if hackathon:
                hackathon.current_participants += 1

        await db.commit()
        await db.refresh(reg)
        return reg

    async def accept_registration(
        self,
        db: AsyncSession,
        hackathon_id: uuid.UUID,
        registration_id: uuid.UUID,
        *,
        hackathon: Hackathon | None = None,
        check_capacity: bool = False,
        increment_participants: bool = False,
        generate_qr: bool = False,
    ) -> Registration:
        """Accept a pending or waitlisted registration.

        Behavior:
        1. Load the registration by id and hackathon_id.
        2. Raise 404 if not found.
        3. Raise 409 if status is not pending or waitlisted.
        4. Optionally check capacity and increment current_participants.
        5. Optionally generate a QR token.
        6. Update status to accepted and set accepted_at.
        7. Commit and refresh.
        8. Return the updated registration.

        Raises: HTTPException(404) if registration not found.
                HTTPException(409) if registration not acceptable.
                HTTPException(400) if at capacity.
        Side Effects: Mutates Registration status, accepted_at, qr_token; may increment Hackathon.current_participants.
        """
        result = await db.execute(
            select(Registration)
            .where(
                and_(
                    Registration.id == registration_id,
                    Registration.hackathon_id == hackathon_id,
                )
            )
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

        if check_capacity and reg.status == RegistrationStatus.pending:
            if not hackathon:
                hackathon = await db.get(Hackathon, hackathon_id)
            if (
                hackathon
                and hackathon.max_participants
                and hackathon.current_participants >= hackathon.max_participants
            ):
                raise HTTPException(status_code=400, detail="Hackathon is at capacity. Consider enabling waitlist.")
            if increment_participants and hackathon:
                hackathon.current_participants += 1

        reg.status = RegistrationStatus.accepted
        reg.accepted_at = datetime.now(UTC)

        if generate_qr:
            if not hackathon:
                hackathon = await db.get(Hackathon, hackathon_id)
            reg.qr_token = create_qr_token(
                registration_id=str(reg.id),
                user_id=str(reg.user_id),
                hackathon_id=str(hackathon_id),
                hackathon_end=hackathon.end_date if hackathon else None,
            )

        await db.commit()
        await db.refresh(reg)
        return reg

    async def reject_registration(
        self,
        db: AsyncSession,
        hackathon_id: uuid.UUID,
        registration_id: uuid.UUID,
        *,
        promote_waitlist: bool = False,
    ) -> Registration:
        """Reject a pending or accepted registration.

        Behavior:
        1. Load the registration by id and hackathon_id.
        2. Raise 404 if not found.
        3. Raise 409 if status is not pending or accepted.
        4. Update status to rejected and invalidate the QR token.
        5. Optionally promote from waitlist if the registration was accepted.
        6. Commit and return the updated registration.

        Raises: HTTPException(404) if registration not found.
                HTTPException(409) if registration not rejectable.
        Side Effects: Mutates Registration status and qr_token; may trigger waitlist promotion.
        """
        result = await db.execute(
            select(Registration).where(
                and_(Registration.id == registration_id, Registration.hackathon_id == hackathon_id)
            )
        )
        reg = result.scalar_one_or_none()
        if not reg:
            raise HTTPException(status_code=404, detail="Registration not found")

        if reg.status not in (RegistrationStatus.pending, RegistrationStatus.accepted):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot reject registration with status '{reg.status.value}'; only pending or accepted registrations can be rejected",
            )

        was_accepted = reg.status == RegistrationStatus.accepted
        reg.status = RegistrationStatus.rejected
        reg.qr_token = None

        if promote_waitlist and was_accepted:
            await db.flush()
            await promote_from_waitlist(hackathon_id, db)

        await db.commit()
        return reg

    async def checkin_registration(
        self,
        db: AsyncSession,
        hackathon_id: uuid.UUID,
        registration_id: uuid.UUID,
    ) -> Registration:
        """Check in an accepted registration.

        Behavior:
        1. Load the registration by id and hackathon_id.
        2. Raise 404 if not found.
        3. Raise 409 if status is not accepted.
        4. Update status to checked_in and set checked_in_at.
        5. Commit and return the updated registration.

        Raises: HTTPException(404) if registration not found.
                HTTPException(409) if registration not accepted.
        Side Effects: Mutates Registration status and checked_in_at.
        """
        result = await db.execute(
            select(Registration).where(
                and_(Registration.id == registration_id, Registration.hackathon_id == hackathon_id)
            )
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
        reg.checked_in_at = datetime.now(UTC)
        await db.commit()
        return reg

    async def waitlist_registration(
        self,
        db: AsyncSession,
        hackathon_id: uuid.UUID,
        registration_id: uuid.UUID,
    ) -> Registration:
        """Move a pending registration to waitlist.

        Behavior:
        1. Load the registration by id and hackathon_id.
        2. Raise 404 if not found.
        3. Raise 409 if status is not pending.
        4. Update status to waitlisted.
        5. Commit and return the updated registration.

        Raises: HTTPException(404) if registration not found.
                HTTPException(409) if registration not pending.
        Side Effects: Mutates Registration status.
        """
        result = await db.execute(
            select(Registration).where(
                and_(Registration.id == registration_id, Registration.hackathon_id == hackathon_id)
            )
        )
        reg = result.scalar_one_or_none()
        if not reg:
            raise HTTPException(status_code=404, detail="Registration not found")
        if reg.status != RegistrationStatus.pending:
            raise HTTPException(status_code=409, detail=f"Cannot waitlist a {reg.status.value} registration")

        reg.status = RegistrationStatus.waitlisted
        await db.commit()
        return reg

    async def unwaitlist_registration(
        self,
        db: AsyncSession,
        hackathon_id: uuid.UUID,
        registration_id: uuid.UUID,
    ) -> Registration:
        """Move a waitlisted registration back to pending.

        Behavior:
        1. Load the registration by id and hackathon_id.
        2. Raise 404 if not found.
        3. Raise 409 if status is not waitlisted.
        4. Update status to pending and reset declined_count.
        5. Commit and return the updated registration.

        Raises: HTTPException(404) if registration not found.
                HTTPException(409) if registration not waitlisted.
        Side Effects: Mutates Registration status and declined_count.
        """
        result = await db.execute(
            select(Registration).where(
                and_(Registration.id == registration_id, Registration.hackathon_id == hackathon_id)
            )
        )
        reg = result.scalar_one_or_none()
        if not reg:
            raise HTTPException(status_code=404, detail="Registration not found")
        if reg.status != RegistrationStatus.waitlisted:
            raise HTTPException(status_code=409, detail=f"Cannot unwaitlist a {reg.status.value} registration")

        reg.status = RegistrationStatus.pending
        reg.declined_count = 0
        await db.commit()
        return reg

    async def manual_promote_waitlist(
        self,
        db: AsyncSession,
        hackathon_id: uuid.UUID,
    ) -> Registration:
        """Manually promote the top waitlisted person to offered.

        Behavior:
        1. Call promote_from_waitlist for the hackathon.
        2. Raise 409 if no one is available to promote or the hackathon is at capacity.
        3. Return the promoted registration.

        Raises: HTTPException(409) if no one to promote or at capacity.
        Side Effects: Mutates Registration status and offer_expires_at via waitlist promotion.
        """
        promoted = await promote_from_waitlist(hackathon_id, db)
        if not promoted:
            raise HTTPException(status_code=409, detail="No one to promote or hackathon at capacity")
        return promoted

    async def list_waitlist(
        self,
        db: AsyncSession,
        hackathon_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> dict:
        """List waitlisted registrations with position.

        Behavior:
        1. Query waitlisted registrations ordered by priority.
        2. Load associated users for name/email enrichment.
        3. Calculate waitlist positions.
        4. Return the waitlist with pagination metadata.

        Raises: None.
        Side Effects: None (read-only).
        """
        result = await db.execute(
            select(Registration)
            .where(Registration.hackathon_id == hackathon_id)
            .where(Registration.status == RegistrationStatus.waitlisted)
            .order_by(Registration.declined_count.asc(), Registration.registered_at.asc())
            .offset(offset)
            .limit(limit)
        )
        registrations = result.scalars().all()

        user_ids = [r.user_id for r in registrations]
        users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        users = {str(u.id): u for u in users_result.scalars().all()}

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

    async def accept_offer(
        self,
        db: AsyncSession,
        registration_id: uuid.UUID,
        user_id: str,
    ) -> Registration:
        """Participant accepts an offered spot from waitlist promotion.

        Behavior:
        1. Lock and load the registration by id and user_id.
        2. Raise 404 if not found.
        3. Raise 409 if not in offered status.
        4. Raise 410 if the offer has expired.
        5. Check capacity one more time; revert to waitlist if the spot is taken.
        6. Update status to accepted, set accepted_at, and generate a QR token.
        7. Commit and send a confirmation email.
        8. Return the updated registration.

        Raises: HTTPException(404, 409, 410).
        Side Effects: Mutates Registration; sends email.
        """
        from app.auth import create_qr_token
        from app.email_service import send_email

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
        if reg.offer_expires_at and reg.offer_expires_at < datetime.now(UTC):
            raise HTTPException(status_code=410, detail="Offer has expired")

        hackathon = await db.get(Hackathon, reg.hackathon_id)
        accepted_count = await db.execute(
            select(func.count(Registration.id))
            .where(Registration.hackathon_id == reg.hackathon_id)
            .where(Registration.status == RegistrationStatus.accepted)
        )

        if accepted_count.scalar() >= hackathon.max_participants:
            reg.status = RegistrationStatus.waitlisted
            reg.offer_expires_at = None
            await db.commit()
            raise HTTPException(status_code=409, detail="Spot no longer available")

        reg.status = RegistrationStatus.accepted
        reg.accepted_at = datetime.now(UTC)
        reg.offer_expires_at = None
        reg.qr_token = create_qr_token(
            registration_id=str(reg.id),
            user_id=str(reg.user_id),
            hackathon_id=str(reg.hackathon_id),
            hackathon_end=hackathon.end_date,
        )

        await db.commit()

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
                db=db,
            )

        return reg

    async def decline_offer(
        self,
        db: AsyncSession,
        registration_id: uuid.UUID,
        user_id: str,
    ) -> Registration:
        """Participant declines an offered spot. Returns to waitlist with lower priority.

        Behavior:
        1. Load the registration by id and user_id.
        2. Raise 404 if not found.
        3. Raise 409 if not in offered status.
        4. Update status to waitlisted, clear offer_expires_at, and increment declined_count.
        5. Flush and trigger promotion of the next waitlisted person.
        6. Commit and return the updated registration.

        Raises: HTTPException(404, 409).
        Side Effects: Mutates Registration; triggers waitlist promotion.
        """
        result = await db.execute(
            select(Registration).where(Registration.id == registration_id).where(Registration.user_id == user_id)
        )
        reg = result.scalar_one_or_none()

        if not reg:
            raise HTTPException(status_code=404, detail="Registration not found")
        if reg.status != RegistrationStatus.offered:
            raise HTTPException(status_code=409, detail=f"Cannot decline a {reg.status.value} registration")

        reg.status = RegistrationStatus.waitlisted
        reg.offer_expires_at = None
        reg.declined_count = (reg.declined_count or 0) + 1

        await db.flush()
        await promote_from_waitlist(reg.hackathon_id, db)

        await db.commit()
        return reg

    async def bulk_accept(
        self,
        db: AsyncSession,
        hackathon_id: uuid.UUID,
        registration_ids: list[uuid.UUID],
    ) -> dict:
        """Bulk accept pending registrations with capacity and waitlist handling.

        Behavior:
        1. Load the hackathon.
        2. For each pending registration ID, skip if not pending or not in this hackathon.
        3. If at capacity and waitlist enabled, move to waitlisted.
        4. If at capacity and waitlist disabled, skip.
        5. Otherwise accept, increment current_participants, and set accepted_at.
        6. Commit and return accepted and waitlisted counts.

        Raises: HTTPException(404) if hackathon not found.
        Side Effects: Mutates Registration rows and Hackathon.current_participants.
        """
        hackathon = await db.get(Hackathon, hackathon_id)
        if not hackathon:
            raise HTTPException(status_code=404, detail="Hackathon not found")

        accepted_count = 0
        waitlisted_count = 0

        for reg_id in registration_ids:
            reg_result = await db.execute(
                select(Registration).where(and_(Registration.id == reg_id, Registration.hackathon_id == hackathon_id))
            )
            reg = reg_result.scalar_one_or_none()
            if not reg or reg.status != RegistrationStatus.pending:
                continue

            if hackathon.max_participants and hackathon.current_participants >= hackathon.max_participants:
                if hackathon.waitlist_enabled:
                    reg.status = RegistrationStatus.waitlisted
                    waitlisted_count += 1
                else:
                    continue
            else:
                reg.status = RegistrationStatus.accepted
                reg.accepted_at = datetime.now(UTC)
                hackathon.current_participants += 1
                accepted_count += 1

        await db.commit()
        return {"accepted": accepted_count, "waitlisted": waitlisted_count}

    async def bulk_reject(
        self,
        db: AsyncSession,
        hackathon_id: uuid.UUID,
        registration_ids: list[uuid.UUID],
    ) -> dict:
        """Bulk reject pending or waitlisted registrations.

        Behavior:
        1. For each registration ID, skip if not pending or waitlisted.
        2. Set status to rejected for matching registrations.
        3. Commit and return the rejected count.

        Raises: None.
        Side Effects: Mutates Registration.status.
        """
        rejected_count = 0

        for reg_id in registration_ids:
            reg_result = await db.execute(
                select(Registration).where(and_(Registration.id == reg_id, Registration.hackathon_id == hackathon_id))
            )
            reg = reg_result.scalar_one_or_none()
            if not reg or reg.status not in (RegistrationStatus.pending, RegistrationStatus.waitlisted):
                continue

            reg.status = RegistrationStatus.rejected
            rejected_count += 1

        await db.commit()
        return {"rejected": rejected_count}

    async def bulk_waitlist(
        self,
        db: AsyncSession,
        hackathon_id: uuid.UUID,
        registration_ids: list[uuid.UUID],
    ) -> dict:
        """Bulk waitlist pending registrations.

        Behavior:
        1. Load the hackathon.
        2. Reject if waitlist is not enabled.
        3. For each pending registration ID, skip if not pending.
        4. Set status to waitlisted.
        5. Commit and return the waitlisted count.

        Raises: HTTPException(404) if hackathon not found.
                HTTPException(400) if waitlist disabled.
        Side Effects: Mutates Registration.status.
        """
        hackathon = await db.get(Hackathon, hackathon_id)
        if not hackathon:
            raise HTTPException(status_code=404, detail="Hackathon not found")

        if not hackathon.waitlist_enabled:
            raise HTTPException(status_code=400, detail="Waitlist is not enabled for this hackathon")

        waitlisted_count = 0

        for reg_id in registration_ids:
            reg_result = await db.execute(
                select(Registration).where(and_(Registration.id == reg_id, Registration.hackathon_id == hackathon_id))
            )
            reg = reg_result.scalar_one_or_none()
            if not reg or reg.status != RegistrationStatus.pending:
                continue

            reg.status = RegistrationStatus.waitlisted
            waitlisted_count += 1

        await db.commit()
        return {"waitlisted": waitlisted_count}

    async def export_registrations_csv(
        self,
        db: AsyncSession,
        hackathon_id: uuid.UUID,
    ) -> tuple[io.BytesIO, str]:
        """Export all hackathon registrations to CSV.

        Behavior:
        1. Query all registrations joined with user info, ordered by registration date.
        2. Write CSV rows with full registration and user fields.
        3. Return the CSV as a BytesIO buffer with a suggested filename.

        Raises: None.
        Side Effects: None (read-only, generates CSV in memory).
        """
        reg_result = await db.execute(
            select(Registration, User)
            .join(User, Registration.user_id == User.id)
            .where(Registration.hackathon_id == hackathon_id)
            .order_by(Registration.registered_at.desc())
        )
        rows = reg_result.all()

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(
            [
                "ID",
                "Status",
                "Registered At",
                "Accepted At",
                "Checked In At",
                "Name",
                "Email",
                "Team Name",
                "Team Members",
                "School",
                "Major",
                "Age",
                "Pronouns",
                "Experience Level",
                "Skills",
                "T-Shirt Size",
                "Dietary Restrictions",
                "Phone",
                "Emergency Contact Name",
                "Emergency Contact Phone",
                "LinkedIn",
                "GitHub",
                "Resume URL",
                "What They Will Build",
                "Why Participate",
            ]
        )

        for reg, user in rows:
            writer.writerow(
                [
                    str(reg.id),
                    reg.status.value,
                    reg.registered_at.isoformat(),
                    reg.accepted_at.isoformat() if reg.accepted_at else "",
                    reg.checked_in_at.isoformat() if reg.checked_in_at else "",
                    user.name,
                    user.email,
                    reg.team_name or "",
                    ", ".join(reg.team_members) if reg.team_members else "",
                    reg.school or "",
                    reg.major or "",
                    reg.age or "",
                    reg.pronouns or "",
                    reg.experience_level or "",
                    ", ".join(reg.skills) if reg.skills else "",
                    reg.t_shirt_size or "",
                    reg.dietary_restrictions or "",
                    reg.phone or "",
                    reg.emergency_contact_name or "",
                    reg.emergency_contact_phone or "",
                    reg.linkedin_url or "",
                    reg.github_url or "",
                    reg.resume_url or "",
                    (reg.what_build or "")[:200],
                    (reg.why_participate or "")[:200],
                ]
            )

        output.seek(0)
        bytes_io = io.BytesIO(output.getvalue().encode())
        filename = f"registrations-{hackathon_id}.csv"
        return bytes_io, filename
