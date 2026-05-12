"""Participant profile management service.

Provides CRUD operations for user public profiles and listing participants
for a hackathon with their profile details.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Registration, RegistrationStatus, User


class ProfileService:
    """Service for managing user public profiles and participant listings."""

    async def get_profile(self, db: AsyncSession, user_id: str) -> User | None:
        """Load a user by ID.

        Behavior:
        1. Query the User table by the provided user_id.
        2. Return the User instance if found, otherwise None.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models.User, sqlalchemy.select.
        Consumers: GET /api/users/me/profile.
        """
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def update_profile(
        self,
        db: AsyncSession,
        user_id: str,
        bio: str | None = None,
        skills: list | None = None,
        links: dict | None = None,
        availability: str | None = None,
        looking_for_team: bool | None = None,
    ) -> User:
        """Update a user's public profile fields selectively.

        Behavior:
        1. Load the user by ID.
        2. Raise ValueError if the user does not exist.
        3. Apply any provided non-None field updates.
        4. Commit and refresh the record.

        Raises: ValueError if the user is not found.
        Side Effects: Updates User row fields in the database.
        Dependencies: app.models.User, sqlalchemy.select.
        Consumers: PUT /api/users/me/profile.
        """
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")

        if bio is not None:
            user.bio = bio
        if skills is not None:
            user.skills = skills
        if links is not None:
            user.links = links
        if availability is not None:
            user.availability = availability
        if looking_for_team is not None:
            user.looking_for_team = looking_for_team

        await db.commit()
        await db.refresh(user)
        return user

    async def list_participants(self, db: AsyncSession, hackathon_id) -> list[User]:
        """List public profiles of accepted participants for a hackathon.

        Behavior:
        1. Query Registration rows for the hackathon with accepted status.
        2. Eagerly load the associated User rows.
        3. Return the list of users.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models.Registration, app.models.RegistrationStatus, app.models.User, sqlalchemy.select.
        Consumers: GET /api/hackathons/{id}/participants.
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
        return [reg.user for reg in registrations if reg.user]
