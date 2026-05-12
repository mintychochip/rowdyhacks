"""Tests for PrizeService."""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Hackathon, PrizeAward, Track, User, UserRole
from app.services.prize_service import PrizeService


@pytest_asyncio.fixture
async def hackathon_and_track(db_session: AsyncSession):
    from datetime import UTC, datetime

    uid = uuid.uuid4().hex[:8]
    user = User(id=f"org-{uid}", email=f"{uid}@example.com", name="Org", role=UserRole.organizer)
    db_session.add(user)

    hackathon = Hackathon(
        name="Prize Hack",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id=user.id,
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)

    track = Track(hackathon_id=hackathon.id, name="AI Track")
    db_session.add(track)
    await db_session.commit()
    await db_session.refresh(track)

    return hackathon, track


@pytest.mark.anyio
async def test_create_prize(db_session: AsyncSession, hackathon_and_track):
    hackathon, track = hackathon_and_track
    service = PrizeService()
    p = await service.create_prize(
        db_session,
        hackathon_id=hackathon.id,
        name="Best AI",
        description="Top AI project",
        amount="$1,000",
        track_id=track.id,
    )
    assert p.name == "Best AI"
    assert p.amount == "$1,000"
    assert p.track_id == track.id


@pytest.mark.anyio
async def test_list_prizes(db_session: AsyncSession, hackathon_and_track):
    hackathon, _ = hackathon_and_track
    service = PrizeService()
    await service.create_prize(db_session, hackathon.id, "Prize B")
    await service.create_prize(db_session, hackathon.id, "Prize A")
    prizes = await service.list_prizes(db_session, hackathon.id)
    names = [p.name for p in prizes]
    assert names == ["Prize A", "Prize B"]


@pytest.mark.anyio
async def test_get_prize(db_session: AsyncSession, hackathon_and_track):
    hackathon, _ = hackathon_and_track
    service = PrizeService()
    p = await service.create_prize(db_session, hackathon.id, "Get Me")
    found = await service.get_prize(db_session, p.id)
    assert found is not None
    assert found.name == "Get Me"


@pytest.mark.anyio
async def test_update_prize(db_session: AsyncSession, hackathon_and_track):
    hackathon, _ = hackathon_and_track
    service = PrizeService()
    p = await service.create_prize(db_session, hackathon.id, "Old")
    updated = await service.update_prize(db_session, p.id, name="New", amount="$500")
    assert updated.name == "New"
    assert updated.amount == "$500"


@pytest.mark.anyio
async def test_delete_prize(db_session: AsyncSession, hackathon_and_track):
    hackathon, _ = hackathon_and_track
    service = PrizeService()
    p = await service.create_prize(db_session, hackathon.id, "Delete Me")
    await service.delete_prize(db_session, p.id)
    found = await service.get_prize(db_session, p.id)
    assert found is None


@pytest.mark.anyio
async def test_award_prize(db_session: AsyncSession, hackathon_and_track):
    from app.models import Team

    hackathon, _ = hackathon_and_track
    service = PrizeService()
    prize = await service.create_prize(db_session, hackathon.id, "Best AI")

    team = Team(hackathon_id=hackathon.id, name="Team Alpha", join_code=uuid.uuid4().hex[:8], captain_id="user-1")
    db_session.add(team)
    await db_session.commit()
    await db_session.refresh(team)

    award = await service.award_prize(db_session, prize.id, team.id, hackathon.id, "org-1")
    assert award.prize_id == prize.id
    assert award.team_id == team.id
    assert award.awarded_by == "org-1"


@pytest.mark.anyio
async def test_award_prize_already_awarded(db_session: AsyncSession, hackathon_and_track):
    from app.models import Team

    hackathon, _ = hackathon_and_track
    service = PrizeService()
    prize = await service.create_prize(db_session, hackathon.id, "Best AI")

    team = Team(hackathon_id=hackathon.id, name="Team Alpha", join_code=uuid.uuid4().hex[:8], captain_id="user-1")
    db_session.add(team)
    await db_session.commit()
    await db_session.refresh(team)

    await service.award_prize(db_session, prize.id, team.id, hackathon.id, "org-1")
    with pytest.raises(ValueError, match="already awarded"):
        await service.award_prize(db_session, prize.id, team.id, hackathon.id, "org-1")


@pytest.mark.anyio
async def test_revoke_award(db_session: AsyncSession, hackathon_and_track):
    from app.models import Team

    hackathon, _ = hackathon_and_track
    service = PrizeService()
    prize = await service.create_prize(db_session, hackathon.id, "Best AI")

    team = Team(hackathon_id=hackathon.id, name="Team Alpha", join_code=uuid.uuid4().hex[:8], captain_id="user-1")
    db_session.add(team)
    await db_session.commit()
    await db_session.refresh(team)

    await service.award_prize(db_session, prize.id, team.id, hackathon.id, "org-1")
    await service.revoke_award(db_session, prize.id)

    result = await db_session.execute(select(PrizeAward).where(PrizeAward.prize_id == prize.id))
    assert result.scalar_one_or_none() is None


@pytest.mark.anyio
async def test_revoke_award_not_found(db_session: AsyncSession, hackathon_and_track):
    hackathon, _ = hackathon_and_track
    service = PrizeService()
    with pytest.raises(ValueError, match="Award not found"):
        await service.revoke_award(db_session, hackathon.id)


@pytest.mark.anyio
async def test_list_awarded_prizes(db_session: AsyncSession, hackathon_and_track):
    from app.models import Team

    hackathon, _ = hackathon_and_track
    service = PrizeService()
    prize = await service.create_prize(db_session, hackathon.id, "Best AI")

    team = Team(hackathon_id=hackathon.id, name="Team Alpha", join_code=uuid.uuid4().hex[:8], captain_id="user-1")
    db_session.add(team)
    await db_session.commit()
    await db_session.refresh(team)

    await service.award_prize(db_session, prize.id, team.id, hackathon.id, "org-1")
    awards = await service.list_awarded_prizes(db_session, hackathon.id)
    assert len(awards) == 1
    assert awards[0].prize_id == prize.id
    assert awards[0].team_id == team.id
