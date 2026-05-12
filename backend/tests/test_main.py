"""Tests for FastAPI app factory and lifespan."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.main import _seed_demo_data, app, lifespan


@pytest.fixture
def test_app():
    """Return the global app instance for route tests."""
    return app


@pytest.mark.asyncio
class TestLifespan:
    async def test_lifespan_starts_and_shuts_down(self):
        with (
            patch("app.main._seed_demo_data", new_callable=AsyncMock),
            patch("app.seed_content.seed_default_content", new_callable=AsyncMock),
            patch("app.services.config_service.ConfigService") as mock_cfg_cls,
            patch("app.assistant.indexer.initialize_vector_store", new_callable=AsyncMock),
            patch("app.main.start_bot", new_callable=AsyncMock),
            patch("app.main.start_scheduler") as mock_start_scheduler,
            patch("app.discord_bot.bot") as mock_bot,
            patch("app.main.shutdown_scheduler") as mock_shutdown_scheduler,
            patch("app.cache.close_redis", new_callable=AsyncMock),
            patch("app.database.async_session") as mock_session,
        ):
            mock_cfg = MagicMock()
            mock_cfg._seed_defaults = AsyncMock()
            mock_cfg_cls.return_value = mock_cfg

            mock_db = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_bot.is_ready.return_value = True
            mock_bot.close = AsyncMock()

            ctx = lifespan(FastAPI())
            await ctx.__aenter__()
            mock_start_scheduler.assert_called_once()
            await ctx.__aexit__(None, None, None)
            mock_shutdown_scheduler.assert_called_once()

    async def test_seed_demo_data(self):
        with (
            patch("app.database.async_session") as mock_session,
            patch("sqlalchemy.select") as mock_select,
            patch("app.models.User") as mock_user_cls,
            patch("app.models.UserRole") as mock_role_cls,
        ):
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

            result_mock = MagicMock()
            result_mock.scalar_one_or_none.return_value = None
            mock_db.execute.return_value = result_mock

            await _seed_demo_data()
            assert mock_db.add.call_count == 4
            mock_db.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_health_check():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


@pytest.mark.anyio
async def test_discord_invite_url_unconfigured():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        with patch("app.main.settings.discord_client_id", ""):
            resp = await ac.get("/api/discord/invite-url")
            assert resp.status_code == 200
            assert "error" in resp.json()


@pytest.mark.anyio
async def test_discord_bot_status():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        with patch("app.discord_bot.bot") as mock_bot:
            mock_bot.is_ready.return_value = False
            mock_bot.user = None
            mock_bot.guilds = []
            resp = await ac.get("/api/discord/bot-status")
            assert resp.status_code == 200
            data = resp.json()
            assert data["ready"] is False
            assert data["guild_count"] == 0


class TestRouterRegistration:
    def test_app_is_fastapi_instance(self):
        assert isinstance(app, FastAPI)

    def test_routers_registered(self):
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert any("/api/auth" in r for r in routes)
        assert any("/api/assistant" in r for r in routes)
        assert any("/api/health" in r for r in routes)
