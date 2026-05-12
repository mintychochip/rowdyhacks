"""Tests for project expo routes."""

import pytest
import pytest_asyncio
from fastapi import FastAPI, Header
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Hackathon, PublicVote, Submission, User, UserRole
from app.routes.project_expo import router as project_expo_router

app = FastAPI()
app.include_router(project_expo_router)


async def _override_require_clerk_user(authorization: str | None = Header(alias="Authorization", default=None)):
    user_id = "test-user-id"
    email = "test@example.com"
    if authorization and authorization.startswith("Bearer test-"):
        parts = authorization.removeprefix("Bearer test-").split(":", 1)
        user_id = parts[0]
        if len(parts) > 1:
            email = parts[1]
    return {"sub": user_id, "email": email}


async def _override_require_hackathon_organizer(hackathon_id):
    return {
        "sub": "test-organizer-id",
        "email": "organizer@test.com",
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
        "payload": {},
    }


@pytest_asyncio.fixture
async def project_expo_client(engine):
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
async def hackathon_with_submission(db_session: AsyncSession):
    from datetime import UTC, datetime
    from sqlalchemy import delete

    await db_session.execute(delete(PublicVote))
    await db_session.execute(delete(Submission))
    await db_session.execute(delete(Hackathon))
    await db_session.execute(delete(User))
    await db_session.commit()

    user = User(id="test-user-id", email="test@example.com", name="Test User", role=UserRole.participant)
    db_session.add(user)

    hackathon = Hackathon(
        name="Hack",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id="test-user-id",
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)

    submission = Submission(
        hackathon_id=hackathon.id,
        devpost_url="https://devpost.com/software/test-project",
        project_title="Test Project",
        project_description="A cool project",
        submitted_by=user.id,
        github_url="https://github.com/test/project",
        team_members=["test-user-id"],
        claimed_tech=["python", "react"],
    )
    db_session.add(submission)
    await db_session.commit()
    await db_session.refresh(submission)

    return hackathon, submission


@pytest.mark.anyio
async def test_list_project_expo_submissions(project_expo_client, hackathon_with_submission):
    hackathon, submission = hackathon_with_submission
    resp = await project_expo_client.get(f"/api/hackathons/{hackathon.id}/project-expo")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == str(submission.id)
    assert data[0]["project_title"] == "Test Project"
    assert data[0]["project_description"] == "A cool project"


@pytest.mark.anyio
async def test_cast_vote(project_expo_client, hackathon_with_submission):
    hackathon, submission = hackathon_with_submission
    resp = await project_expo_client.post(f"/api/hackathons/{hackathon.id}/project-expo/{submission.id}/vote")
    assert resp.status_code == 201
    data = resp.json()
    assert data["submission_id"] == str(submission.id)
    assert data["voter_id"] == "test-user-id"


@pytest.mark.anyio
async def test_cast_vote_duplicate(project_expo_client, hackathon_with_submission):
    hackathon, submission = hackathon_with_submission
    await project_expo_client.post(f"/api/hackathons/{hackathon.id}/project-expo/{submission.id}/vote")

    resp = await project_expo_client.post(f"/api/hackathons/{hackathon.id}/project-expo/{submission.id}/vote")
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_get_results(project_expo_client, hackathon_with_submission, db_session: AsyncSession):
    hackathon, submission = hackathon_with_submission

    other_user = User(id="other-id", email="other@example.com", name="Other User", role=UserRole.participant)
    db_session.add(other_user)
    await db_session.commit()

    await project_expo_client.post(f"/api/hackathons/{hackathon.id}/project-expo/{submission.id}/vote")
    await project_expo_client.post(
        f"/api/hackathons/{hackathon.id}/project-expo/{submission.id}/vote",
        headers={"Authorization": "Bearer test-other-id"},
    )

    resp = await project_expo_client.get(f"/api/hackathons/{hackathon.id}/project-expo/results")
    assert resp.status_code == 200
    data = resp.json()
    assert data["hackathon_id"] == str(hackathon.id)
    assert len(data["results"]) == 1
    assert data["results"][0]["submission_id"] == str(submission.id)
    assert data["results"][0]["vote_count"] == 2
