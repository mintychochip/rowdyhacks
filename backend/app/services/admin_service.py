"""Admin user management service.

Provides listing, searching, banning, role changes, and activity logs
for platform administrators.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, Registration, Submission, SurveyResponse, TeamMember, User, UserRole


class AdminService:
    """Service for admin-level user management."""

    async def list_users(
        self,
        db: AsyncSession,
        search: str | None = None,
        role: str | None = None,
        banned: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[User], int]:
        """List users with optional filters and pagination.

        Behavior:
        1. Build a base select statement on User.
        2. Apply optional search filter on email or name.
        3. Apply optional role and banned filters.
        4. Execute count and paginated fetch.
        5. Return (users, total_count).

        Raises: None
        Side Effects: None (read-only).
        """
        stmt = select(User)
        count_stmt = select(User)

        if search:
            like = f"%{search}%"
            stmt = stmt.where(User.email.ilike(like) | User.name.ilike(like))
            count_stmt = count_stmt.where(User.email.ilike(like) | User.name.ilike(like))

        if role:
            stmt = stmt.where(User.role == role)
            count_stmt = count_stmt.where(User.role == role)

        if banned is not None:
            stmt = stmt.where(User.is_banned.is_(banned))
            count_stmt = count_stmt.where(User.is_banned.is_(banned))

        from sqlalchemy import func

        total_result = await db.execute(select(func.count()).select_from(count_stmt.subquery()))
        total = total_result.scalar() or 0

        result = await db.execute(stmt.order_by(User.created_at.desc()).limit(limit).offset(offset))
        users = list(result.scalars().all())
        return users, total

    async def ban_user(self, db: AsyncSession, user_id: str) -> User:
        """Ban a user.

        Behavior:
        1. Load the user by ID.
        2. Raise ValueError if not found.
        3. Set is_banned=True and banned_at=now.
        4. Commit and refresh.

        Raises: ValueError if user not found.
        Side Effects: Updates User row.
        """
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")

        user.is_banned = True
        user.banned_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(user)
        return user

    async def unban_user(self, db: AsyncSession, user_id: str) -> User:
        """Unban a user.

        Behavior:
        1. Load the user by ID.
        2. Raise ValueError if not found.
        3. Set is_banned=False and banned_at=None.
        4. Commit and refresh.

        Raises: ValueError if user not found.
        Side Effects: Updates User row.
        """
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")

        user.is_banned = False
        user.banned_at = None
        await db.commit()
        await db.refresh(user)
        return user

    async def change_role(self, db: AsyncSession, user_id: str, new_role: str) -> User:
        """Change a user's role.

        Behavior:
        1. Load the user by ID.
        2. Raise ValueError if not found or role is invalid.
        3. Update the role and commit.

        Raises: ValueError if user not found or role invalid.
        Side Effects: Updates User row.
        """
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")

        try:
            user.role = UserRole(new_role)
        except ValueError:
            raise ValueError(f"Invalid role: {new_role}")

        await db.commit()
        await db.refresh(user)
        return user

    async def get_user_activity(self, db: AsyncSession, user_id: str) -> dict:
        """Return a summary of user activity across the platform.

        Behavior:
        1. Count registrations, team memberships, submissions, survey responses, and audit logs.
        2. Return a dict with activity summaries.

        Raises: None
        Side Effects: None (read-only).
        """
        from sqlalchemy import func

        reg_result = await db.execute(select(func.count(Registration.id)).where(Registration.user_id == user_id))
        registrations = reg_result.scalar() or 0

        team_result = await db.execute(select(func.count(TeamMember.id)).where(TeamMember.user_id == user_id))
        team_memberships = team_result.scalar() or 0

        sub_result = await db.execute(select(func.count(Submission.id)).where(Submission.submitted_by == user_id))
        submissions = sub_result.scalar() or 0

        survey_result = await db.execute(select(func.count(SurveyResponse.id)).where(SurveyResponse.user_id == user_id))
        survey_responses = survey_result.scalar() or 0

        audit_result = await db.execute(
            select(AuditLog).where(AuditLog.user_id == user_id).order_by(AuditLog.created_at.desc()).limit(50)
        )
        audit_logs = list(audit_result.scalars().all())

        return {
            "user_id": user_id,
            "registrations": registrations,
            "team_memberships": team_memberships,
            "submissions": submissions,
            "survey_responses": survey_responses,
            "recent_audit_logs": [
                {
                    "id": str(log.id),
                    "action": log.action,
                    "entity_type": log.entity_type,
                    "entity_id": log.entity_id,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in audit_logs
            ],
        }
