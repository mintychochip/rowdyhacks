"""Team finder / hacker matching service.

Provides CRUD operations for team finder posts, allowing hackers to
advertise that they are looking for a team or looking for members.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import TeamFinderPost


class TeamFinderService:
    """Service for managing team finder posts within hackathons."""

    async def create_post(
        self,
        db: AsyncSession,
        hackathon_id,
        user_id: str,
        post_type: str,
        skills_needed: list[str] | None = None,
        description: str | None = None,
    ) -> TeamFinderPost:
        """Create a new team finder post.

        Behavior:
        1. Build a TeamFinderPost instance with the provided fields.
        2. Add the post to the async session.
        3. Commit and refresh to persist the record.

        Raises: ValueError if post_type is invalid.
        Side Effects: Inserts a new TeamFinderPost row into the database.
        Dependencies: app.models.TeamFinderPost.
        Consumers: POST /api/hackathons/{id}/team-finder.
        """
        if post_type not in ("looking_for_team", "looking_for_members"):
            raise ValueError("post_type must be 'looking_for_team' or 'looking_for_members'")

        post = TeamFinderPost(
            hackathon_id=hackathon_id,
            user_id=user_id,
            post_type=post_type,
            skills_needed=skills_needed,
            description=description,
        )
        db.add(post)
        await db.commit()
        await db.refresh(post)
        return post

    async def list_posts(self, db: AsyncSession, hackathon_id) -> list[TeamFinderPost]:
        """List active team finder posts for a hackathon.

        Behavior:
        1. Query TeamFinderPost rows filtered by hackathon_id and is_active=True.
        2. Eagerly load the associated User rows.
        3. Order results by created_at descending.
        4. Return the list of matching posts.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models.TeamFinderPost, sqlalchemy.select.
        Consumers: GET /api/hackathons/{id}/team-finder.
        """
        result = await db.execute(
            select(TeamFinderPost)
            .options(selectinload(TeamFinderPost.user))
            .where(
                TeamFinderPost.hackathon_id == hackathon_id,
                TeamFinderPost.is_active.is_(True),
            )
            .order_by(TeamFinderPost.created_at.desc())
        )
        return list(result.scalars().all())

    async def deactivate_post(
        self,
        db: AsyncSession,
        post_id,
        user_id: str,
    ) -> TeamFinderPost:
        """Deactivate a team finder post (owner only).

        Behavior:
        1. Load the post by ID.
        2. Raise ValueError if the post does not exist.
        3. Raise PermissionError if the requesting user is not the owner.
        4. Set is_active to False.
        5. Commit and refresh the record.

        Raises: ValueError if the post is not found. PermissionError if the requester is not the owner.
        Side Effects: Updates TeamFinderPost.is_active in the database.
        Dependencies: app.models.TeamFinderPost, sqlalchemy.select.
        Consumers: DELETE /api/hackathons/{id}/team-finder/{post_id}.
        """
        result = await db.execute(select(TeamFinderPost).where(TeamFinderPost.id == post_id))
        post = result.scalar_one_or_none()
        if not post:
            raise ValueError("Post not found")
        if str(post.user_id) != user_id:
            raise PermissionError("Only the post owner can deactivate this post")

        post.is_active = False
        await db.commit()
        await db.refresh(post)
        return post
