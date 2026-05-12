"""Participant registration routes."""

import asyncio
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import decode_token
from app.clerk_auth import require_clerk_user
from app.database import get_db
from app.discord_bot import post_application_to_discord
from app.models import Hackathon, HackathonOrganizer, RegistrationStatus, User, UserRole
from app.schemas import RegistrationCreate
from app.services.registration_service import RegistrationService
from app.waitlist import get_waitlist_position

router = APIRouter(prefix="/api", tags=["registrations"])


async def _ensure_hackathon_organizer(
    db: AsyncSession,
    user_id: str,
    hackathon_id: uuid.UUID,
) -> Hackathon:
    """Verify the current user is the organizer or co-organizer of the given hackathon.

    Behavior:
    1. Load the hackathon and user in parallel.
    2. Raise 404 if the hackathon is not found.
    3. Raise 403 if the user is not an organizer.
    4. Return the hackathon if the user is the primary organizer.
    5. Check HackathonOrganizer for co-organizer status and return if confirmed.
    6. Raise 403 if the user lacks ownership.

    Raises: HTTPException(404) if hackathon not found. HTTPException(403) if user is not organizer or does not own hackathon.
    Side Effects: None (read-only).
    Dependencies: app.models.Hackathon, app.models.HackathonOrganizer, app.models.User, app.models.UserRole.
    Consumers: Internal helper used by registration organizer routes.
    """
    # Parallel: hackathon + user lookups are independent
    hk_task = db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    user_task = db.execute(select(User).where(User.id == user_id))
    hk_result, user_result = await asyncio.gather(hk_task, user_task)

    hackathon = hk_result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    # Verify caller is an organizer and owns this hackathon (or is co-organizer)
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
    user_payload: dict = Depends(require_clerk_user),
    status: str | None = Query(None, description="Filter by status: pending, accepted, rejected, checked_in"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Organizer view: list all registrations for a hackathon.

    Behavior:
    1. Verify the user is an organizer for the hackathon.
    2. Validate the optional status filter.
    3. Build count and list queries with filters and pagination.
    4. Fetch registrations with eager-loaded users.
    5. Return the registration list with pagination metadata.

    Raises: HTTPException(403) if user is not an organizer. HTTPException(422) if invalid status filter.
    Side Effects: None (read-only).
    Dependencies: app.models.Registration, app.models.User, app.clerk_auth.require_clerk_user.
    Consumers: GET /api/hackathons/{hackathon_id}/registrations, organizer dashboard.
    """
    await _ensure_hackathon_organizer(db, user_payload["sub"], hackathon_id)

    service = RegistrationService()
    return await service.list_registrations_for_hackathon(db, hackathon_id, status=status, offset=offset, limit=limit)


@router.post("/hackathons/{hackathon_id}/registrations/{registration_id}/accept", status_code=200)
async def accept_registration(
    hackathon_id: uuid.UUID,
    registration_id: uuid.UUID,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Accept a pending or waitlisted registration (organizer only).

    Behavior:
    1. Verify the user is an organizer for the hackathon.
    2. Load the registration by id and hackathon_id with eager-loaded user.
    3. Raise 404 if the registration is not found.
    4. Raise 409 if the registration is not pending or waitlisted.
    5. Check capacity and increment current_participants if needed.
    6. Update status to accepted and set accepted_at.
    7. Commit, refresh, and return the full registration details.

    Raises: HTTPException(403) if user is not an organizer. HTTPException(404) if registration not found. HTTPException(409) if registration not pending or waitlisted. HTTPException(400) if hackathon at capacity.
    Side Effects: Mutates Registration status, accepted_at; increments Hackathon.current_participants.
    Dependencies: app.models.Registration, app.models.Hackathon, app.clerk_auth.require_clerk_user.
    Consumers: POST /api/hackathons/{hackathon_id}/registrations/{registration_id}/accept, organizer dashboard.
    """
    hackathon = await _ensure_hackathon_organizer(db, user_payload["sub"], hackathon_id)

    service = RegistrationService()
    reg = await service.accept_registration(
        db,
        hackathon_id,
        registration_id,
        hackathon=hackathon,
        check_capacity=True,
        increment_participants=True,
    )
    return RegistrationService.registration_to_response(reg, reg.user)


@router.post("/hackathons/{hackathon_id}/registrations/{registration_id}/reject", status_code=200)
async def reject_registration(
    hackathon_id: uuid.UUID,
    registration_id: uuid.UUID,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Reject a pending registration (organizer only).

    Behavior:
    1. Verify the user is an organizer for the hackathon.
    2. Delegate to RegistrationService.reject_registration.
    3. Return the full registration details.

    Raises: HTTPException(403) if user is not an organizer. HTTPException(404) if registration not found. HTTPException(409) if registration not pending.
    Side Effects: Mutates Registration status.
    Dependencies: app.services.registration_service.RegistrationService, app.clerk_auth.require_clerk_user.
    Consumers: POST /api/hackathons/{hackathon_id}/registrations/{registration_id}/reject, organizer dashboard.
    """
    await _ensure_hackathon_organizer(db, user_payload["sub"], hackathon_id)

    service = RegistrationService()
    reg = await service.reject_registration(db, hackathon_id, registration_id)
    return RegistrationService.registration_to_response(reg, reg.user)


@router.post("/hackathons/{hackathon_id}/registrations/{registration_id}/checkin", status_code=200)
async def checkin_registration(
    hackathon_id: uuid.UUID,
    registration_id: uuid.UUID,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Check in a registration (organizer action). Only accepted registrations can be checked in.

    Behavior:
    1. Verify the user is an organizer for the hackathon.
    2. Delegate to RegistrationService.checkin_registration.
    3. Return the full registration details.

    Raises: HTTPException(403) if user is not an organizer. HTTPException(404) if registration not found. HTTPException(409) if registration not accepted.
    Side Effects: Mutates Registration status and checked_in_at.
    Dependencies: app.services.registration_service.RegistrationService, app.clerk_auth.require_clerk_user.
    Consumers: POST /api/hackathons/{hackathon_id}/registrations/{registration_id}/checkin, organizer dashboard.
    """
    await _ensure_hackathon_organizer(db, user_payload["sub"], hackathon_id)

    service = RegistrationService()
    reg = await service.checkin_registration(db, hackathon_id, registration_id)
    return RegistrationService.registration_to_response(reg, reg.user)


@router.post("/hackathons/{hackathon_id}/register", status_code=201)
async def register_for_hackathon(
    hackathon_id: uuid.UUID,
    body: RegistrationCreate,
    background_tasks: BackgroundTasks,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Register current user for a hackathon.

    Behavior:
    1. Load the user and hackathon in parallel.
    2. Raise 401 if the user is not found.
    3. Raise 404 if the hackathon is not found.
    4. Raise 400 if the application deadline has passed.
    5. Raise 409 if the user is already registered.
    6. Determine if auto-waitlist is needed based on capacity.
    7. Create a Registration with the appropriate initial status.
    8. Commit and send a Discord notification via background task.
    9. Publish a registration.created event.
    10. Return the registration details with optional waitlist info.

    Raises: HTTPException(401) if user not found. HTTPException(404) if hackathon not found. HTTPException(400) if deadline passed or at capacity without waitlist. HTTPException(409) if already registered.
    Side Effects: Inserts Registration row; increments Hackathon.current_participants if waitlisted; spawns background task; publishes event.
    Dependencies: app.models.Registration, app.models.Hackathon, app.models.User, app.discord_bot.post_application_to_discord, app.services.event_service.publish_event.
    Consumers: POST /api/hackathons/{hackathon_id}/register, participant registration form.
    """
    user_result = await db.execute(select(User).where(User.id == user_payload["sub"]))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    hk_result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = hk_result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    if hackathon.application_deadline and datetime.now(UTC) > hackathon.application_deadline:
        raise HTTPException(status_code=400, detail="Application deadline has passed")

    service = RegistrationService()
    reg = await service.create_registration(db, hackathon_id, user.id, body)

    # Validate and attach custom question answers
    if body.answers:
        from app.services.registration_question_service import RegistrationQuestionService

        q_service = RegistrationQuestionService(db)
        try:
            answer_objects = await q_service.validate_answers(
                hackathon_id=hackathon_id,
                answers=[{"question_id": a.question_id, "value": a.value} for a in body.answers],
            )
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

        for ans in answer_objects:
            ans.registration_id = reg.id
            db.add(ans)
        await db.commit()

    # Discord notification via background task
    background_tasks.add_task(post_application_to_discord, str(reg.id))

    # Publish event for webhooks
    from app.services.event_service import publish_event

    await publish_event(
        db,
        "registration.created",
        {
            "registration_id": str(reg.id),
            "hackathon_id": str(hackathon_id),
            "user_id": str(user.id),
            "status": reg.status.value,
        },
    )

    # Reload with answers for response
    from sqlalchemy.orm import selectinload
    from app.models import Registration, RegistrationAnswer

    result = await db.execute(
        select(Registration)
        .where(Registration.id == reg.id)
        .options(selectinload(Registration.user))
        .options(selectinload(Registration.answers).selectinload(RegistrationAnswer.question))
    )
    reg = result.scalar_one()

    response = RegistrationService.registration_to_response(reg, user)

    # If waitlisted, add position info
    if reg.status == RegistrationStatus.waitlisted:
        position = await get_waitlist_position(reg.id, hackathon_id, db)
        response["waitlist_info"] = {"estimated_position": position}

    return response


@router.get("/registrations")
async def list_my_registrations(
    user_payload: dict = Depends(require_clerk_user),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List registrations for the current user. RLS: own registrations only.

    Behavior:
    1. Load the current user.
    2. Raise 401 if the user is not found.
    3. Count and query registrations filtered by user_id.
    4. Fetch registrations with eager-loaded users.
    5. Return the registration list with pagination metadata.

    Raises: HTTPException(401) if user not found.
    Side Effects: None (read-only).
    Dependencies: app.models.Registration, app.models.User, app.clerk_auth.require_clerk_user.
    Consumers: GET /api/registrations, participant profile.
    """
    result = await db.execute(select(User).where(User.id == user_payload["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    service = RegistrationService()
    return await service.list_registrations_for_user(db, user.id, offset=offset, limit=limit)


@router.get("/registrations/{registration_id}")
async def get_registration(
    registration_id: uuid.UUID,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single registration. RLS: own only.

    Behavior:
    1. Load the current user.
    2. Raise 401 if the user is not found.
    3. Delegate to RegistrationService.get_registration.
    4. Return the full registration details.

    Raises: HTTPException(401) if user not found. HTTPException(404) if registration not found or does not belong to user.
    Side Effects: None (read-only).
    Dependencies: app.services.registration_service.RegistrationService, app.clerk_auth.require_clerk_user.
    Consumers: GET /api/registrations/{registration_id}, participant profile.
    """
    result = await db.execute(select(User).where(User.id == user_payload["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    service = RegistrationService()
    reg = await service.get_registration(db, registration_id, user_id=user.id)
    return RegistrationService.registration_to_response(reg, reg.user)


@router.put("/registrations/{registration_id}")
async def update_registration(
    registration_id: uuid.UUID,
    body: RegistrationCreate,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a pending registration and its answers."""
    from sqlalchemy.orm import selectinload
    from app.models import Registration, RegistrationAnswer, RegistrationStatus

    result = await db.execute(select(User).where(User.id == user_payload["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    reg_result = await db.execute(
        select(Registration)
        .where(and_(Registration.id == registration_id, Registration.user_id == user.id))
        .options(selectinload(Registration.answers))
    )
    reg = reg_result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")

    if reg.status != RegistrationStatus.pending:
        raise HTTPException(status_code=409, detail="Can only update pending registrations")

    # Update standard fields
    for field in [
        "team_name",
        "team_members",
        "linkedin_url",
        "github_url",
        "resume_url",
        "experience_level",
        "t_shirt_size",
        "phone",
        "dietary_restrictions",
        "what_build",
        "why_participate",
        "age",
        "school",
        "major",
        "pronouns",
        "skills",
        "emergency_contact_name",
        "emergency_contact_phone",
    ]:
        val = getattr(body, field, None)
        if val is not None:
            setattr(reg, field, val)

    # Update answers
    if body.answers:
        from app.services.registration_question_service import RegistrationQuestionService

        service = RegistrationQuestionService(db)
        try:
            new_answers = await service.validate_answers(
                hackathon_id=reg.hackathon_id,
                answers=[{"question_id": a.question_id, "value": a.value} for a in body.answers],
            )
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

        # Remove old answers and add new ones
        for old in reg.answers:
            await db.delete(old)
        for ans in new_answers:
            ans.registration_id = reg.id
            db.add(ans)

    await db.commit()
    await db.refresh(reg)

    # Reload with relationships
    reg_result = await db.execute(
        select(Registration)
        .where(Registration.id == reg.id)
        .options(selectinload(Registration.user))
        .options(selectinload(Registration.answers).selectinload(RegistrationAnswer.question))
    )
    reg = reg_result.scalar_one()

    return RegistrationService.registration_to_response(reg, reg.user)


@router.post("/{registration_id}/accept-offer")
async def accept_offer(
    registration_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Participant accepts an offered spot from waitlist promotion.

    Behavior:
    1. Authenticate from the Authorization header.
    2. Raise 401 if authentication is missing or invalid.
    3. Lock and load the registration by id and user_id.
    4. Raise 404 if the registration is not found.
    5. Raise 409 if the registration is not in offered status.
    6. Raise 410 if the offer has expired.
    7. Check capacity one more time; revert to waitlist if the spot is taken.
    8. Update status to accepted, set accepted_at, and generate a QR token.
    9. Commit and send a confirmation email.
    10. Return the updated registration details.

    Raises: HTTPException(401) if authentication missing or invalid. HTTPException(404) if registration not found. HTTPException(409) if registration not offered or spot taken. HTTPException(410) if offer expired.
    Side Effects: Mutates Registration status, accepted_at, offer_expires_at, qr_token; sends email.
    Dependencies: app.auth.decode_token, app.auth.create_qr_token, app.models.Registration, app.models.Hackathon, app.email_service.send_email.
    Consumers: POST /api/{registration_id}/accept-offer, participant waitlist action.
    """
    # Authenticate
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization.removeprefix("Bearer ")
    payload = decode_token(token)
    user_id = payload.get("sub")

    service = RegistrationService()
    reg = await service.accept_offer(db, registration_id, user_id)

    return {
        "id": str(reg.id),
        "status": reg.status.value,
        "qr_token": reg.qr_token,
        "accepted_at": reg.accepted_at.isoformat(),
    }


@router.post("/{registration_id}/decline-offer")
async def decline_offer(
    registration_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Participant declines an offered spot. Returns to waitlist with lower priority.

    Behavior:
    1. Authenticate from the Authorization header.
    2. Delegate to RegistrationService.decline_offer.
    3. Return the updated registration details.

    Raises: HTTPException(401) if authentication missing or invalid. HTTPException(404) if registration not found. HTTPException(409) if registration not offered.
    Side Effects: Mutates Registration status, offer_expires_at, declined_count; triggers waitlist promotion.
    Dependencies: app.auth.decode_token, app.services.registration_service.RegistrationService.
    Consumers: POST /api/{registration_id}/decline-offer, participant waitlist action.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization.removeprefix("Bearer ")
    payload = decode_token(token)
    user_id = payload.get("sub")

    service = RegistrationService()
    reg = await service.decline_offer(db, registration_id, user_id)

    return {"id": str(reg.id), "status": reg.status.value, "declined_count": reg.declined_count}
