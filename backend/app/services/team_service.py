"""Team management service with join code generation."""

import secrets
import string

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Registration, RegistrationStatus, Team, TeamMember


class TeamService:
    """Create teams, manage membership, and generate join codes."""

    @staticmethod
    def _generate_join_code(length: int = 8) -> str:
        """Generate a random alphanumeric join code."""
        alphabet = string.ascii_uppercase + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    async def create_team(
        self,
        db: AsyncSession,
        hackathon_id,
        name: str,
        captain_id: str,
    ) -> Team:
        """Create a new team and add the captain as the first member."""
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
        """Join a team using its join code."""
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
        """Load a team with its members and captain."""
        result = await db.execute(select(Team).options(selectinload(Team.members)).where(Team.id == team_id))
        return result.scalar_one_or_none()

    async def update_team(
        self,
        db: AsyncSession,
        team_id,
        captain_id: str,
        name: str | None = None,
    ) -> Team:
        """Update team name (captain only)."""
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
        """Remove a member from the team (captain only, cannot remove self)."""
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
