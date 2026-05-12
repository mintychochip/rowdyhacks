"""Routes for custom registration questions."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import require_clerk_user, require_hackathon_organizer
from app.database import get_db
from app.schemas import RegistrationQuestionCreate, RegistrationQuestionUpdate
from app.services.registration_question_service import RegistrationQuestionService
from app.storage import StorageService

router = APIRouter(prefix="/api/hackathons", tags=["registration-questions"])


@router.post("/{hackathon_id}/registration-questions", status_code=201)
async def create_question(
    hackathon_id: uuid.UUID,
    body: RegistrationQuestionCreate,
    auth: dict = Depends(require_hackathon_organizer),
    db: AsyncSession = Depends(get_db),
):
    """Create a custom registration question. Organizer only."""
    service = RegistrationQuestionService(db)
    try:
        question = await service.create_question(
            hackathon_id=hackathon_id,
            question_text=body.question_text,
            question_type=body.question_type,
            options=body.options,
            is_required=body.is_required,
            sort_order=body.sort_order,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return {
        "id": str(question.id),
        "hackathon_id": str(question.hackathon_id),
        "question_text": question.question_text,
        "question_type": question.question_type.value,
        "options": question.options,
        "is_required": question.is_required,
        "sort_order": question.sort_order,
        "created_at": question.created_at.isoformat(),
    }


@router.get("/{hackathon_id}/registration-questions")
async def list_questions(
    hackathon_id: uuid.UUID,
    auth: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """List custom registration questions for a hackathon. Logged-in users only."""
    service = RegistrationQuestionService(db)
    questions = await service.get_questions_for_hackathon(hackathon_id)
    return {
        "questions": [
            {
                "id": str(q.id),
                "question_text": q.question_text,
                "question_type": q.question_type.value,
                "options": q.options,
                "is_required": q.is_required,
                "sort_order": q.sort_order,
            }
            for q in questions
        ]
    }


@router.put("/{hackathon_id}/registration-questions/{question_id}")
async def update_question(
    hackathon_id: uuid.UUID,
    question_id: uuid.UUID,
    body: RegistrationQuestionUpdate,
    auth: dict = Depends(require_hackathon_organizer),
    db: AsyncSession = Depends(get_db),
):
    """Update a custom registration question. Organizer only."""
    from sqlalchemy import select
    from app.models import RegistrationQuestion, QuestionType

    result = await db.execute(
        select(RegistrationQuestion).where(
            RegistrationQuestion.id == question_id,
            RegistrationQuestion.hackathon_id == hackathon_id,
        )
    )
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    if body.question_text is not None:
        question.question_text = body.question_text
    if body.question_type is not None:
        question.question_type = QuestionType(body.question_type)
    if body.options is not None:
        question.options = body.options
    if body.is_required is not None:
        question.is_required = body.is_required
    if body.sort_order is not None:
        question.sort_order = body.sort_order

    await db.commit()
    await db.refresh(question)

    return {
        "id": str(question.id),
        "question_text": question.question_text,
        "question_type": question.question_type.value,
        "options": question.options,
        "is_required": question.is_required,
        "sort_order": question.sort_order,
    }


@router.delete("/{hackathon_id}/registration-questions/{question_id}", status_code=204)
async def delete_question(
    hackathon_id: uuid.UUID,
    question_id: uuid.UUID,
    auth: dict = Depends(require_hackathon_organizer),
    db: AsyncSession = Depends(get_db),
):
    """Delete a custom registration question. Organizer only."""
    from sqlalchemy import select
    from app.models import RegistrationQuestion

    result = await db.execute(
        select(RegistrationQuestion).where(
            RegistrationQuestion.id == question_id,
            RegistrationQuestion.hackathon_id == hackathon_id,
        )
    )
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    await db.delete(question)
    await db.commit()
    return None


@router.post("/{hackathon_id}/upload")
async def upload_file(
    hackathon_id: uuid.UUID,
    file: UploadFile = File(...),
    auth: dict = Depends(require_clerk_user),
):
    """Upload a file for registration answers (MinIO/S3)."""
    storage = StorageService()
    try:
        result = await storage.upload_generic(
            file,
            folder=f"hackathons/{hackathon_id}/uploads",
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return result
