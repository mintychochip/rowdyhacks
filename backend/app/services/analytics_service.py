"""Analytics service for hackathon organizers.

Aggregates registration, attendance, workshop, team, submission, and
demographic metrics for a single hackathon.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Registration,
    RegistrationStatus,
    Submission,
    Team,
    TeamMember,
    Workshop,
    WorkshopRSVP,
    WorkshopRSVPStatus,
)


class AnalyticsService:
    """Compute analytics metrics for a hackathon."""

    async def get_registration_funnel(self, db: AsyncSession, hackathon_id) -> dict:
        """Count registrations by status for the funnel.

        Behavior:
        1. Query Registration counts grouped by status for the hackathon.
        2. Return counts for pending, accepted, rejected, waitlisted, offered, checked_in.

        Raises: None
        Side Effects: None (read-only).
        """
        result = await db.execute(
            select(Registration.status, func.count(Registration.id))
            .where(Registration.hackathon_id == hackathon_id)
            .group_by(Registration.status)
        )
        counts = {status.value: 0 for status in RegistrationStatus}
        for status, count in result.all():
            counts[status.value] = count

        return {
            "applied": counts.get("pending", 0)
            + counts.get("accepted", 0)
            + counts.get("rejected", 0)
            + counts.get("waitlisted", 0)
            + counts.get("offered", 0)
            + counts.get("checked_in", 0),
            "pending": counts.get("pending", 0),
            "accepted": counts.get("accepted", 0),
            "rejected": counts.get("rejected", 0),
            "waitlisted": counts.get("waitlisted", 0),
            "offered": counts.get("offered", 0),
            "checked_in": counts.get("checked_in", 0),
        }

    async def get_attendance_metrics(self, db: AsyncSession, hackathon_id) -> dict:
        """Compute attendance and no-show rates.

        Behavior:
        1. Count accepted registrations.
        2. Count checked_in registrations.
        3. Compute attendance rate and no-show rate.

        Raises: None
        Side Effects: None (read-only).
        """
        accepted_result = await db.execute(
            select(func.count(Registration.id)).where(
                Registration.hackathon_id == hackathon_id,
                Registration.status == RegistrationStatus.accepted,
            )
        )
        accepted = accepted_result.scalar() or 0

        checked_in_result = await db.execute(
            select(func.count(Registration.id)).where(
                Registration.hackathon_id == hackathon_id,
                Registration.status == RegistrationStatus.checked_in,
            )
        )
        checked_in = checked_in_result.scalar() or 0

        total = accepted + checked_in
        attendance_rate = (checked_in / total * 100) if total > 0 else 0.0
        no_show_rate = (accepted / total * 100) if total > 0 else 0.0

        return {
            "accepted": accepted,
            "checked_in": checked_in,
            "attendance_rate": round(attendance_rate, 2),
            "no_show_rate": round(no_show_rate, 2),
        }

    async def get_workshop_engagement(self, db: AsyncSession, hackathon_id) -> list[dict]:
        """Per-workshop RSVP vs attendance rates.

        Behavior:
        1. List all workshops for the hackathon.
        2. For each workshop, count RSVPs and attendances.
        3. Return aggregated metrics per workshop.

        Raises: None
        Side Effects: None (read-only).
        """
        workshop_result = await db.execute(select(Workshop).where(Workshop.hackathon_id == hackathon_id))
        workshops = workshop_result.scalars().all()

        metrics = []
        for ws in workshops:
            rsvp_result = await db.execute(
                select(func.count(WorkshopRSVP.id)).where(
                    WorkshopRSVP.workshop_id == ws.id,
                    WorkshopRSVP.status.in_([WorkshopRSVPStatus.registered, WorkshopRSVPStatus.attended]),
                )
            )
            rsvps = rsvp_result.scalar() or 0

            attended_result = await db.execute(
                select(func.count(WorkshopRSVP.id)).where(
                    WorkshopRSVP.workshop_id == ws.id,
                    WorkshopRSVP.status == WorkshopRSVPStatus.attended,
                )
            )
            attended = attended_result.scalar() or 0

            metrics.append(
                {
                    "workshop_id": str(ws.id),
                    "title": ws.title,
                    "rsvps": rsvps,
                    "attended": attended,
                    "attendance_rate": round((attended / rsvps * 100), 2) if rsvps > 0 else 0.0,
                }
            )

        return metrics

    async def get_team_formation_stats(self, db: AsyncSession, hackathon_id) -> dict:
        """Team formation summary.

        Behavior:
        1. Count teams for the hackathon.
        2. Compute average team size from TeamMember counts.
        3. Count accepted registrations without team membership as solo hackers.

        Raises: None
        Side Effects: None (read-only).
        """
        team_count_result = await db.execute(select(func.count(Team.id)).where(Team.hackathon_id == hackathon_id))
        teams_formed = team_count_result.scalar() or 0

        avg_size_result = await db.execute(
            select(func.count(TeamMember.id)).where(
                TeamMember.team_id.in_(select(Team.id).where(Team.hackathon_id == hackathon_id))
            )
        )
        total_members = avg_size_result.scalar() or 0
        avg_team_size = round(total_members / teams_formed, 2) if teams_formed > 0 else 0.0

        # Solo hackers = accepted/checked_in registrations not in any team for this hackathon
        solo_result = await db.execute(
            select(func.count(Registration.id)).where(
                Registration.hackathon_id == hackathon_id,
                Registration.status.in_([RegistrationStatus.accepted, RegistrationStatus.checked_in]),
                Registration.user_id.notin_(
                    select(TeamMember.user_id).where(
                        TeamMember.team_id.in_(select(Team.id).where(Team.hackathon_id == hackathon_id))
                    )
                ),
            )
        )
        solo_hackers = solo_result.scalar() or 0

        return {
            "teams_formed": teams_formed,
            "avg_team_size": avg_team_size,
            "total_team_members": total_members,
            "solo_hackers": solo_hackers,
        }

    async def get_submission_stats(self, db: AsyncSession, hackathon_id) -> dict:
        """Submission counts, track breakdown, and risk score averages.

        Behavior:
        1. Count total submissions for the hackathon.
        2. Compute average risk score.
        3. Count submissions by verdict.

        Raises: None
        Side Effects: None (read-only).
        """
        total_result = await db.execute(
            select(func.count(Submission.id)).where(Submission.hackathon_id == hackathon_id)
        )
        total = total_result.scalar() or 0

        avg_risk_result = await db.execute(
            select(func.avg(Submission.risk_score)).where(
                Submission.hackathon_id == hackathon_id,
                Submission.risk_score.isnot(None),
            )
        )
        avg_risk = avg_risk_result.scalar()

        verdict_result = await db.execute(
            select(Submission.verdict, func.count(Submission.id))
            .where(
                Submission.hackathon_id == hackathon_id,
                Submission.verdict.isnot(None),
            )
            .group_by(Submission.verdict)
        )
        by_verdict = {v.value if hasattr(v, "value") else str(v): c for v, c in verdict_result.all()}

        return {
            "total_submissions": total,
            "avg_risk_score": round(float(avg_risk), 2) if avg_risk is not None else None,
            "by_verdict": by_verdict,
        }

    async def get_demographics(self, db: AsyncSession, hackathon_id) -> dict:
        """Breakdown of school, major, experience level, and age.

        Behavior:
        1. Query accepted/checked_in registrations for the hackathon.
        2. Group by school, major, experience_level, and age.
        3. Return frequency distributions for each dimension.

        Raises: None
        Side Effects: None (read-only).
        """
        regs_result = await db.execute(
            select(Registration).where(
                Registration.hackathon_id == hackathon_id,
                Registration.status.in_([RegistrationStatus.accepted, RegistrationStatus.checked_in]),
            )
        )
        regs = regs_result.scalars().all()

        schools: dict[str, int] = {}
        majors: dict[str, int] = {}
        experience: dict[str, int] = {}
        ages: dict[int, int] = {}

        for r in regs:
            if r.school:
                schools[r.school] = schools.get(r.school, 0) + 1
            if r.major:
                majors[r.major] = majors.get(r.major, 0) + 1
            if r.experience_level:
                experience[r.experience_level] = experience.get(r.experience_level, 0) + 1
            if r.age is not None:
                ages[r.age] = ages.get(r.age, 0) + 1

        return {
            "schools": schools,
            "majors": majors,
            "experience_levels": experience,
            "ages": ages,
            "total_respondents": len(regs),
        }

    async def get_all_metrics(self, db: AsyncSession, hackathon_id) -> dict:
        """Aggregate all analytics metrics for a hackathon.

        Behavior:
        1. Call each individual metric method.
        2. Return a combined dict.

        Raises: None
        Side Effects: None (read-only).
        """
        return {
            "registration_funnel": await self.get_registration_funnel(db, hackathon_id),
            "attendance": await self.get_attendance_metrics(db, hackathon_id),
            "workshops": await self.get_workshop_engagement(db, hackathon_id),
            "teams": await self.get_team_formation_stats(db, hackathon_id),
            "submissions": await self.get_submission_stats(db, hackathon_id),
            "demographics": await self.get_demographics(db, hackathon_id),
        }
