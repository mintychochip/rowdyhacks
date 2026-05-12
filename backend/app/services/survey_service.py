"""Survey management service.

Handles creation, listing, response collection, and result aggregation
for post-event surveys and NPS scoring.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Survey, SurveyResponse


class SurveyService:
    """Service for managing hackathon surveys and responses."""

    async def create_survey(
        self,
        db: AsyncSession,
        hackathon_id: uuid.UUID,
        title: str,
        questions_json: dict | list,
    ) -> Survey:
        """Create a new survey for a hackathon.

        Behavior:
        1. Build a Survey row with the provided title and questions.
        2. Add to the session, commit, and refresh.
        3. Return the created Survey instance.

        Raises: None
        Side Effects: Inserts a Survey row.
        """
        survey = Survey(
            hackathon_id=hackathon_id,
            title=title,
            questions_json=questions_json,
            is_active=True,
        )
        db.add(survey)
        await db.commit()
        await db.refresh(survey)
        return survey

    async def list_surveys(
        self,
        db: AsyncSession,
        hackathon_id: uuid.UUID,
        include_inactive: bool = False,
    ) -> list[Survey]:
        """List surveys for a hackathon.

        Behavior:
        1. Query Survey rows filtered by hackathon_id.
        2. Optionally filter to only active surveys.
        3. Return the list of Survey instances.

        Raises: None
        Side Effects: None (read-only).
        """
        stmt = select(Survey).where(Survey.hackathon_id == hackathon_id)
        if not include_inactive:
            stmt = stmt.where(Survey.is_active.is_(True))
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_survey(self, db: AsyncSession, survey_id: uuid.UUID) -> Survey | None:
        """Load a survey by ID.

        Raises: None
        Side Effects: None (read-only).
        """
        result = await db.execute(select(Survey).where(Survey.id == survey_id))
        return result.scalar_one_or_none()

    async def submit_response(
        self,
        db: AsyncSession,
        survey_id: uuid.UUID,
        user_id: str,
        answers_json: dict,
        nps_score: int | None = None,
    ) -> SurveyResponse:
        """Submit a response to a survey.

        Behavior:
        1. Verify the survey exists and is active.
        2. Check the user hasn't already responded (optional guard).
        3. Create a SurveyResponse row.
        4. Commit and return.

        Raises: ValueError if the survey is not found or inactive, or if the user already responded.
        Side Effects: Inserts a SurveyResponse row.
        """
        survey = await self.get_survey(db, survey_id)
        if not survey:
            raise ValueError("Survey not found")
        if not survey.is_active:
            raise ValueError("Survey is not active")

        existing = await db.execute(
            select(SurveyResponse).where(
                SurveyResponse.survey_id == survey_id,
                SurveyResponse.user_id == user_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("User has already responded to this survey")

        response = SurveyResponse(
            survey_id=survey_id,
            user_id=user_id,
            answers_json=answers_json,
            nps_score=nps_score,
            submitted_at=datetime.now(UTC),
        )
        db.add(response)
        await db.commit()
        await db.refresh(response)
        return response

    async def get_results(self, db: AsyncSession, survey_id: uuid.UUID) -> dict:
        """Aggregate survey results.

        Behavior:
        1. Load the survey.
        2. Count total responses.
        3. Compute average NPS score.
        4. Collect all answers_json for downstream analysis.

        Raises: ValueError if survey not found.
        Side Effects: None (read-only).
        """
        survey = await self.get_survey(db, survey_id)
        if not survey:
            raise ValueError("Survey not found")

        count_result = await db.execute(
            select(func.count(SurveyResponse.id)).where(SurveyResponse.survey_id == survey_id)
        )
        total_responses = count_result.scalar() or 0

        avg_nps_result = await db.execute(
            select(func.avg(SurveyResponse.nps_score)).where(
                SurveyResponse.survey_id == survey_id,
                SurveyResponse.nps_score.isnot(None),
            )
        )
        avg_nps = avg_nps_result.scalar()

        # NPS distribution
        nps_dist_result = await db.execute(
            select(SurveyResponse.nps_score, func.count(SurveyResponse.id))
            .where(
                SurveyResponse.survey_id == survey_id,
                SurveyResponse.nps_score.isnot(None),
            )
            .group_by(SurveyResponse.nps_score)
        )
        nps_distribution = {str(score): count for score, count in nps_dist_result.all()}

        # NPS categories
        promoters_result = await db.execute(
            select(func.count(SurveyResponse.id)).where(
                SurveyResponse.survey_id == survey_id,
                SurveyResponse.nps_score >= 9,
            )
        )
        promoters = promoters_result.scalar() or 0

        passives_result = await db.execute(
            select(func.count(SurveyResponse.id)).where(
                SurveyResponse.survey_id == survey_id,
                SurveyResponse.nps_score.between(7, 8),
            )
        )
        passives = passives_result.scalar() or 0

        detractors_result = await db.execute(
            select(func.count(SurveyResponse.id)).where(
                SurveyResponse.survey_id == survey_id,
                SurveyResponse.nps_score <= 6,
            )
        )
        detractors = detractors_result.scalar() or 0

        nps = round(((promoters - detractors) / total_responses) * 100, 2) if total_responses > 0 else 0.0

        return {
            "survey_id": str(survey_id),
            "title": survey.title,
            "total_responses": total_responses,
            "avg_nps_score": round(float(avg_nps), 2) if avg_nps is not None else None,
            "nps": nps,
            "promoters": promoters,
            "passives": passives,
            "detractors": detractors,
            "nps_distribution": nps_distribution,
        }
