"""Team management service with join code generation.

Provides CRUD operations for hackathon teams, including secure join-code
generation, membership management, and captain-only updates. All membership
changes validate that users have an accepted registration for the target
hackathon.
"""

import secrets
import string

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Registration, RegistrationStatus, Team, TeamMember


class TeamService:
    """Service for creating teams, managing membership, and generating join codes.

    Team creation requires the captain to have an accepted hackathon registration.
    Join codes are cryptographically random and guaranteed unique at creation
    time. Team updates and member removals are restricted to the captain.
    """

    @staticmethod
    def _generate_join_code(length: int = 8) -> str:
        """Generate a cryptographically random alphanumeric join code.

        Behavior:
        1. Build an alphabet of uppercase ASCII letters and digits.
        2. Use ``secrets.choice`` to pick ``length`` characters uniformly at random.
        3. Return the concatenated code string.

        Raises: None
        Side Effects: None (read-only, but consumes entropy).
        Dependencies: secrets.choice, string.ascii_uppercase, string.digits.
        Consumers: TeamService.create_team.
        """
        alphabet = string.ascii_uppercase + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    async def create_team(
        self,
        db: AsyncSession,
        hackathon_id,
        name: str,
        captain_id: str,
    ) -> Team:
        """Create a new team and add the captain as the first member.

        Behavior:
        1. Verify the captain has an accepted registration for the hackathon.
        2. Generate a random join code and ensure it is unique in the database.
        3. Insert a new Team row with the hackathon ID, name, join code, and captain.
        4. Commit and refresh to obtain the generated team ID.
        5. Insert a TeamMember row linking the captain to the new team.
        6. Commit again and return the team.

        Raises: ValueError if the captain lacks an accepted registration.
        Side Effects: Inserts Team and TeamMember rows; commits twice.
        Dependencies: app.models.Registration, app.models.RegistrationStatus, app.models.Team, app.models.TeamMember, sqlalchemy.select.
        Consumers: POST /api/teams, authenticated users creating teams.
        """
        # Verify user has an accepted registration for this hackathon
        reg_result = await db.execute(
            select(Registration).where(
                Registration.hackathon_id == hackathon_id,
                Registration.user_id == captain_id,
                Registration.status == RegistrationStatus.accepted,
            )
        )
        if not reg_result.scalar_one_or_none():
            raise ValueError("User must have an accepted registration to create a team")

        join_code = self._generate_join_code()
        # Ensure uniqueness
        while True:
            existing = await db.execute(select(Team).where(Team.join_code == join_code))
            if not existing.scalar_one_or_none():
                break
            join_code = self._generate_join_code()

        team = Team(
            hackathon_id=hackathon_id,
            name=name,
            join_code=join_code,
            captain_id=captain_id,
        )
        db.add(team)
        await db.commit()
        await db.refresh(team)

        # Add captain as first member
        member = TeamMember(team_id=team.id, user_id=captain_id)
        db.add(member)
        await db.commit()

        return team

    async def join_team_by_code(
        self,
        db: AsyncSession,
        join_code: str,
        user_id: str,
    ) -> Team:
        """Join a team using its join code.

        Behavior:
        1. Query the Team table by the provided join code.
        2. Raise ValueError if no matching team is found.
        3. Verify the user has an accepted registration for the hackathon.
        4. Verify the user is not already a member of the team.
        5. Insert a new TeamMember row and commit.
        6. Return the joined Team instance.

        Raises: ValueError if the join code is invalid, the user lacks an accepted registration, or the user is already a member.
        Side Effects: Inserts a TeamMember row; commits the transaction.
        Dependencies: app.models.Team, app.models.Registration, app.models.RegistrationStatus, app.models.TeamMember, sqlalchemy.select.
        Consumers: POST /api/teams/join, authenticated users joining by code.
        """
        result = await db.execute(select(Team).where(Team.join_code == join_code))
        team = result.scalar_one_or_none()
        if not team:
            raise ValueError("Invalid join code")

        # Verify user has an accepted registration for this hackathon
        reg_result = await db.execute(
            select(Registration).where(
                Registration.hackathon_id == team.hackathon_id,
                Registration.user_id == user_id,
                Registration.status == RegistrationStatus.accepted,
            )
        )
        if not reg_result.scalar_one_or_none():
            raise ValueError("User must have an accepted registration to join a team")

        # Check not already a member
        existing_member = await db.execute(
            select(TeamMember).where(
                TeamMember.team_id == team.id,
                TeamMember.user_id == user_id,
            )
        )
        if existing_member.scalar_one_or_none():
            raise ValueError("Already a member of this team")

        member = TeamMember(team_id=team.id, user_id=user_id)
        db.add(member)
        await db.commit()

        return team

    async def get_team(self, db: AsyncSession, team_id) -> Team | None:
        """Load a team by ID with its members eagerly loaded.

        Behavior:
        1. Query the Team table by ID with ``selectinload(Team.members)``.
        2. Return the Team instance if found, otherwise None.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models.Team, sqlalchemy.select, sqlalchemy.orm.selectinload.
        Consumers: GET /api/teams/{team_id}, internal team management helpers.
        """
        result = await db.execute(select(Team).options(selectinload(Team.members)).where(Team.id == team_id))
        return result.scalar_one_or_none()

    async def update_team(
        self,
        db: AsyncSession,
        team_id,
        captain_id: str,
        name: str | None = None,
    ) -> Team:
        """Update team name (restricted to the captain).

        Behavior:
        1. Load the team by ID.
        2. Raise ValueError if the team does not exist.
        3. Raise PermissionError if the requesting user is not the captain.
        4. If a new name is provided, update it.
        5. Commit, refresh, and return the team.

        Raises: ValueError if the team is not found. PermissionError if the requester is not the captain.
        Side Effects: Updates the Team row; commits the transaction.
        Dependencies: app.models.Team, TeamService.get_team.
        Consumers: PUT /api/teams/{team_id}, team captain updates.
        """
        team = await self.get_team(db, team_id)
        if not team:
            raise ValueError("Team not found")
        if str(team.captain_id) != captain_id:
            raise PermissionError("Only the captain can update the team")

        if name:
            team.name = name
            await db.commit()
            await db.refresh(team)

        return team

    async def remove_member(
        self,
        db: AsyncSession,
        team_id,
        captain_id: str,
        user_id: str,
    ) -> None:
        """Remove a member from the team (captain only; cannot remove self).

        Behavior:
        1. Load the team by ID.
        2. Raise ValueError if the team does not exist.
        3. Raise PermissionError if the requesting user is not the captain.
        4. Raise ValueError if the captain attempts to remove themselves.
        5. Query for the TeamMember row matching the team and target user.
        6. Raise ValueError if the member is not found.
        7. Delete the member and commit.

        Raises: ValueError if the team or member is not found, or if the captain tries to remove themselves. PermissionError if the requester is not the captain.
        Side Effects: Deletes a TeamMember row; commits the transaction.
        Dependencies: app.models.Team, app.models.TeamMember, sqlalchemy.select.
        Consumers: DELETE /api/teams/{team_id}/members/{user_id}, team captain actions.
        """
        team = await self.get_team(db, team_id)
        if not team:
            raise ValueError("Team not found")
        if str(team.captain_id) != captain_id:
            raise PermissionError("Only the captain can remove members")
        if str(team.captain_id) == user_id:
            raise ValueError("Captain cannot remove themselves")

        result = await db.execute(
            select(TeamMember).where(
                TeamMember.team_id == team_id,
                TeamMember.user_id == user_id,
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            raise ValueError("Member not found")

        await db.delete(member)
        await db.commit()
