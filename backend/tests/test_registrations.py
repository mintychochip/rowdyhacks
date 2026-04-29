"""Tests for participant registration routes (Tasks 2.2-2.4)."""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User, Hackathon, UserRole, Hackathon
from datetime import datetime, timezone


async def _create_user(db, email, name, password="password123", role=UserRole.participant):
    from app.auth import hash_password
    user = User(id=uuid.uuid4(), email=email, name=name,
                password_hash=hash_password(password), role=role)
    db.add(user)
    await db.commit()
    return user


async def _create_hackathon(db, name, organizer):
    h = Hackathon(id=uuid.uuid4(), name=name, organizer_id=organizer.id,
                  start_date=datetime.now(timezone.utc),
                  end_date=datetime.now(timezone.utc))
    db.add(h)
    await db.commit()
    return h


def _auth_headers(user):
    from app.auth import create_access_token
    token = create_access_token(str(user.id), user.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_register_for_hackathon(client: AsyncClient, db_session: AsyncSession):
    """Task 2.2: Register for a hackathon."""
    user = await _create_user(db_session, "regtest@test.com", "Reg User")
    hackathon = await _create_hackathon(db_session, "RegHack", user)
    headers = _auth_headers(user)

    response = await client.post(
        f"/api/hackathons/{hackathon.id}/register",
        json={"team_name": "Dream Team", "team_members": ["Alice", "Bob"]},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert data["team_name"] == "Dream Team"
    assert data["team_members"] == ["Alice", "Bob"]
    assert data["hackathon_id"] == str(hackathon.id)
    assert data["user_id"] == str(user.id)
    # QR token should NOT be set at registration time
    assert data["qr_token"] is None


@pytest.mark.asyncio
async def test_register_duplicate(client: AsyncClient, db_session: AsyncSession):
    """Task 2.2: Duplicate registration returns 409."""
    user = await _create_user(db_session, "dup@test.com", "Dup User")
    hackathon = await _create_hackathon(db_session, "DupHack", user)
    headers = _auth_headers(user)

    await client.post(
        f"/api/hackathons/{hackathon.id}/register",
        json={"team_name": "Dream Team"},
        headers=headers,
    )
    response = await client.post(
        f"/api/hackathons/{hackathon.id}/register",
        json={"team_name": "Dream Team"},
        headers=headers,
    )
    assert response.status_code == 409
    assert "Already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_nonexistent_hackathon(client: AsyncClient, db_session: AsyncSession):
    """Task 2.2: Registering for a non-existent hackathon returns 404."""
    user = await _create_user(db_session, "nope@test.com", "Nope User")
    headers = _auth_headers(user)

    fake_id = uuid.uuid4()
    response = await client.post(
        f"/api/hackathons/{fake_id}/register",
        json={"team_name": "Ghost Team"},
        headers=headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_my_registrations(client: AsyncClient, db_session: AsyncSession):
    """Task 2.3: List own registrations."""
    user = await _create_user(db_session, "list@test.com", "List User")
    hackathon = await _create_hackathon(db_session, "ListHack", user)
    headers = _auth_headers(user)

    resp = await client.post(
        f"/api/hackathons/{hackathon.id}/register",
        json={"team_name": "My Team"},
        headers=headers,
    )
    assert resp.status_code == 201

    response = await client.get("/api/registrations", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["registrations"]) == 1
    assert data["registrations"][0]["team_name"] == "My Team"
    assert data["total"] == 1
    assert data["limit"] == 20
    assert data["offset"] == 0


@pytest.mark.asyncio
async def test_cannot_see_others_registration(client: AsyncClient, db_session: AsyncSession):
    """Task 2.3: RLS - user cannot see another user's registrations."""
    user1 = await _create_user(db_session, "user1@test.com", "User One")
    hackathon = await _create_hackathon(db_session, "PrivateHack", user1)
    headers1 = _auth_headers(user1)

    await client.post(
        f"/api/hackathons/{hackathon.id}/register",
        json={"team_name": "Team One"},
        headers=headers1,
    )

    user2 = await _create_user(db_session, "other@test.com", "Other User")
    headers2 = _auth_headers(user2)
    response = await client.get("/api/registrations", headers=headers2)
    assert response.status_code == 200
    data = response.json()
    assert len(data["registrations"]) == 0


@pytest.mark.asyncio
async def test_get_my_registration_detail(client: AsyncClient, db_session: AsyncSession):
    """Task 2.4: Get detail of own registration."""
    user = await _create_user(db_session, "detail@test.com", "Detail User")
    hackathon = await _create_hackathon(db_session, "DetailHack", user)
    headers = _auth_headers(user)

    resp = await client.post(
        f"/api/hackathons/{hackathon.id}/register",
        json={"team_name": "Detail Team"},
        headers=headers,
    )
    reg_id = resp.json()["id"]

    response = await client.get(f"/api/registrations/{reg_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["team_name"] == "Detail Team"
    assert response.json()["id"] == reg_id


@pytest.mark.asyncio
async def test_cannot_get_others_registration_detail(client: AsyncClient, db_session: AsyncSession):
    """Task 2.4: RLS - cannot get another user's registration detail (404, not 403)."""
    user1 = await _create_user(db_session, "private@test.com", "Private User")
    hackathon = await _create_hackathon(db_session, "PrivateHack", user1)
    headers1 = _auth_headers(user1)

    resp = await client.post(
        f"/api/hackathons/{hackathon.id}/register",
        json={"team_name": "Private Team"},
        headers=headers1,
    )
    reg_id = resp.json()["id"]

    user2 = await _create_user(db_session, "intruder@test.com", "Intruder")
    headers2 = _auth_headers(user2)
    response = await client.get(f"/api/registrations/{reg_id}", headers=headers2)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_register_requires_auth(client: AsyncClient, db_session: AsyncSession):
    """Task 2.2: Registration requires authentication."""
    user = await _create_user(db_session, "noauth@test.com", "No Auth")
    hackathon = await _create_hackathon(db_session, "NoAuthHack", user)

    # No auth header at all -> 422 (FastAPI required header validation)
    response = await client.post(
        f"/api/hackathons/{hackathon.id}/register",
        json={"team_name": "Ghost Team"},
    )
    assert response.status_code == 422

    # Invalid token -> 401
    response = await client.post(
        f"/api/hackathons/{hackathon.id}/register",
        json={"team_name": "Ghost Team"},
        headers={"Authorization": "Bearer invalidtoken"},
    )
    assert response.status_code == 401
