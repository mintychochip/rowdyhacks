"""Tests for registration review note routes."""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Hackathon, Registration, RegistrationStatus, User, UserRole
from app.routes.registration_notes import router as notes_router

app = FastAPI()
app.include_router(notes_router)


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
async def notes_client(engine):
    async_session_maker = __import__("sqlalchemy.ext.asyncio", fromlist=["async_sessionmaker"]).async_sessionmaker

    async def override_get_db():
        async with async_session_maker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
            yield session

    from app.clerk_auth import require_hackathon_organizer

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_hackathon_organizer] = _override_require_hackathon_organizer
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def hackathon_with_registration(db_session: AsyncSession):
    from datetime import UTC, datetime
    from sqlalchemy import delete

    await db_session.execute(delete(Registration))
    await db_session.execute(delete(Hackathon))
    await db_session.execute(delete(User))
    await db_session.commit()

    org = User(id="test-organizer-id", email="organizer@test.com", name="Test Organizer", role=UserRole.organizer)
    participant = User(id="test-user-id", email="test@example.com", name="Test User", role=UserRole.participant)
    db_session.add(org)
    db_session.add(participant)

    hackathon = Hackathon(
        name="Test Hack",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id="test-organizer-id",
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)

    reg = Registration(
        hackathon_id=hackathon.id,
        user_id="test-user-id",
        status=RegistrationStatus.pending,
    )
    db_session.add(reg)
    await db_session.commit()
    await db_session.refresh(reg)

    return hackathon, reg


@pytest.mark.anyio
async def test_create_note(notes_client, hackathon_with_registration):
    hackathon, reg = hackathon_with_registration
    resp = await notes_client.post(
        f"/api/hackathons/{hackathon.id}/registrations/{reg.id}/notes",
        json={"note_text": "Strong applicant", "rating": 5},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["note_text"] == "Strong applicant"
    assert data["rating"] == 5
    assert data["organizer_id"] == "test-organizer-id"


@pytest.mark.anyio
async def test_list_notes(notes_client, hackathon_with_registration):
    hackathon, reg = hackathon_with_registration
    await notes_client.post(
        f"/api/hackathons/{hackathon.id}/registrations/{reg.id}/notes",
        json={"note_text": "Note 1", "rating": 4},
    )
    await notes_client.post(
        f"/api/hackathons/{hackathon.id}/registrations/{reg.id}/notes",
        json={"note_text": "Note 2", "rating": 3},
    )

    resp = await notes_client.get(f"/api/hackathons/{hackathon.id}/registrations/{reg.id}/notes")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["notes"]) == 2


@pytest.mark.anyio
async def test_update_note(notes_client, hackathon_with_registration):
    hackathon, reg = hackathon_with_registration
    create_resp = await notes_client.post(
        f"/api/hackathons/{hackathon.id}/registrations/{reg.id}/notes",
        json={"note_text": "Original", "rating": 2},
    )
    note_id = create_resp.json()["id"]

    resp = await notes_client.put(
        f"/api/hackathons/{hackathon.id}/registrations/{reg.id}/notes/{note_id}",
        json={"note_text": "Updated", "rating": 4},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["note_text"] == "Updated"
    assert data["rating"] == 4


@pytest.mark.anyio
async def test_delete_note(notes_client, hackathon_with_registration):
    hackathon, reg = hackathon_with_registration
    create_resp = await notes_client.post(
        f"/api/hackathons/{hackathon.id}/registrations/{reg.id}/notes",
        json={"note_text": "To delete", "rating": 2},
    )
    note_id = create_resp.json()["id"]

    resp = await notes_client.delete(f"/api/hackathons/{hackathon.id}/registrations/{reg.id}/notes/{note_id}")
    assert resp.status_code == 204

    list_resp = await notes_client.get(f"/api/hackathons/{hackathon.id}/registrations/{reg.id}/notes")
    assert len(list_resp.json()["notes"]) == 0
