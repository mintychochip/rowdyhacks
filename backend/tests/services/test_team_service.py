"""Tests for TeamService."""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Hackathon, Registration, RegistrationStatus, TeamMember, User, UserRole
from app.services.team_service import TeamService


@pytest_asyncio.fixture
async def hackathon_and_user(db_session: AsyncSession):
    """Create a hackathon and user with accepted registration (unique IDs per test)."""
    from datetime import UTC, datetime

    uid = uuid.uuid4().hex[:8]
    user = User(id=f"user-{uid}", email=f"{uid}@example.com", name="User One", role=UserRole.participant)
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

    reg = Registration(
        hackathon_id=hackathon.id,
        user_id=user.id,
        status=RegistrationStatus.accepted,
    )
    db_session.add(reg)
    await db_session.commit()

    return hackathon, user


@pytest.mark.anyio
async def test_create_team(db_session: AsyncSession, hackathon_and_user):
    """TeamService.create_team must create a team with join code and captain member."""
    hackathon, user = hackathon_and_user
    service = TeamService()

    team = await service.create_team(db_session, hackathon.id, "Team Alpha", user.id)
    assert team.name == "Team Alpha"
    assert team.join_code is not None
    assert len(team.join_code) == 8
    assert team.captain_id == user.id

    # Verify member row
    result = await db_session.execute(select(TeamMember).where(TeamMember.team_id == team.id))
    members = result.scalars().all()
    assert len(members) == 1
    assert members[0].user_id == user.id


@pytest.mark.anyio
async def test_join_team_by_code(db_session: AsyncSession, hackathon_and_user):
    """join_team_by_code must add a new member."""
    hackathon, user = hackathon_and_user
    service = TeamService()

    team = await service.create_team(db_session, hackathon.id, "Team Beta", user.id)

    uid2 = uuid.uuid4().hex[:8]
    user2 = User(id=f"user-{uid2}", email=f"{uid2}@example.com", name="User Two", role=UserRole.participant)
    db_session.add(user2)
    reg2 = Registration(
        hackathon_id=hackathon.id,
        user_id=user2.id,
        status=RegistrationStatus.accepted,
    )
    db_session.add(reg2)
    await db_session.commit()

    joined = await service.join_team_by_code(db_session, team.join_code, user2.id)
    assert joined.id == team.id

    result = await db_session.execute(select(TeamMember).where(TeamMember.team_id == team.id))
    members = result.scalars().all()
    assert len(members) == 2


@pytest.mark.anyio
async def test_join_team_rejects_duplicate(db_session: AsyncSession, hackathon_and_user):
    """join_team_by_code must reject already-member users."""
    hackathon, user = hackathon_and_user
    service = TeamService()
    team = await service.create_team(db_session, hackathon.id, "Team Gamma", user.id)

    with pytest.raises(ValueError, match="Already a member"):
        await service.join_team_by_code(db_session, team.join_code, user.id)


@pytest.mark.anyio
async def test_update_team(db_session: AsyncSession, hackathon_and_user):
    """update_team must change name when called by captain."""
    hackathon, user = hackathon_and_user
    service = TeamService()
    team = await service.create_team(db_session, hackathon.id, "Old Name", user.id)

    updated = await service.update_team(db_session, team.id, user.id, name="New Name")
    assert updated.name == "New Name"


@pytest.mark.anyio
async def test_remove_member(db_session: AsyncSession, hackathon_and_user):
    """remove_member must delete a team member (captain only)."""
    hackathon, user = hackathon_and_user
    service = TeamService()
    team = await service.create_team(db_session, hackathon.id, "Team Delta", user.id)

    uid2 = uuid.uuid4().hex[:8]
    user2 = User(id=f"user-{uid2}", email=f"{uid2}@example.com", name="User Two", role=UserRole.participant)
    db_session.add(user2)
    reg2 = Registration(
        hackathon_id=hackathon.id,
        user_id=user2.id,
        status=RegistrationStatus.accepted,
    )
    db_session.add(reg2)
    await db_session.commit()

    await service.join_team_by_code(db_session, team.join_code, user2.id)

    await service.remove_member(db_session, team.id, user.id, user2.id)

    result = await db_session.execute(select(TeamMember).where(TeamMember.team_id == team.id))
    members = result.scalars().all()
    assert len(members) == 1
    assert members[0].user_id == user.id
