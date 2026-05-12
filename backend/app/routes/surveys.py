"""Survey management routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import require_clerk_user_with_db
from app.database import get_db
from app.models import UserRole
from app.services.survey_service import SurveyService

router = APIRouter(prefix="/api/hackathons", tags=["surveys"])


class CreateSurveyRequest(BaseModel):
    """Request body for creating a survey."""

    title: str
    questions_json: dict | list


class SubmitSurveyResponseRequest(BaseModel):
    """Request body for submitting a survey response."""

    answers_json: dict | list
    nps_score: int | None = None


@router.post("/{hackathon_id}/surveys", status_code=201)
async def create_survey(
    hackathon_id: uuid.UUID,
    body: CreateSurveyRequest,
    auth: dict = Depends(require_clerk_user_with_db),
    db: AsyncSession = Depends(get_db),
):
    """Create a survey for a hackathon (organizer only).

    Behavior:
    1. Verify the user is an organizer.
    2. Create the survey via SurveyService.
    3. Return the created survey.

    Raises: HTTPException(403) if not organizer.
    """
    user = auth["user"]
    if user.role != UserRole.organizer:
        raise HTTPException(status_code=403, detail="Organizer access required")

    service = SurveyService()
    survey = await service.create_survey(
        db,
        hackathon_id=hackathon_id,
        title=body.title,
        questions_json=body.questions_json,
    )

    return {
        "id": str(survey.id),
        "hackathon_id": str(survey.hackathon_id),
        "title": survey.title,
        "questions_json": survey.questions_json,
        "is_active": survey.is_active,
        "created_at": survey.created_at.isoformat() if survey.created_at else None,
    }


@router.get("/{hackathon_id}/surveys")
async def list_surveys(
    hackathon_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """List active surveys for a hackathon.

    Behavior:
    1. Query active surveys via SurveyService.
    2. Return serialized list.

    Raises: None
    """
    service = SurveyService()
    surveys = await service.list_surveys(db, hackathon_id=hackathon_id, include_inactive=False)

    return [
        {
            "id": str(survey.id),
            "hackathon_id": str(survey.hackathon_id),
            "title": survey.title,
            "questions_json": survey.questions_json,
            "is_active": survey.is_active,
            "created_at": survey.created_at.isoformat() if survey.created_at else None,
        }
        for survey in surveys
    ]


@router.post("/surveys/{survey_id}/responses", status_code=201)
async def submit_response(
    survey_id: uuid.UUID,
    body: SubmitSurveyResponseRequest,
    auth: dict = Depends(require_clerk_user_with_db),
    db: AsyncSession = Depends(get_db),
):
    """Submit a response to a survey.

    Behavior:
    1. Submit via SurveyService.
    2. Return confirmation.

    Raises: HTTPException(400) on validation errors.
    """
    service = SurveyService()
    try:
        response = await service.submit_response(
            db,
            survey_id=survey_id,
            user_id=auth["sub"],
            answers_json=body.answers_json,
            nps_score=body.nps_score,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "id": str(response.id),
        "survey_id": str(response.survey_id),
        "submitted_at": response.submitted_at.isoformat() if response.submitted_at else None,
    }


@router.get("/surveys/{survey_id}/results")
async def get_survey_results(
    survey_id: uuid.UUID,
    auth: dict = Depends(require_clerk_user_with_db),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated survey results (organizer only).

    Behavior:
    1. Verify organizer role.
    2. Aggregate results via SurveyService.
    3. Return metrics.

    Raises: HTTPException(403) if not organizer, HTTPException(404) if survey not found.
    """
    user = auth["user"]
    if user.role != UserRole.organizer:
        raise HTTPException(status_code=403, detail="Organizer access required")

    service = SurveyService()
    try:
        results = await service.get_results(db, survey_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return results
