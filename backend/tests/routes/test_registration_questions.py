"""Tests for registration question routes."""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Hackathon, User, UserRole
from app.routes.registration_questions import router as questions_router

app = FastAPI()
app.include_router(questions_router)


async def _override_require_clerk_user():
    return {"sub": "test-user-id", "email": "test@example.com"}


async def _override_require_hackathon_organizer(hackathon_id):
    return {
        "user": type(
            "FakeUser",
            (),
            {
                "role": UserRole.organizer,
                "id": "test-organizer-id",
                "email": "organizer@test.com",
                "name": "Test Organizer",
            },
        )(),
        "sub": "test-organizer-id",
        "email": "organizer@test.com",
        "payload": {},
    }


@pytest_asyncio.fixture
async def question_client(engine):
    async_session_maker = __import__("sqlalchemy.ext.asyncio", fromlist=["async_sessionmaker"]).async_sessionmaker

    async def override_get_db():
        async with async_session_maker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
            yield session

    from app.clerk_auth import require_clerk_user, require_hackathon_organizer

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_clerk_user] = _override_require_clerk_user
    app.dependency_overrides[require_hackathon_organizer] = _override_require_hackathon_organizer
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def hackathon_with_questions(db_session: AsyncSession):
    from datetime import UTC, datetime
    from sqlalchemy import delete
    from app.models import RegistrationQuestion

    await db_session.execute(delete(RegistrationQuestion))
    await db_session.execute(delete(Hackathon))
    await db_session.execute(delete(User))
    await db_session.commit()

    user = User(id="test-organizer-id", email="organizer@test.com", name="Test Organizer", role=UserRole.organizer)
    db_session.add(user)

    hackathon = Hackathon(
        name="Test Hack",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id="test-organizer-id",
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)

    return hackathon


@pytest.mark.anyio
async def test_create_question(question_client, hackathon_with_questions):
    hackathon = hackathon_with_questions
    resp = await question_client.post(
        f"/api/hackathons/{hackathon.id}/registration-questions",
        json={
            "question_text": "What is your favorite programming language?",
            "question_type": "select",
            "options": ["Python", "JavaScript", "Rust", "Go"],
            "is_required": True,
            "sort_order": 1,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["question_text"] == "What is your favorite programming language?"
    assert data["question_type"] == "select"
    assert data["options"] == ["Python", "JavaScript", "Rust", "Go"]


@pytest.mark.anyio
async def test_list_questions(question_client, hackathon_with_questions):
    hackathon = hackathon_with_questions
    # Create a question first
    await question_client.post(
        f"/api/hackathons/{hackathon.id}/registration-questions",
        json={
            "question_text": "Tell us about yourself",
            "question_type": "textarea",
            "is_required": False,
            "sort_order": 2,
        },
    )

    resp = await question_client.get(f"/api/hackathons/{hackathon.id}/registration-questions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["questions"]) == 1
    assert data["questions"][0]["question_type"] == "textarea"


@pytest.mark.anyio
async def test_update_question(question_client, hackathon_with_questions):
    hackathon = hackathon_with_questions
    create_resp = await question_client.post(
        f"/api/hackathons/{hackathon.id}/registration-questions",
        json={
            "question_text": "Original text",
            "question_type": "text",
            "is_required": True,
            "sort_order": 1,
        },
    )
    qid = create_resp.json()["id"]

    resp = await question_client.put(
        f"/api/hackathons/{hackathon.id}/registration-questions/{qid}",
        json={"question_text": "Updated text", "sort_order": 5},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["question_text"] == "Updated text"
    assert data["sort_order"] == 5


@pytest.mark.anyio
async def test_delete_question(question_client, hackathon_with_questions):
    hackathon = hackathon_with_questions
    create_resp = await question_client.post(
        f"/api/hackathons/{hackathon.id}/registration-questions",
        json={
            "question_text": "Delete me",
            "question_type": "text",
            "is_required": True,
            "sort_order": 3,
        },
    )
    qid = create_resp.json()["id"]

    resp = await question_client.delete(f"/api/hackathons/{hackathon.id}/registration-questions/{qid}")
    assert resp.status_code == 204

    list_resp = await question_client.get(f"/api/hackathons/{hackathon.id}/registration-questions")
    assert len(list_resp.json()["questions"]) == 0
