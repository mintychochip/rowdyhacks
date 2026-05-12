"""Tests for survey routes."""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Hackathon, Survey, SurveyResponse, User, UserRole
from app.routes.surveys import router as surveys_router

app = FastAPI()
app.include_router(surveys_router)


@pytest_asyncio.fixture
async def survey_client(engine):
    async_session_maker = __import__("sqlalchemy.ext.asyncio", fromlist=["async_sessionmaker"]).async_sessionmaker

    async def override_get_db():
        async with async_session_maker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
            yield session

    from app.clerk_auth import require_clerk_user_with_db

    async def _override_organizer():
        fake_user = type(
            "FakeUser",
            (),
            {
                "role": UserRole.organizer,
                "id": "test-organizer-id",
                "email": "organizer@test.com",
                "name": "Test Organizer",
            },
        )()
        return {
            "user": fake_user,
            "sub": "test-organizer-id",
            "email": "organizer@test.com",
            "payload": {},
        }

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_clerk_user_with_db] = _override_organizer
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def survey_hackathon(db_session: AsyncSession):
    from datetime import UTC, datetime

    await db_session.execute(delete(SurveyResponse))
    await db_session.execute(delete(Survey))
    await db_session.execute(delete(Hackathon))
    await db_session.execute(delete(User))
    await db_session.commit()

    user = User(id="test-organizer-id", email="org@test.com", name="Org", role=UserRole.organizer)
    db_session.add(user)

    hackathon = Hackathon(
        name="Survey Hack",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id="test-organizer-id",
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)
    return hackathon


@pytest.mark.anyio
async def test_create_survey(survey_client, survey_hackathon):
    hackathon = survey_hackathon
    resp = await survey_client.post(
        f"/api/hackathons/{hackathon.id}/surveys",
        json={
            "title": "Post-Event Survey",
            "questions_json": [{"question": "How was it?", "type": "rating"}],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Post-Event Survey"
    assert data["is_active"] is True


@pytest.mark.anyio
async def test_list_surveys(survey_client, survey_hackathon):
    hackathon = survey_hackathon
    await survey_client.post(
        f"/api/hackathons/{hackathon.id}/surveys",
        json={"title": "Survey 1", "questions_json": []},
    )
    resp = await survey_client.get(f"/api/hackathons/{hackathon.id}/surveys")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1


@pytest.mark.anyio
async def test_submit_response(survey_client, survey_hackathon, db_session: AsyncSession):
    hackathon = survey_hackathon
    create_resp = await survey_client.post(
        f"/api/hackathons/{hackathon.id}/surveys",
        json={"title": "NPS Survey", "questions_json": [{"question": "NPS?", "type": "nps"}]},
    )
    survey_id = create_resp.json()["id"]

    # Override to participant for response submission
    from app.clerk_auth import require_clerk_user_with_db

    async def _override_participant():
        fake_user = type(
            "FakeUser",
            (),
            {
                "role": UserRole.participant,
                "id": "test-participant-id",
                "email": "part@test.com",
                "name": "Part",
            },
        )()
        return {
            "user": fake_user,
            "sub": "test-participant-id",
            "email": "part@test.com",
            "payload": {},
        }

    app.dependency_overrides[require_clerk_user_with_db] = _override_participant

    resp = await survey_client.post(
        f"/api/hackathons/surveys/{survey_id}/responses",
        json={"answers_json": {"nps": 9}, "nps_score": 9},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "submitted_at" in data

    # Duplicate should fail
    resp2 = await survey_client.post(
        f"/api/hackathons/surveys/{survey_id}/responses",
        json={"answers_json": {"nps": 9}, "nps_score": 9},
    )
    assert resp2.status_code == 400

    # Restore organizer override
    async def _override_organizer():
        fake_user = type(
            "FakeUser",
            (),
            {
                "role": UserRole.organizer,
                "id": "test-organizer-id",
                "email": "organizer@test.com",
                "name": "Test Organizer",
            },
        )()
        return {
            "user": fake_user,
            "sub": "test-organizer-id",
            "email": "organizer@test.com",
            "payload": {},
        }

    app.dependency_overrides[require_clerk_user_with_db] = _override_organizer


@pytest.mark.anyio
async def test_get_survey_results(survey_client, survey_hackathon, db_session: AsyncSession):
    hackathon = survey_hackathon
    create_resp = await survey_client.post(
        f"/api/hackathons/{hackathon.id}/surveys",
        json={"title": "Results Survey", "questions_json": []},
    )
    survey_id = create_resp.json()["id"]

    from app.clerk_auth import require_clerk_user_with_db

    async def _override_participant():
        fake_user = type(
            "FakeUser",
            (),
            {
                "role": UserRole.participant,
                "id": "test-participant-id",
                "email": "part@test.com",
                "name": "Part",
            },
        )()
        return {
            "user": fake_user,
            "sub": "test-participant-id",
            "email": "part@test.com",
            "payload": {},
        }

    app.dependency_overrides[require_clerk_user_with_db] = _override_participant
    await survey_client.post(
        f"/api/hackathons/surveys/{survey_id}/responses",
        json={"answers_json": {}, "nps_score": 10},
    )

    # Restore organizer override
    async def _override_organizer():
        fake_user = type(
            "FakeUser",
            (),
            {
                "role": UserRole.organizer,
                "id": "test-organizer-id",
                "email": "organizer@test.com",
                "name": "Test Organizer",
            },
        )()
        return {
            "user": fake_user,
            "sub": "test-organizer-id",
            "email": "organizer@test.com",
            "payload": {},
        }

    app.dependency_overrides[require_clerk_user_with_db] = _override_organizer

    resp = await survey_client.get(f"/api/hackathons/surveys/{survey_id}/results")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_responses"] == 1
    assert data["promoters"] == 1
    assert data["nps"] == 100.0


@pytest.mark.anyio
async def test_survey_results_forbidden_for_participant(survey_client, survey_hackathon):
    hackathon = survey_hackathon
    create_resp = await survey_client.post(
        f"/api/hackathons/{hackathon.id}/surveys",
        json={"title": "Forbidden Results", "questions_json": []},
    )
    survey_id = create_resp.json()["id"]

    from app.clerk_auth import require_clerk_user_with_db

    async def _override_participant():
        fake_user = type(
            "FakeUser",
            (),
            {
                "role": UserRole.participant,
                "id": "test-participant-id",
                "email": "part@test.com",
                "name": "Part",
            },
        )()
        return {
            "user": fake_user,
            "sub": "test-participant-id",
            "email": "part@test.com",
            "payload": {},
        }

    app.dependency_overrides[require_clerk_user_with_db] = _override_participant
    resp = await survey_client.get(f"/api/hackathons/surveys/{survey_id}/results")
    assert resp.status_code == 403

    # Restore organizer override
    async def _override_organizer():
        fake_user = type(
            "FakeUser",
            (),
            {
                "role": UserRole.organizer,
                "id": "test-organizer-id",
                "email": "organizer@test.com",
                "name": "Test Organizer",
            },
        )()
        return {
            "user": fake_user,
            "sub": "test-organizer-id",
            "email": "organizer@test.com",
            "payload": {},
        }

    app.dependency_overrides[require_clerk_user_with_db] = _override_organizer
