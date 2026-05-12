"""Tests for RegistrationQuestionService."""

import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Hackathon, RegistrationQuestion, QuestionType, User, UserRole
from app.services.registration_question_service import RegistrationQuestionService


@pytest_asyncio.fixture
async def hackathon_and_question(db_session: AsyncSession):
    """Create a hackathon with a custom question."""
    uid = uuid.uuid4().hex[:8]
    user = User(id=f"org-{uid}", email=f"org-{uid}@example.com", name="Test Organizer", role=UserRole.organizer)
    db_session.add(user)

    hackathon = Hackathon(
        name="Test Hack",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id=user.id,
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)

    question = RegistrationQuestion(
        hackathon_id=hackathon.id,
        question_text="Favorite language?",
        question_type=QuestionType.select,
        options=["Python", "JavaScript"],
        is_required=True,
        sort_order=1,
    )
    db_session.add(question)
    await db_session.commit()
    await db_session.refresh(question)

    return hackathon, question


@pytest_asyncio.fixture
async def participant(db_session: AsyncSession):
    uid = uuid.uuid4().hex[:8]
    user = User(id=f"part-{uid}", email=f"part-{uid}@example.com", name="Test Participant", role=UserRole.participant)
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.mark.anyio
async def test_get_questions_for_hackathon(db_session: AsyncSession, hackathon_and_question):
    hackathon, _ = hackathon_and_question
    service = RegistrationQuestionService(db_session)
    questions = await service.get_questions_for_hackathon(hackathon.id)
    assert len(questions) == 1
    assert questions[0].question_text == "Favorite language?"


@pytest.mark.anyio
async def test_validate_answers_success(db_session: AsyncSession, hackathon_and_question, participant):
    hackathon, question = hackathon_and_question
    service = RegistrationQuestionService(db_session)

    answers = await service.validate_answers(
        hackathon_id=hackathon.id,
        answers=[{"question_id": str(question.id), "value": "Python"}],
    )
    assert len(answers) == 1
    assert answers[0].answer_value == "Python"


@pytest.mark.anyio
async def test_validate_answers_missing_required(db_session: AsyncSession, hackathon_and_question):
    hackathon, question = hackathon_and_question
    service = RegistrationQuestionService(db_session)

    with pytest.raises(ValueError, match="Missing required answers"):
        await service.validate_answers(
            hackathon_id=hackathon.id,
            answers=[],
        )


@pytest.mark.anyio
async def test_validate_answers_invalid_option(db_session: AsyncSession, hackathon_and_question):
    hackathon, question = hackathon_and_question
    service = RegistrationQuestionService(db_session)

    with pytest.raises(ValueError, match="not a valid option"):
        await service.validate_answers(
            hackathon_id=hackathon.id,
            answers=[{"question_id": str(question.id), "value": "C++"}],
        )


@pytest.mark.anyio
async def test_validate_answers_invalid_question(db_session: AsyncSession, hackathon_and_question):
    hackathon, _ = hackathon_and_question
    service = RegistrationQuestionService(db_session)

    with pytest.raises(ValueError, match="does not exist"):
        await service.validate_answers(
            hackathon_id=hackathon.id,
            answers=[{"question_id": str(uuid.uuid4()), "value": "Python"}],
        )


@pytest.mark.anyio
async def test_create_question(db_session: AsyncSession, hackathon_and_question):
    hackathon, _ = hackathon_and_question
    service = RegistrationQuestionService(db_session)

    question = await service.create_question(
        hackathon_id=hackathon.id,
        question_text="Tell us about yourself",
        question_type="textarea",
        options=None,
        is_required=False,
        sort_order=2,
    )
    assert question.question_type == QuestionType.textarea
    assert question.is_required is False


@pytest.mark.anyio
async def test_create_question_select_requires_options(db_session: AsyncSession, hackathon_and_question):
    hackathon, _ = hackathon_and_question
    service = RegistrationQuestionService(db_session)

    with pytest.raises(ValueError, match="requires options"):
        await service.create_question(
            hackathon_id=hackathon.id,
            question_text="Pick one",
            question_type="select",
            options=None,
            is_required=True,
            sort_order=0,
        )


@pytest.mark.anyio
async def test_validate_text_answer(db_session: AsyncSession, hackathon_and_question):
    hackathon, fixture_question = hackathon_and_question
    service = RegistrationQuestionService(db_session)

    question = RegistrationQuestion(
        hackathon_id=hackathon.id,
        question_text="Short bio",
        question_type=QuestionType.text,
        is_required=True,
    )
    db_session.add(question)
    await db_session.commit()

    answers = await service.validate_answers(
        hackathon_id=hackathon.id,
        answers=[
            {"question_id": str(fixture_question.id), "value": "Python"},
            {"question_id": str(question.id), "value": "Hello world"},
        ],
    )
    assert len(answers) == 2
    assert any(a.answer_value == "Hello world" for a in answers)


@pytest.mark.anyio
async def test_validate_number_answer(db_session: AsyncSession, hackathon_and_question):
    hackathon, fixture_question = hackathon_and_question
    service = RegistrationQuestionService(db_session)

    question = RegistrationQuestion(
        hackathon_id=hackathon.id,
        question_text="Years of experience",
        question_type=QuestionType.number,
        is_required=True,
    )
    db_session.add(question)
    await db_session.commit()

    answers = await service.validate_answers(
        hackathon_id=hackathon.id,
        answers=[
            {"question_id": str(fixture_question.id), "value": "Python"},
            {"question_id": str(question.id), "value": 5},
        ],
    )
    assert any(a.answer_value == "5" for a in answers)


@pytest.mark.anyio
async def test_validate_checkbox_answer(db_session: AsyncSession, hackathon_and_question):
    hackathon, fixture_question = hackathon_and_question
    service = RegistrationQuestionService(db_session)

    question = RegistrationQuestion(
        hackathon_id=hackathon.id,
        question_text="Agree to terms",
        question_type=QuestionType.checkbox,
        is_required=True,
    )
    db_session.add(question)
    await db_session.commit()

    answers = await service.validate_answers(
        hackathon_id=hackathon.id,
        answers=[
            {"question_id": str(fixture_question.id), "value": "Python"},
            {"question_id": str(question.id), "value": True},
        ],
    )
    import json

    checkbox_answer = next(a for a in answers if a.question_id == question.id)
    assert json.loads(checkbox_answer.answer_value) is True


@pytest.mark.anyio
async def test_validate_multiselect_answer(db_session: AsyncSession, hackathon_and_question):
    hackathon, fixture_question = hackathon_and_question
    service = RegistrationQuestionService(db_session)

    question = RegistrationQuestion(
        hackathon_id=hackathon.id,
        question_text="Interests",
        question_type=QuestionType.multiselect,
        options=["AI", "Web", "Mobile"],
        is_required=True,
    )
    db_session.add(question)
    await db_session.commit()

    answers = await service.validate_answers(
        hackathon_id=hackathon.id,
        answers=[
            {"question_id": str(fixture_question.id), "value": "Python"},
            {"question_id": str(question.id), "value": ["AI", "Web"]},
        ],
    )
    import json

    multi_answer = next(a for a in answers if a.question_id == question.id)
    assert json.loads(multi_answer.answer_value) == ["AI", "Web"]


@pytest.mark.anyio
async def test_validate_url_answer(db_session: AsyncSession, hackathon_and_question):
    hackathon, fixture_question = hackathon_and_question
    service = RegistrationQuestionService(db_session)

    question = RegistrationQuestion(
        hackathon_id=hackathon.id,
        question_text="Portfolio URL",
        question_type=QuestionType.url,
        is_required=True,
    )
    db_session.add(question)
    await db_session.commit()

    answers = await service.validate_answers(
        hackathon_id=hackathon.id,
        answers=[
            {"question_id": str(fixture_question.id), "value": "Python"},
            {"question_id": str(question.id), "value": "https://example.com"},
        ],
    )
    assert any(a.answer_value == "https://example.com" for a in answers)


@pytest.mark.anyio
async def test_validate_url_answer_invalid(db_session: AsyncSession, hackathon_and_question):
    hackathon, fixture_question = hackathon_and_question
    service = RegistrationQuestionService(db_session)

    question = RegistrationQuestion(
        hackathon_id=hackathon.id,
        question_text="Portfolio URL",
        question_type=QuestionType.url,
        is_required=True,
    )
    db_session.add(question)
    await db_session.commit()

    with pytest.raises(ValueError, match="URL must start with"):
        await service.validate_answers(
            hackathon_id=hackathon.id,
            answers=[
                {"question_id": str(fixture_question.id), "value": "Python"},
                {"question_id": str(question.id), "value": "example.com"},
            ],
        )
