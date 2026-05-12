"""Tests for BackupService."""

import json
import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Hackathon,
    Prize,
    Registration,
    RegistrationStatus,
    Sponsor,
    Team,
    TeamMember,
    Track,
    User,
    UserRole,
    Workshop,
)
from app.services.backup_service import (
    BackupService,
    _parse_dt,
    _serialize,
)


@pytest_asyncio.fixture
async def hackathon_with_data(db_session: AsyncSession):
    """Create a hackathon with tracks, teams, workshops, sponsors, prizes, and registrations."""
    uid = uuid.uuid4().hex[:8]
    organizer = User(
        id=f"org-{uid}",
        email=f"org-{uid}@example.com",
        name="Organizer",
        role=UserRole.organizer,
    )
    db_session.add(organizer)
    await db_session.commit()

    hackathon = Hackathon(
        name=f"Test Hack {uid}",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        organizer_id=organizer.id,
        max_participants=100,
        waitlist_enabled=True,
        description="A test hackathon",
        schedule={"day1": "kickoff"},
        venue_address="123 Main St",
        parking_info="Lot A",
        wifi_ssid="HackWiFi",
        wifi_password="secret",
        discord_invite_url="https://discord.gg/test",
        devpost_url="https://devpost.com/test",
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)

    track = Track(
        hackathon_id=hackathon.id,
        name="AI Track",
        description="Build something with AI",
        challenge="Use LLMs",
        icon="robot",
        color="#2563eb",
        prize="$500",
        track_type="prize",
        criteria=["innovation", "technical"],
        resources=["https://docs.example.com"],
        resources_markdown="# Resources",
    )
    db_session.add(track)

    team = Team(
        hackathon_id=hackathon.id,
        name="Team Alpha",
        join_code=f"JOIN{uuid.uuid4().hex[:8].upper()}",
        captain_id=organizer.id,
    )
    db_session.add(team)
    await db_session.commit()
    await db_session.refresh(team)

    member = TeamMember(team_id=team.id, user_id=organizer.id)
    db_session.add(member)

    workshop = Workshop(
        hackathon_id=hackathon.id,
        title="Intro to ML",
        description="Basics of machine learning",
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC),
        location="Room 101",
        speaker_name="Dr. Smith",
    )
    db_session.add(workshop)

    sponsor = Sponsor(
        hackathon_id=hackathon.id,
        name="TechCorp",
        tier="gold",
        logo_url="https://example.com/logo.png",
        website_url="https://example.com",
        description="We build things",
    )
    db_session.add(sponsor)

    prize = Prize(
        hackathon_id=hackathon.id,
        name="Best AI Project",
        description="Top project using AI",
        amount="500",
        currency="USD",
        track_id=None,
    )
    db_session.add(prize)

    registration = Registration(
        hackathon_id=hackathon.id,
        user_id=organizer.id,
        status=RegistrationStatus.accepted,
    )
    db_session.add(registration)

    await db_session.commit()
    return hackathon, organizer


@pytest.mark.anyio
async def test_export_hackathon_returns_expected_structure(db_session: AsyncSession, hackathon_with_data):
    """export_hackathon must return a dict with all expected top-level keys."""
    hackathon, _ = hackathon_with_data
    service = BackupService()
    data = await service.export_hackathon(db_session, hackathon.id)

    assert "hackathon" in data
    assert "tracks" in data
    assert "teams" in data
    assert "workshops" in data
    assert "sponsors" in data
    assert "prizes" in data
    assert "registrations" in data

    assert data["hackathon"]["name"] == hackathon.name
    assert len(data["tracks"]) == 1
    assert len(data["teams"]) == 1
    assert len(data["workshops"]) == 1
    assert len(data["sponsors"]) == 1
    assert len(data["prizes"]) == 1
    assert len(data["registrations"]) == 1


@pytest.mark.anyio
async def test_export_hackathon_not_found(db_session: AsyncSession):
    """export_hackathon must raise ValueError when hackathon does not exist."""
    service = BackupService()
    with pytest.raises(ValueError, match="Hackathon not found"):
        await service.export_hackathon(db_session, uuid.uuid4())


@pytest.mark.anyio
async def test_restore_hackathon_creates_records(db_session: AsyncSession, hackathon_with_data):
    """restore_hackathon must create a new hackathon and related records from exported data."""
    hackathon, organizer = hackathon_with_data
    service = BackupService()
    exported = await service.export_hackathon(db_session, hackathon.id)

    restored = await service.restore_hackathon(db_session, organizer.id, exported)
    await db_session.refresh(restored)

    assert restored.name == hackathon.name
    assert restored.organizer_id == organizer.id
    assert restored.id != hackathon.id


@pytest.mark.anyio
async def test_restore_hackathon_defaults(db_session: AsyncSession):
    """restore_hackathon must use sensible defaults when optional fields are missing."""
    service = BackupService()
    now = datetime.now(UTC)
    data = {
        "hackathon": {
            "start_date": now.isoformat(),
            "end_date": now.isoformat(),
        }
    }
    restored = await service.restore_hackathon(db_session, "test-org", data)
    assert restored.name == "Restored Hackathon"
    assert restored.waitlist_enabled is False


@pytest.mark.anyio
async def test_serialize_handles_uuid_datetime_enum():
    """_serialize must encode UUID, datetime, and RegistrationStatus correctly."""
    payload = {
        "id": uuid.uuid4(),
        "created": datetime.now(UTC),
        "status": RegistrationStatus.accepted,
    }
    raw = _serialize(payload)
    parsed = json.loads(raw)
    assert isinstance(parsed["id"], str)
    assert isinstance(parsed["created"], str)
    assert parsed["status"] == "accepted"


@pytest.mark.anyio
async def test_parse_dt_variants():
    """_parse_dt must handle None, datetime objects, and ISO strings."""
    now = datetime.now(UTC)
    assert _parse_dt(None) is None
    assert _parse_dt(now) == now
    iso_str = now.isoformat().replace("+00:00", "Z")
    parsed = _parse_dt(iso_str)
    assert isinstance(parsed, datetime)


@pytest.mark.anyio
async def test_parse_dt_invalid():
    """_parse_dt must raise ValueError for invalid datetime strings."""
    with pytest.raises(ValueError):
        _parse_dt("not-a-datetime")
