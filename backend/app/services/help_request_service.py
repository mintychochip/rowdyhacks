"""Mentorship help queue service."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import HelpRequest


class HelpRequestService:
    """CRUD and queue operations for hackathon help requests."""

    async def create_help_request(
        self,
        db: AsyncSession,
        hackathon_id,
        requester_id: str,
        title: str,
        description: str | None = None,
    ) -> HelpRequest:
        """Create a new help request."""
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
        """List open help requests for a hackathon ordered by created_at."""
        result = await db.execute(
            select(HelpRequest)
            .where(HelpRequest.hackathon_id == hackathon_id, HelpRequest.status == "open")
            .order_by(HelpRequest.created_at)
        )
        return list(result.scalars().all())

    async def get_help_request(self, db: AsyncSession, request_id) -> HelpRequest | None:
        """Get a single help request by ID."""
        result = await db.execute(select(HelpRequest).where(HelpRequest.id == request_id))
        return result.scalar_one_or_none()

    async def claim_help_request(self, db: AsyncSession, request_id, mentor_id: str) -> HelpRequest:
        """Claim an open help request."""
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
        """Mark a help request as resolved."""
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
        """Delete a help request."""
        req = await self.get_help_request(db, request_id)
        if not req:
            raise ValueError("Help request not found")
        await db.delete(req)
        await db.commit()
