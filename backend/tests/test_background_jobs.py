"""Tests for background job scheduler and job handlers."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.ext.asyncio import AsyncSession

from app.background_jobs import (
    cleanup_expired_offers,
    scheduler,
    send_event_reminders,
    shutdown_scheduler,
    start_scheduler,
)
from app.models import UserRole


class TestSchedulerLifecycle:
    def test_start_scheduler_adds_jobs_and_starts(self):
        with (
            patch.object(scheduler, "add_job") as mock_add_job,
            patch.object(scheduler, "start") as mock_start,
        ):
            start_scheduler()
            assert mock_add_job.call_count == 2
            calls = mock_add_job.call_args_list

            assert calls[0].kwargs["id"] == "cleanup_expired_offers"
            assert isinstance(calls[0].args[1], IntervalTrigger)
            assert calls[0].kwargs["replace_existing"] is True

            assert calls[1].kwargs["id"] == "send_event_reminders"
            assert isinstance(calls[1].args[1], CronTrigger)
            assert calls[1].kwargs["replace_existing"] is True

            mock_start.assert_called_once()

    def test_shutdown_scheduler(self):
        with patch.object(scheduler, "shutdown") as mock_shutdown:
            shutdown_scheduler()
            mock_shutdown.assert_called_once()


@pytest.mark.asyncio
async def test_cleanup_expired_offers_no_expired():
    """When there are no expired offers, commit should not be called."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []

    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()
    mock_session.flush = AsyncMock()

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("app.background_jobs.async_session", return_value=mock_cm):
        await cleanup_expired_offers()

    # commit is always called at the end of the async session block
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_cleanup_expired_offers_processes_expired():
    """Expired offers are reverted to waitlisted and the next applicant is promoted."""
    from app.models import Registration, RegistrationStatus

    now = datetime.now(UTC)
    reg = MagicMock(spec=Registration)
    reg.hackathon_id = "hack-1"
    reg.status = RegistrationStatus.offered
    reg.offer_expires_at = now - timedelta(hours=1)
    reg.declined_count = 0

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [reg]

    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()
    mock_session.flush = AsyncMock()

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.background_jobs.async_session", return_value=mock_cm),
        patch(
            "app.background_jobs.promote_from_waitlist",
            new=AsyncMock(return_value=reg),
        ) as mock_promote,
    ):
        await cleanup_expired_offers()

    assert reg.status == RegistrationStatus.waitlisted
    assert reg.offer_expires_at is None
    assert reg.declined_count == 1
    mock_session.commit.assert_called_once()
    mock_promote.assert_awaited_once_with("hack-1", mock_session)


@pytest.mark.asyncio
async def test_send_event_reminders(db_session: AsyncSession):
    """Reminders are sent for hackathons starting tomorrow to accepted participants."""
    from app.models import Hackathon, Registration, RegistrationStatus, User
    from sqlalchemy import delete

    # Clean slate
    await db_session.execute(delete(Registration))
    await db_session.execute(delete(Hackathon))
    await db_session.execute(delete(User))
    await db_session.commit()

    now = datetime.now(UTC)
    tomorrow = now + timedelta(days=1)

    user = User(id="remind-user", email="user@example.com", name="User One", role=UserRole.participant)
    db_session.add(user)

    hackathon = Hackathon(
        id=uuid.uuid4(),
        name="TestHack",
        start_date=tomorrow,
        end_date=tomorrow + timedelta(days=1),
        organizer_id="remind-user",
    )
    db_session.add(hackathon)
    await db_session.commit()
    await db_session.refresh(hackathon)

    reg = Registration(
        id=uuid.uuid4(),
        hackathon_id=hackathon.id,
        user_id=user.id,
        status=RegistrationStatus.accepted,
    )
    db_session.add(reg)
    await db_session.commit()

    # Patch async_session so send_event_reminders uses the test db_session
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=db_session)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.background_jobs.async_session", return_value=mock_cm),
        patch("app.background_jobs.send_email_with_retry", new=AsyncMock()) as mock_send,
    ):
        await send_event_reminders()

    mock_send.assert_called_once()
    call_kwargs = mock_send.call_args.kwargs
    assert call_kwargs["to_email"] == "user@example.com"
    assert call_kwargs["email_type"] == "event_reminder"
    assert call_kwargs["context"]["hackathon_name"] == "TestHack"
