"""Tests for Discord bot module."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.discord_bot import (
    ApplicationView,
    bot,
    get_bot_invite_url,
    post_application_to_discord,
    start_bot,
)


@pytest.fixture(autouse=True)
def reset_bot_state():
    """Reset bot state between tests."""
    bot._connection._ready = False
    yield
    bot._connection._ready = False


class TestGetBotInviteUrl:
    def test_returns_none_when_no_client_id(self):
        with patch("app.discord_bot.settings.discord_client_id", ""):
            assert get_bot_invite_url() is None

    def test_returns_url_when_configured(self):
        with patch("app.discord_bot.settings.discord_client_id", "12345"):
            url = get_bot_invite_url()
            assert url is not None
            assert "https://discord.com/api/oauth2/authorize" in url
            assert "client_id=12345" in url
            assert "bot" in url


@pytest.mark.asyncio
class TestStartBot:
    async def test_skips_when_no_token(self):
        with patch("app.discord_bot.settings.discord_bot_token", ""):
            result = await start_bot()
            assert result is None

    async def test_starts_bot(self):
        with (
            patch("app.discord_bot.settings.discord_bot_token", "fake-token"),
            patch("app.discord_bot.settings.discord_client_id", "12345"),
            patch("app.discord_bot.bot.start", new_callable=AsyncMock) as mock_start,
            patch("app.discord_bot.bot.wait_until_ready", new_callable=AsyncMock) as mock_ready,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            result = await start_bot()
            mock_start.assert_called_once_with("fake-token")
            mock_ready.assert_awaited_once()
            assert result is bot

    async def test_handles_timeout(self):
        with (
            patch("app.discord_bot.settings.discord_bot_token", "fake-token"),
            patch("app.discord_bot.bot.start", new_callable=AsyncMock),
            patch("app.discord_bot.bot.wait_until_ready", new_callable=AsyncMock, side_effect=TimeoutError),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            result = await start_bot()
            assert result is bot


@pytest.mark.asyncio
class TestApplicationView:
    async def test_review_callback_not_found(self):
        view = ApplicationView(str(uuid4()), str(uuid4()))
        interaction = MagicMock()
        interaction.response.send_message = AsyncMock()

        with patch("app.discord_bot.async_session") as mock_session:
            db = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=db)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

            result_mock = MagicMock()
            result_mock.scalar_one_or_none.return_value = None
            db.execute.return_value = result_mock

            await view._review_callback(interaction)
            interaction.response.send_message.assert_awaited_once_with("Registration not found.", ephemeral=True)

    async def test_accept_callback(self):
        from app.models import Registration, RegistrationStatus, User

        view = ApplicationView(str(uuid4()), str(uuid4()))
        interaction = MagicMock()
        interaction.response.send_message = AsyncMock()
        interaction.message.edit = AsyncMock()
        interaction.message.embeds = [MagicMock()]

        user = MagicMock(spec=User)
        user.name = "Alice"

        reg = MagicMock(spec=Registration)
        reg.status = RegistrationStatus.pending
        reg.user = user
        reg.id = uuid4()
        reg.user_id = uuid4()

        hack = MagicMock()
        hack.id = uuid4()
        hack.end_date = datetime.now(UTC)

        with (
            patch("app.discord_bot.async_session") as mock_session,
            patch("app.discord_bot.select") as mock_select,
            patch("app.discord_bot.Hackathon") as mock_hack_cls,
            patch("app.auth.create_qr_token", return_value="qr-token"),
        ):
            db = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=db)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

            reg_result = MagicMock()
            reg_result.scalar_one_or_none.return_value = reg
            hack_result = MagicMock()
            hack_result.scalar_one.return_value = hack
            db.execute.side_effect = [reg_result, hack_result]

            await view._accept_callback(interaction)
            assert reg.status == RegistrationStatus.accepted
            interaction.message.edit.assert_awaited_once()

    async def test_reject_callback(self):
        from app.models import Registration, RegistrationStatus, User

        view = ApplicationView(str(uuid4()), str(uuid4()))
        interaction = MagicMock()
        interaction.response.send_message = AsyncMock()
        interaction.message.edit = AsyncMock()
        interaction.message.embeds = [MagicMock()]

        user = MagicMock(spec=User)
        user.name = "Alice"

        reg = MagicMock(spec=Registration)
        reg.status = RegistrationStatus.pending
        reg.user = user

        with patch("app.discord_bot.async_session") as mock_session, patch("app.discord_bot.select") as mock_select:
            db = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=db)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

            result_mock = MagicMock()
            result_mock.scalar_one_or_none.return_value = reg
            db.execute.return_value = result_mock

            await view._reject_callback(interaction)
            assert reg.status == RegistrationStatus.rejected
            interaction.message.edit.assert_awaited_once()


@pytest.mark.asyncio
class TestHackathonBot:
    async def test_setup_hook_syncs_commands(self):
        with patch.object(bot.tree, "sync", new_callable=AsyncMock) as mock_sync:
            await bot.setup_hook()
            mock_sync.assert_awaited_once()


@pytest.mark.asyncio
class TestPostApplicationToDiscord:
    async def test_returns_false_when_no_token(self):
        with patch("app.discord_bot.settings.discord_bot_token", ""):
            result = await post_application_to_discord(str(uuid4()))
            assert result is False

    async def test_returns_false_when_no_registration(self):
        with patch("app.discord_bot.settings.discord_bot_token", "token"):
            with patch("app.discord_bot.async_session") as mock_session, patch("app.discord_bot.select") as mock_select:
                db = AsyncMock()
                mock_session.return_value.__aenter__ = AsyncMock(return_value=db)
                mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

                result_mock = MagicMock()
                result_mock.scalar_one_or_none.return_value = None
                db.execute.return_value = result_mock

                result = await post_application_to_discord(str(uuid4()))
                assert result is False
