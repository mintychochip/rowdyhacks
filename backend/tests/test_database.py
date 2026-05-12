"""Tests for database session management and RLS context."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import (
    async_session,
    engine,
    get_current_user_id,
    get_db,
    set_current_user_id,
)


class TestCurrentUserContext:
    def test_set_and_get_user_id(self):
        set_current_user_id("user-123")
        assert get_current_user_id() == "user-123"

    def test_default_is_none(self):
        # Ensure a clean context
        set_current_user_id(None)
        assert get_current_user_id() is None

    def test_clear_by_setting_none(self):
        set_current_user_id("user-123")
        set_current_user_id(None)
        assert get_current_user_id() is None


@pytest.mark.asyncio
async def test_get_db_yields_session():
    """get_db should yield the session produced by async_session."""
    mock_session = MagicMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    mock_session.close = AsyncMock()

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("app.database.async_session", return_value=mock_cm):
        sessions = []
        async for session in get_db():
            sessions.append(session)
        assert len(sessions) == 1
        assert sessions[0] is mock_session
        mock_session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_db_sets_rls_with_user():
    """When a user ID is present in the context, SET LOCAL should include it."""
    set_current_user_id("rls-user")
    mock_session = MagicMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    mock_session.close = AsyncMock()

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("app.database.async_session", return_value=mock_cm):
        async for _ in get_db():
            pass

    calls = mock_session.execute.call_args_list
    assert any("rls-user" in str(c.args[0]) for c in calls if c.args)


@pytest.mark.asyncio
async def test_get_db_sets_rls_empty_when_no_user():
    """When no user ID is in the context, SET LOCAL should use an empty string."""
    set_current_user_id(None)
    mock_session = MagicMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    mock_session.close = AsyncMock()

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("app.database.async_session", return_value=mock_cm):
        async for _ in get_db():
            pass

    calls = mock_session.execute.call_args_list
    assert any("''" in str(c.args[0]) for c in calls if c.args)


@pytest.mark.asyncio
async def test_get_db_clears_rls_in_finally():
    """After yielding, the finally block should clear the RLS context."""
    set_current_user_id("rls-user")
    mock_session = MagicMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    mock_session.close = AsyncMock()

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("app.database.async_session", return_value=mock_cm):
        async for _ in get_db():
            pass

    calls = mock_session.execute.call_args_list
    # The final execute should clear the RLS user ID
    last_call = calls[-1]
    assert "''" in str(last_call.args[0])
    mock_session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_db_handles_close_exception():
    """Exceptions during session context teardown should propagate cleanly."""
    set_current_user_id("rls-user")
    mock_session = MagicMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    mock_session.close = AsyncMock()

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(side_effect=Exception("boom"))

    with patch("app.database.async_session", return_value=mock_cm):
        with pytest.raises(Exception, match="boom"):
            async for _ in get_db():
                pass


def test_engine_exists():
    assert engine is not None


def test_async_session_exists():
    assert async_session is not None
