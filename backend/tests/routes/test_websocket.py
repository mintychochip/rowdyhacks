"""Tests for WebSocket routes."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import WebSocketDisconnect

from app.routes.websocket import hackathon_websocket, submission_websocket, user_websocket


@pytest.fixture
def mock_websocket():
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.send_text = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.mark.asyncio
class TestHackathonWebsocket:
    async def test_connect_and_ping_pong(self, mock_websocket):
        mock_websocket.receive_text.side_effect = ["ping", WebSocketDisconnect()]

        with patch("app.routes.websocket.manager") as mock_manager:
            mock_manager.connect = AsyncMock()
            mock_manager.disconnect = AsyncMock()
            await hackathon_websocket(mock_websocket, "hack-1")

            mock_manager.connect.assert_awaited_once_with(mock_websocket, "hackathon:hack-1")
            mock_websocket.send_text.assert_awaited_once_with("pong")
            mock_manager.disconnect.assert_awaited_once_with(mock_websocket)

    async def test_disconnect_handled(self, mock_websocket):
        mock_websocket.receive_text.side_effect = WebSocketDisconnect()

        with patch("app.routes.websocket.manager") as mock_manager:
            mock_manager.connect = AsyncMock()
            mock_manager.disconnect = AsyncMock()
            await hackathon_websocket(mock_websocket, "hack-1")
            mock_manager.disconnect.assert_awaited_once_with(mock_websocket)


@pytest.mark.asyncio
class TestSubmissionWebsocket:
    async def test_connect_and_ping_pong(self, mock_websocket):
        mock_websocket.receive_text.side_effect = ["ping", WebSocketDisconnect()]

        with patch("app.routes.websocket.manager") as mock_manager:
            mock_manager.connect = AsyncMock()
            mock_manager.disconnect = AsyncMock()
            await submission_websocket(mock_websocket, "sub-1")

            mock_manager.connect.assert_awaited_once_with(mock_websocket, "submission:sub-1")
            mock_websocket.send_text.assert_awaited_once_with("pong")


@pytest.mark.asyncio
class TestUserWebsocket:
    async def test_authorized_user(self, mock_websocket):
        mock_websocket.receive_text.side_effect = ["ping", WebSocketDisconnect()]
        current_user = {"id": "user-1"}

        with patch("app.routes.websocket.manager") as mock_manager:
            mock_manager.connect = AsyncMock()
            mock_manager.disconnect = AsyncMock()
            await user_websocket(mock_websocket, "user-1", current_user)

            mock_manager.connect.assert_awaited_once_with(mock_websocket, "user:user-1")
            mock_websocket.send_text.assert_awaited_once_with("pong")

    async def test_unauthorized_user(self, mock_websocket):
        current_user = {"id": "user-2"}

        with patch("app.routes.websocket.manager") as mock_manager:
            mock_manager.connect = AsyncMock()
            await user_websocket(mock_websocket, "user-1", current_user)

            mock_websocket.close.assert_awaited_once_with(code=403)
            mock_manager.connect.assert_not_called()

    async def test_no_current_user(self, mock_websocket):
        with patch("app.routes.websocket.manager") as mock_manager:
            mock_manager.connect = AsyncMock()
            await user_websocket(mock_websocket, "user-1", None)

            mock_websocket.close.assert_awaited_once_with(code=403)
            mock_manager.connect.assert_not_called()
