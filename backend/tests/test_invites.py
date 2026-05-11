"""Tests for hackathon invite code system (Task 5)."""

import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from app.auth import get_current_user, require_organizer
from app.clerk_auth import require_clerk_user
from app.main import app
from app.models import Hackathon, HackathonInvite, User, UserRole
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def _create_user(db: AsyncSession, email: str, name: str, role: UserRole = UserRole.participant):
    user = User(id=str(uuid.uuid4()), email=email, name=name, role=role)
    db.add(user)
    await db.commit()
    return user


async def _create_hackathon(db: AsyncSession, name: str, organizer: User):
    h = Hackathon(
        id=uuid.uuid4(),
        name=name,
        organizer_id=organizer.id,
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
    )
    db.add(h)
    await db.commit()
    return h


@pytest_asyncio.fixture
async def organizer_auth(client: AsyncClient, db_session: AsyncSession):
    """Create an organizer user and override auth deps to return them."""
    uid = str(uuid.uuid4())[:8]
    organizer = await _create_user(db_session, f"organizer_{uid}@test.com", "Org User", role=UserRole.organizer)

    async def _override_get_current_user():
        return organizer

    def _override_require_organizer():
        return organizer

    app.dependency_overrides[get_current_user] = _override_get_current_user
    app.dependency_overrides[require_organizer] = _override_require_organizer

    headers = {"Authorization": "Bearer test-token"}
    yield organizer, headers

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_organizer, None)


@pytest.mark.asyncio
async def test_generate_invite_codes(client: AsyncClient, db_session: AsyncSession, organizer_auth):
    organizer, headers = organizer_auth
    hackathon = await _create_hackathon(db_session, "InviteHack", organizer)

    res = await client.post(
        f"/api/hackathons/{hackathon.id}/invites",
        json={"count": 5, "role": "participant"},
        headers=headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert len(data["codes"]) == 5
    assert data["count"] == 5

    # Verify codes exist in DB
    result = await db_session.execute(select(HackathonInvite).where(HackathonInvite.hackathon_id == hackathon.id))
    invites = result.scalars().all()
    assert len(invites) == 5
    for invite in invites:
        assert invite.role == UserRole.participant
        assert invite.uses_remaining == 1


@pytest.mark.asyncio
async def test_list_invites(client: AsyncClient, db_session: AsyncSession, organizer_auth):
    organizer, headers = organizer_auth
    hackathon = await _create_hackathon(db_session, "ListInvitesHack", organizer)

    # Generate some invites
    await client.post(
        f"/api/hackathons/{hackathon.id}/invites",
        json={"count": 3, "role": "participant"},
        headers=headers,
    )

    res = await client.get(f"/api/hackathons/{hackathon.id}/invites", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 3
    assert data[0]["role"] == "participant"
    assert "uses_remaining" in data[0]
    assert "created_at" in data[0]


@pytest.mark.asyncio
async def test_revoke_invite(client: AsyncClient, db_session: AsyncSession, organizer_auth):
    organizer, headers = organizer_auth
    hackathon = await _create_hackathon(db_session, "RevokeHack", organizer)

    # Generate an invite
    res = await client.post(
        f"/api/hackathons/{hackathon.id}/invites",
        json={"count": 1, "role": "participant"},
        headers=headers,
    )
    code = res.json()["codes"][0]

    # Revoke it
    res = await client.delete(f"/api/hackathons/invites/{code}", headers=headers)
    assert res.status_code == 200
    assert "revoked" in res.json()["message"]

    # Verify in DB
    result = await db_session.execute(select(HackathonInvite).where(HackathonInvite.code == code))
    invite = result.scalar_one_or_none()
    assert invite is not None
    assert invite.uses_remaining == 0


@pytest.mark.asyncio
async def test_register_with_invite_code(client: AsyncClient, db_session: AsyncSession, organizer_auth):
    organizer, org_headers = organizer_auth
    hackathon = await _create_hackathon(db_session, "InviteOnlyHack", organizer)
    hackathon.registration_mode = "invite_only"
    await db_session.commit()

    # Generate an invite
    res = await client.post(
        f"/api/hackathons/{hackathon.id}/invites",
        json={"count": 1, "role": "participant"},
        headers=org_headers,
    )
    code = res.json()["codes"][0]

    # Create a participant user and override auth for them
    uid = str(uuid.uuid4())[:8]
    participant = await _create_user(db_session, f"participant_{uid}@test.com", "Part User", role=UserRole.participant)

    async def _override_get_current_user():
        return participant

    async def _override_require_clerk_user():
        return {"sub": participant.id, "email": participant.email}

    app.dependency_overrides[get_current_user] = _override_get_current_user
    app.dependency_overrides[require_clerk_user] = _override_require_clerk_user

    # Register with invite code
    res = await client.post(
        f"/api/hackathons/{hackathon.id}/register",
        json={"team_name": "Invited Team", "invite_code": code},
        headers={"Authorization": "Bearer test-token"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["team_name"] == "Invited Team"

    # Verify invite uses decremented
    result = await db_session.execute(select(HackathonInvite).where(HackathonInvite.code == code))
    invite = result.scalar_one()
    assert invite.uses_remaining == 0

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_clerk_user, None)


@pytest.mark.asyncio
async def test_register_invite_only_without_code(client: AsyncClient, db_session: AsyncSession, organizer_auth):
    organizer, org_headers = organizer_auth
    hackathon = await _create_hackathon(db_session, "NoCodeHack", organizer)
    hackathon.registration_mode = "invite_only"
    await db_session.commit()

    uid = str(uuid.uuid4())[:8]
    participant = await _create_user(db_session, f"nocode_{uid}@test.com", "No Code", role=UserRole.participant)

    async def _override_get_current_user():
        return participant

    async def _override_require_clerk_user():
        return {"sub": participant.id, "email": participant.email}

    app.dependency_overrides[get_current_user] = _override_get_current_user
    app.dependency_overrides[require_clerk_user] = _override_require_clerk_user

    res = await client.post(
        f"/api/hackathons/{hackathon.id}/register",
        json={"team_name": "No Code Team"},
        headers={"Authorization": "Bearer test-token"},
    )
    assert res.status_code == 400
    assert "Invite code required" in res.json()["detail"]

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_clerk_user, None)


@pytest.mark.asyncio
async def test_register_invite_only_invalid_code(client: AsyncClient, db_session: AsyncSession, organizer_auth):
    organizer, org_headers = organizer_auth
    hackathon = await _create_hackathon(db_session, "BadCodeHack", organizer)
    hackathon.registration_mode = "invite_only"
    await db_session.commit()

    uid = str(uuid.uuid4())[:8]
    participant = await _create_user(db_session, f"badcode_{uid}@test.com", "Bad Code", role=UserRole.participant)

    async def _override_get_current_user():
        return participant

    async def _override_require_clerk_user():
        return {"sub": participant.id, "email": participant.email}

    app.dependency_overrides[get_current_user] = _override_get_current_user
    app.dependency_overrides[require_clerk_user] = _override_require_clerk_user

    res = await client.post(
        f"/api/hackathons/{hackathon.id}/register",
        json={"team_name": "Bad Code Team", "invite_code": "INVALID-CODE"},
        headers={"Authorization": "Bearer test-token"},
    )
    assert res.status_code == 400
    assert "Invalid or expired invite code" in res.json()["detail"]

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_clerk_user, None)
