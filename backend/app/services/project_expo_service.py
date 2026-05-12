"""Project expo and public voting service.

Provides operations for listing hackathon submissions with public details,
casting people's choice votes, and viewing vote tallies (organizer only).
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PublicVote, Submission


class ProjectExpoService:
    """Service for managing project expo submissions and public voting."""

    async def list_submissions(
        self,
        db: AsyncSession,
        hackathon_id,
    ) -> list[Submission]:
        """List submissions for a hackathon with public details.

        Behavior:
        1. Query Submission rows filtered by hackathon_id.
        2. Order results by created_at descending.
        3. Return the list of matching submissions.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models.Submission, sqlalchemy.select.
        Consumers: GET /api/hackathons/{id}/project-expo.
        """
        result = await db.execute(
            select(Submission).where(Submission.hackathon_id == hackathon_id).order_by(Submission.created_at.desc())
        )
        return list(result.scalars().all())

    async def cast_vote(
        self,
        db: AsyncSession,
        hackathon_id,
        submission_id,
        voter_id: str,
    ) -> PublicVote:
        """Cast a people's choice vote for a submission.

        Behavior:
        1. Check if the voter has already voted in this hackathon.
        2. Raise ValueError if a vote already exists.
        3. Insert a new PublicVote row.
        4. Commit and refresh to persist the record.

        Raises: ValueError if the voter has already voted in this hackathon.
        Side Effects: Inserts a PublicVote row into the database.
        Dependencies: app.models.PublicVote, sqlalchemy.select.
        Consumers: POST /api/hackathons/{id}/project-expo/{submission_id}/vote.
        """
        existing = await db.execute(
            select(PublicVote).where(
                PublicVote.hackathon_id == hackathon_id,
                PublicVote.voter_id == voter_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("You have already voted in this hackathon")

        vote = PublicVote(
            hackathon_id=hackathon_id,
            submission_id=submission_id,
            voter_id=voter_id,
        )
        db.add(vote)
        await db.commit()
        await db.refresh(vote)
        return vote

    async def get_results(
        self,
        db: AsyncSession,
        hackathon_id,
    ) -> list[dict]:
        """Get vote counts per submission for a hackathon.

        Behavior:
        1. Query PublicVote rows filtered by hackathon_id.
        2. Group by submission_id and count votes.
        3. Return a list of dicts with submission_id and vote_count.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models.PublicVote, sqlalchemy.select, sqlalchemy.func.
        Consumers: GET /api/hackathons/{id}/project-expo/results.
        """
        result = await db.execute(
            select(
                PublicVote.submission_id,
                func.count(PublicVote.id).label("vote_count"),
            )
            .where(PublicVote.hackathon_id == hackathon_id)
            .group_by(PublicVote.submission_id)
            .order_by(func.count(PublicVote.id).desc())
        )
        rows = result.all()
        return [
            {
                "submission_id": str(row.submission_id),
                "vote_count": row.vote_count,
            }
            for row in rows
        ]
