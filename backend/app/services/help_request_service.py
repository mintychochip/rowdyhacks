"""Mentorship help queue service.

Provides CRUD and queue operations for hackathon help requests, including
open/claimed/resolved lifecycle management with mentor assignment.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import HelpRequest


class HelpRequestService:
    """CRUD and queue operations for hackathon help requests.

    Manages the full lifecycle of mentorship requests: creation, listing,
    claiming by mentors, resolution, and deletion.
    """

    async def create_help_request(
        self,
        db: AsyncSession,
        hackathon_id,
        requester_id: str,
        title: str,
        description: str | None = None,
    ) -> HelpRequest:
        """Create a new help request for a hackathon.

        Behavior:
        1. Build a HelpRequest with the provided fields and status "open".
        2. Add the request to the async session.
        3. Commit and refresh to persist the record.

        Raises: None
        Side Effects: Inserts a new HelpRequest row into the database.
        Dependencies: app.models.HelpRequest.
        Consumers: POST /api/help-requests, authenticated users requesting mentorship.
        """
        req = HelpRequest(
            hackathon_id=hackathon_id,
            requester_id=requester_id,
            title=title,
            description=description,
            status="open",
        )
        db.add(req)
        await db.commit()
        await db.refresh(req)
        return req

    async def list_open_requests(self, db: AsyncSession, hackathon_id) -> list[HelpRequest]:
        """List open help requests for a hackathon ordered by creation time.

        Behavior:
        1. Query HelpRequest rows filtered by hackathon_id and status "open".
        2. Order results by created_at ascending.
        3. Return the list of matching requests.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models.HelpRequest.
        Consumers: GET /api/help-requests?hackathon_id=..., public or internal listing.
        """
        result = await db.execute(
            select(HelpRequest)
            .where(HelpRequest.hackathon_id == hackathon_id, HelpRequest.status == "open")
            .order_by(HelpRequest.created_at)
        )
        return list(result.scalars().all())

    async def get_help_request(self, db: AsyncSession, request_id) -> HelpRequest | None:
        """Get a single help request by its ID.

        Behavior:
        1. Query HelpRequest by the given request_id.
        2. Return the record if found, otherwise None.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models.HelpRequest.
        Consumers: GET /api/help-requests/{request_id}, public detail view.
        """
        result = await db.execute(select(HelpRequest).where(HelpRequest.id == request_id))
        return result.scalar_one_or_none()

    async def claim_help_request(self, db: AsyncSession, request_id, mentor_id: str) -> HelpRequest:
        """Claim an open help request for mentorship.

        Behavior:
        1. Load the help request by ID.
        2. Validate the request exists and its status is "open".
        3. Set status to "claimed", assign mentor_id, and record claimed_at timestamp.
        4. Commit and refresh the record.

        Raises: ValueError if the request is not found or is not open.
        Side Effects: Updates HelpRequest status, mentor_id, and claimed_at.
        Dependencies: app.models.HelpRequest.
        Consumers: POST /api/help-requests/{request_id}/claim, mentors claiming requests.
        """
        req = await self.get_help_request(db, request_id)
        if not req:
            raise ValueError("Help request not found")
        if req.status != "open":
            raise ValueError("Request is not open")

        req.status = "claimed"
        req.mentor_id = mentor_id
        req.claimed_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(req)
        return req

    async def resolve_help_request(self, db: AsyncSession, request_id) -> HelpRequest:
        """Mark a help request as resolved.

        Behavior:
        1. Load the help request by ID.
        2. Validate the request exists and is not already resolved.
        3. Set status to "resolved" and record resolved_at timestamp.
        4. Commit and refresh the record.

        Raises: ValueError if the request is not found or is already resolved.
        Side Effects: Updates HelpRequest status and resolved_at.
        Dependencies: app.models.HelpRequest.
        Consumers: POST /api/help-requests/{request_id}/resolve, mentors or requesters resolving.
        """
        req = await self.get_help_request(db, request_id)
        if not req:
            raise ValueError("Help request not found")
        if req.status == "resolved":
            raise ValueError("Request is already resolved")

        req.status = "resolved"
        req.resolved_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(req)
        return req

    async def delete_help_request(self, db: AsyncSession, request_id) -> None:
        """Delete a help request from the queue.

        Behavior:
        1. Load the help request by ID.
        2. Validate the request exists.
        3. Delete the record from the session and commit.

        Raises: ValueError if the request is not found.
        Side Effects: Deletes a HelpRequest row from the database.
        Dependencies: app.models.HelpRequest.
        Consumers: DELETE /api/help-requests/{request_id}, authenticated user or admin cleanup.
        """
        req = await self.get_help_request(db, request_id)
        if not req:
            raise ValueError("Help request not found")
        await db.delete(req)
        await db.commit()
