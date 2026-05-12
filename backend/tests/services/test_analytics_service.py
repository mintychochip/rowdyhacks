"""Tests for AnalyticsService."""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import (
    Hackathon,
    Registration,
    RegistrationStatus,
    Submission,
    SubmissionStatus,
    Team,
    TeamMember,
    User,
    UserRole,
    Verdict,
    Workshop,
    WorkshopRSVP,
    WorkshopRSVPStatus,
)
from app.routes.hackathons import router as hackathons_router
from app.services.analytics_service import AnalyticsService

app = FastAPI()
app.include_router(hackathons_router)


@pytest_asyncio.fixture
async def analytics_client(engine):
    async_session_maker = __import__("sqlalchemy.ext.asyncio", fromlist=["async_sessionmaker"]).async_sessionmaker

    async def override_get_db():
        async with async_session_maker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
            yield session

    from app.clerk_auth import require_clerk_user_with_db

    async def _override_require_clerk_user_with_db():
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
    app.dependency_overrides[require_clerk_user_with_db] = _override_require_clerk_user_with_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def analytics_hackathon(db_session: AsyncSession):
    from datetime import UTC, datetime

    await db_session.execute(delete(WorkshopRSVP))
    await db_session.execute(delete(Workshop))
    await db_session.execute(delete(TeamMember))
    await db_session.execute(delete(Team))
    await db_session.execute(delete(Submission))
    await db_session.execute(delete(Registration))
    await db_session.execute(delete(Hackathon))
    await db_session.execute(delete(User))
    await db_session.commit()

    organizer = User(
        id="test-organizer-id",
        email="organizer@test.com",
        name="Organizer",
        role=UserRole.organizer,
    )
    db_session.add(organizer)

    hackathon = Hackathon(
        name="Analytics Hack",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id="test-organizer-id",
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)

    return hackathon


@pytest.mark.anyio
async def test_registration_funnel(db_session: AsyncSession, analytics_hackathon):

    hackathon = analytics_hackathon
    service = AnalyticsService()

    for i, status in enumerate(
        [
            RegistrationStatus.pending,
            RegistrationStatus.accepted,
            RegistrationStatus.accepted,
            RegistrationStatus.checked_in,
            RegistrationStatus.rejected,
            RegistrationStatus.waitlisted,
        ]
    ):
        user = User(
            id=f"user-{i}",
            email=f"user{i}@test.com",
            name=f"User {i}",
            role=UserRole.participant,
        )
        db_session.add(user)
        reg = Registration(
            hackathon_id=hackathon.id,
            user_id=user.id,
            status=status,
        )
        db_session.add(reg)

    await db_session.commit()

    funnel = await service.get_registration_funnel(db_session, hackathon.id)
    assert funnel["applied"] == 6
    assert funnel["pending"] == 1
    assert funnel["accepted"] == 2
    assert funnel["checked_in"] == 1
    assert funnel["rejected"] == 1
    assert funnel["waitlisted"] == 1


@pytest.mark.anyio
async def test_attendance_metrics(db_session: AsyncSession, analytics_hackathon):

    hackathon = analytics_hackathon
    service = AnalyticsService()

    for i, status in enumerate(
        [
            RegistrationStatus.accepted,
            RegistrationStatus.accepted,
            RegistrationStatus.checked_in,
        ]
    ):
        user = User(
            id=f"att-user-{i}",
            email=f"att{i}@test.com",
            name=f"Att {i}",
            role=UserRole.participant,
        )
        db_session.add(user)
        reg = Registration(
            hackathon_id=hackathon.id,
            user_id=user.id,
            status=status,
        )
        db_session.add(reg)

    await db_session.commit()

    metrics = await service.get_attendance_metrics(db_session, hackathon.id)
    assert metrics["accepted"] == 2
    assert metrics["checked_in"] == 1
    assert metrics["attendance_rate"] == 33.33
    assert metrics["no_show_rate"] == 66.67


@pytest.mark.anyio
async def test_workshop_engagement(db_session: AsyncSession, analytics_hackathon):
    from datetime import UTC, datetime

    hackathon = analytics_hackathon
    service = AnalyticsService()

    ws = Workshop(
        hackathon_id=hackathon.id,
        title="Intro to Python",
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC),
    )
    db_session.add(ws)
    await db_session.commit()
    await db_session.refresh(ws)

    for i in range(3):
        user = User(
            id=f"ws-user-{i}",
            email=f"ws{i}@test.com",
            name=f"WS {i}",
            role=UserRole.participant,
        )
        db_session.add(user)
        rsvp = WorkshopRSVP(
            user_id=user.id,
            workshop_id=ws.id,
            hackathon_id=hackathon.id,
            status=WorkshopRSVPStatus.registered if i < 2 else WorkshopRSVPStatus.attended,
        )
        db_session.add(rsvp)

    await db_session.commit()

    engagement = await service.get_workshop_engagement(db_session, hackathon.id)
    assert len(engagement) == 1
    assert engagement[0]["rsvps"] == 3
    assert engagement[0]["attended"] == 1


@pytest.mark.anyio
async def test_team_formation_stats(db_session: AsyncSession, analytics_hackathon):

    hackathon = analytics_hackathon
    service = AnalyticsService()

    # Two accepted users, one in a team, one solo
    user_a = User(id="team-user-a", email="a@test.com", name="A", role=UserRole.participant)
    user_b = User(id="team-user-b", email="b@test.com", name="B", role=UserRole.participant)
    db_session.add_all([user_a, user_b])

    reg_a = Registration(hackathon_id=hackathon.id, user_id=user_a.id, status=RegistrationStatus.accepted)
    reg_b = Registration(hackathon_id=hackathon.id, user_id=user_b.id, status=RegistrationStatus.accepted)
    db_session.add_all([reg_a, reg_b])

    team = Team(hackathon_id=hackathon.id, name="Alpha", join_code="ALPHA", captain_id=user_a.id)
    db_session.add(team)
    await db_session.commit()
    await db_session.refresh(team)

    member = TeamMember(team_id=team.id, user_id=user_a.id)
    db_session.add(member)
    await db_session.commit()

    stats = await service.get_team_formation_stats(db_session, hackathon.id)
    assert stats["teams_formed"] == 1
    assert stats["total_team_members"] == 1
    assert stats["avg_team_size"] == 1.0
    assert stats["solo_hackers"] == 1


@pytest.mark.anyio
async def test_submission_stats(db_session: AsyncSession, analytics_hackathon):
    hackathon = analytics_hackathon
    service = AnalyticsService()

    sub1 = Submission(
        devpost_url="https://devpost.com/software/a",
        hackathon_id=hackathon.id,
        risk_score=20,
        verdict=Verdict.clean,
        status=SubmissionStatus.completed,
    )
    sub2 = Submission(
        devpost_url="https://devpost.com/software/b",
        hackathon_id=hackathon.id,
        risk_score=40,
        verdict=Verdict.review,
        status=SubmissionStatus.completed,
    )
    db_session.add_all([sub1, sub2])
    await db_session.commit()

    stats = await service.get_submission_stats(db_session, hackathon.id)
    assert stats["total_submissions"] == 2
    assert stats["avg_risk_score"] == 30.0
    assert stats["by_verdict"]["clean"] == 1
    assert stats["by_verdict"]["review"] == 1


@pytest.mark.anyio
async def test_demographics(db_session: AsyncSession, analytics_hackathon):
    hackathon = analytics_hackathon
    service = AnalyticsService()

    user = User(
        id="demo-user",
        email="demo@test.com",
        name="Demo",
        role=UserRole.participant,
    )
    db_session.add(user)
    reg = Registration(
        hackathon_id=hackathon.id,
        user_id=user.id,
        status=RegistrationStatus.accepted,
        school="UTSA",
        major="CS",
        experience_level="Intermediate",
        age=20,
    )
    db_session.add(reg)
    await db_session.commit()

    demo = await service.get_demographics(db_session, hackathon.id)
    assert demo["schools"]["UTSA"] == 1
    assert demo["majors"]["CS"] == 1
    assert demo["experience_levels"]["Intermediate"] == 1
    assert demo["ages"][20] == 1
    assert demo["total_respondents"] == 1


@pytest.mark.anyio
async def test_get_all_metrics(analytics_client, analytics_hackathon):
    hackathon = analytics_hackathon
    resp = await analytics_client.get(f"/api/hackathons/{hackathon.id}/analytics")
    assert resp.status_code == 200
    data = resp.json()
    assert "registration_funnel" in data
    assert "attendance" in data
    assert "workshops" in data
    assert "teams" in data
    assert "submissions" in data
    assert "demographics" in data


@pytest.mark.anyio
async def test_analytics_forbidden_for_participant(engine):
    async_session_maker = __import__("sqlalchemy.ext.asyncio", fromlist=["async_sessionmaker"]).async_sessionmaker

    async def override_get_db():
        async with async_session_maker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
            yield session

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

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_clerk_user_with_db] = _override_participant
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        from datetime import UTC, datetime
        from sqlalchemy import delete
        from app.models import Hackathon

        async with async_session_maker(engine, class_=AsyncSession, expire_on_commit=False)() as s:
            await s.execute(delete(Hackathon))
            h = Hackathon(
                name="Forbidden Hack",
                start_date=datetime.now(UTC),
                end_date=datetime.now(UTC),
                organizer_id="test-organizer-id",
            )
            s.add(h)
            await s.commit()
            await s.refresh(h)
            resp = await ac.get(f"/api/hackathons/{h.id}/analytics")
            assert resp.status_code == 403
    app.dependency_overrides.clear()
