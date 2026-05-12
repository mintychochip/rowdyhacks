"""Mentorship pairing service.

Provides CRUD operations for mentorship requests within hackathons,
including request creation, acceptance, and completion.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import MentorshipRequest


class MentorshipService:
    """Service for managing mentorship requests within hackathons."""

    async def create_request(
        self,
        db: AsyncSession,
        hackathon_id,
        requester_id: str,
        topic: str,
    ) -> MentorshipRequest:
        """Create a new mentorship request.

        Behavior:
        1. Build a MentorshipRequest instance with the provided fields.
        2. Add the request to the async session.
        3. Commit and refresh to persist the record.

        Raises: None
        Side Effects: Inserts a new MentorshipRequest row into the database.
        Dependencies: app.models.MentorshipRequest.
        Consumers: POST /api/hackathons/{id}/mentorship/request.
        """
        request = MentorshipRequest(
            hackathon_id=hackathon_id,
            requester_id=requester_id,
            topic=topic,
            status="pending",
        )
        db.add(request)
        await db.commit()
        await db.refresh(request)
        return request

    async def list_my_requests(
        self,
        db: AsyncSession,
        hackathon_id,
        user_id: str,
    ) -> list[MentorshipRequest]:
        """List mentorship requests for a user at a hackathon.

        Behavior:
        1. Query MentorshipRequest rows filtered by hackathon_id where
           the user is either the requester or the assigned mentor.
        2. Eagerly load requester and mentor relationships.
        3. Order results by created_at descending.
        4. Return the list of matching requests.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models.MentorshipRequest, sqlalchemy.select.
        Consumers: GET /api/hackathons/{id}/mentorship/requests.
        """
        result = await db.execute(
            select(MentorshipRequest)
            .options(selectinload(MentorshipRequest.requester), selectinload(MentorshipRequest.mentor))
            .where(
                MentorshipRequest.hackathon_id == hackathon_id,
                ((MentorshipRequest.requester_id == user_id) | (MentorshipRequest.mentor_id == user_id)),
            )
            .order_by(MentorshipRequest.created_at.desc())
        )
        return list(result.scalars().all())

    async def accept_request(
        self,
        db: AsyncSession,
        request_id,
        mentor_id: str,
    ) -> MentorshipRequest:
        """Accept a pending mentorship request.

        Behavior:
        1. Load the request by ID.
        2. Raise ValueError if the request does not exist.
        3. Raise ValueError if the request is not in pending status.
        4. Set mentor_id and status to accepted.
        5. Commit and refresh the record.

        Raises: ValueError if the request is not found or not pending.
        Side Effects: Updates MentorshipRequest row in the database.
        Dependencies: app.models.MentorshipRequest, sqlalchemy.select.
        Consumers: POST /api/mentorship/{id}/accept.
        """
        result = await db.execute(select(MentorshipRequest).where(MentorshipRequest.id == request_id))
        request = result.scalar_one_or_none()
        if not request:
            raise ValueError("Request not found")
        if request.status != "pending":
            raise ValueError("Request is not pending")

        request.mentor_id = mentor_id
        request.status = "accepted"
        await db.commit()
        await db.refresh(request)
        return request

    async def complete_request(
        self,
        db: AsyncSession,
        request_id,
        user_id: str,
    ) -> MentorshipRequest:
        """Mark a mentorship request as completed.

        Behavior:
        1. Load the request by ID.
        2. Raise ValueError if the request does not exist.
        3. Raise PermissionError if the requesting user is neither the requester nor the mentor.
        4. Raise ValueError if the request is not in accepted status.
        5. Set status to completed.
        6. Commit and refresh the record.

        Raises: ValueError if the request is not found or not accepted. PermissionError if the user is not involved.
        Side Effects: Updates MentorshipRequest row in the database.
        Dependencies: app.models.MentorshipRequest, sqlalchemy.select.
        Consumers: POST /api/mentorship/{id}/complete.
        """
        result = await db.execute(select(MentorshipRequest).where(MentorshipRequest.id == request_id))
        request = result.scalar_one_or_none()
        if not request:
            raise ValueError("Request not found")
        if str(request.requester_id) != user_id and str(request.mentor_id) != user_id:
            raise PermissionError("Only the requester or mentor can complete this request")
        if request.status != "accepted":
            raise ValueError("Request must be accepted before completion")

        request.status = "completed"
        await db.commit()
        await db.refresh(request)
        return request
