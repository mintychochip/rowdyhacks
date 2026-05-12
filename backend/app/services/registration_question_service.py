"""Service for registration question CRUD and answer validation."""

import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RegistrationAnswer, RegistrationQuestion, QuestionType


class RegistrationQuestionService:
    """Business logic for custom registration questions and answers."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_questions_for_hackathon(self, hackathon_id: uuid.UUID) -> list[RegistrationQuestion]:
        """Return all questions for a hackathon, ordered by sort_order."""
        result = await self.db.execute(
            select(RegistrationQuestion)
            .where(RegistrationQuestion.hackathon_id == hackathon_id)
            .order_by(RegistrationQuestion.sort_order)
        )
        return list(result.scalars().all())

    async def validate_answers(
        self,
        hackathon_id: uuid.UUID,
        answers: list[dict[str, Any]],
    ) -> list[RegistrationAnswer]:
        """Validate a list of answers against the hackathon's questions.

        Returns a list of RegistrationAnswer objects ready to be added to the DB.
        Raises ValueError with descriptive message on validation failure.
        """
        # Fetch all questions for this hackathon
        questions_result = await self.db.execute(
            select(RegistrationQuestion).where(RegistrationQuestion.hackathon_id == hackathon_id)
        )
        questions = {q.id: q for q in questions_result.scalars().all()}

        # Build lookup for required questions
        required_question_ids = {q.id for q in questions.values() if q.is_required}
        answered_question_ids = set()

        result = []
        for ans in answers:
            qid = ans.get("question_id")
            if not qid:
                raise ValueError("Each answer must have a question_id")
            try:
                qid_uuid = uuid.UUID(qid)
            except ValueError:
                raise ValueError(f"Invalid question_id: {qid}")

            answered_question_ids.add(qid_uuid)
            question = questions.get(qid_uuid)
            if not question:
                raise ValueError(f"Question {qid} does not exist for this hackathon")

            value = ans.get("value")
            validated_value = self._validate_answer_value(question, value)
            result.append(
                RegistrationAnswer(
                    question_id=qid_uuid,
                    answer_value=validated_value,
                )
            )

        # Check all required questions are answered
        missing = required_question_ids - answered_question_ids
        if missing:
            raise ValueError(f"Missing required answers for questions: {[str(m) for m in missing]}")

        return result

    def _validate_answer_value(self, question: RegistrationQuestion, value: Any) -> str:
        """Validate a single answer value against its question type.

        Returns the string to store in answer_value (JSON for structured types).
        """
        qt = question.question_type

        if qt == QuestionType.text:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Question '{question.question_text}': text answer must be a non-empty string")
            if len(value) > 500:
                raise ValueError(f"Question '{question.question_text}': text answer exceeds 500 characters")
            return value

        if qt == QuestionType.textarea:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Question '{question.question_text}': textarea answer must be a non-empty string")
            if len(value) > 2000:
                raise ValueError(f"Question '{question.question_text}': textarea answer exceeds 2000 characters")
            return value

        if qt == QuestionType.number:
            if not isinstance(value, (int, float)):
                raise ValueError(f"Question '{question.question_text}': number answer must be numeric")
            return str(value)

        if qt == QuestionType.select:
            if not isinstance(value, str):
                raise ValueError(f"Question '{question.question_text}': select answer must be a string")
            options = question.options or []
            if value not in options:
                raise ValueError(f"Question '{question.question_text}': '{value}' is not a valid option")
            return value

        if qt == QuestionType.multiselect:
            if not isinstance(value, list):
                raise ValueError(f"Question '{question.question_text}': multiselect answer must be a list")
            options = question.options or []
            for v in value:
                if v not in options:
                    raise ValueError(f"Question '{question.question_text}': '{v}' is not a valid option")
            return json.dumps(value)

        if qt == QuestionType.checkbox:
            if not isinstance(value, bool):
                raise ValueError(f"Question '{question.question_text}': checkbox answer must be a boolean")
            return json.dumps(value)

        if qt == QuestionType.url:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Question '{question.question_text}': URL answer must be a non-empty string")
            # Basic URL format check
            if not value.startswith(("http://", "https://")):
                raise ValueError(f"Question '{question.question_text}': URL must start with http:// or https://")
            return value

        if qt == QuestionType.file:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Question '{question.question_text}': file answer must be a URL string")
            return value

        raise ValueError(f"Unknown question type: {qt}")

    async def create_question(
        self,
        hackathon_id: uuid.UUID,
        question_text: str,
        question_type: str,
        options: list[str] | None,
        is_required: bool,
        sort_order: int,
    ) -> RegistrationQuestion:
        """Create and persist a new registration question."""
        qt = QuestionType(question_type)
        if qt in (QuestionType.select, QuestionType.multiselect):
            if not options:
                raise ValueError(f"Question type '{qt.value}' requires options")
        else:
            if options is not None:
                raise ValueError(f"Question type '{qt.value}' does not accept options")

        question = RegistrationQuestion(
            hackathon_id=hackathon_id,
            question_text=question_text,
            question_type=qt,
            options=options,
            is_required=is_required,
            sort_order=sort_order,
        )
        self.db.add(question)
        await self.db.commit()
        await self.db.refresh(question)
        return question
