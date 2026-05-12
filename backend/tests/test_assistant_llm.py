"""Tests for assistant LLM client."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.assistant.llm import LLMClient, llm_client


@pytest.fixture
def client():
    return LLMClient()


@pytest.mark.asyncio
class TestChatCompletion:
    @patch("app.assistant.llm.POOLSIDE_API_KEY", "test-key")
    @patch("app.assistant.llm.POOLSIDE_API_URL", "https://api.test")
    async def test_chat_completion_success(self, client):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"choices": [{"message": {"content": "hi"}}]}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await client.chat_completion([{"role": "user", "content": "hello"}])
            assert result == {"choices": [{"message": {"content": "hi"}}]}
            mock_client.post.assert_awaited_once()
            call = mock_client.post.call_args
            assert call.kwargs["json"]["model"] == client.model
            assert call.kwargs["json"]["stream"] is False

    @patch("app.assistant.llm.POOLSIDE_API_KEY", "test-key")
    @patch("app.assistant.llm.POOLSIDE_API_URL", "https://api.test")
    async def test_chat_completion_with_tools(self, client):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"choices": []}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            tools = [{"type": "function", "function": {"name": "test"}}]
            await client.chat_completion([{"role": "user", "content": "hello"}], tools=tools)
            call = mock_client.post.call_args
            assert call.kwargs["json"]["tools"] == tools
            assert call.kwargs["json"]["tool_choice"] == "auto"

    @patch("app.assistant.llm.POOLSIDE_API_KEY", "test-key")
    @patch("app.assistant.llm.POOLSIDE_API_URL", "https://api.test")
    async def test_chat_completion_raises_on_error(self, client):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "400", request=MagicMock(), response=MagicMock()
        )

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            with pytest.raises(httpx.HTTPStatusError):
                await client.chat_completion([{"role": "user", "content": "hello"}])


@pytest.mark.asyncio
class TestChatCompletionStream:
    @patch("app.assistant.llm.POOLSIDE_API_KEY", "test-key")
    @patch("app.assistant.llm.POOLSIDE_API_URL", "https://api.test")
    async def test_stream_yields_content(self, client):
        async def mock_aiter_lines():
            yield 'data: {"choices": [{"delta": {"content": "Hello"}}]}'
            yield "data: [DONE]"

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.aiter_lines = mock_aiter_lines
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_http = AsyncMock()
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_http.stream = MagicMock(return_value=mock_response)
            mock_client_cls.return_value = mock_http

            chunks = []
            async for chunk in client.chat_completion_stream([{"role": "user", "content": "hi"}]):
                chunks.append(chunk)
            assert "Hello" in chunks

    @patch("app.assistant.llm.POOLSIDE_API_KEY", "test-key")
    @patch("app.assistant.llm.POOLSIDE_API_URL", "https://api.test")
    async def test_stream_error_status(self, client):
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.aread = AsyncMock(return_value=b"internal error")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_http = AsyncMock()
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_http.stream = MagicMock(return_value=mock_response)
            mock_client_cls.return_value = mock_http

            chunks = []
            async for chunk in client.chat_completion_stream([{"role": "user", "content": "hi"}]):
                chunks.append(chunk)
            assert len(chunks) == 1
            data = json.loads(chunks[0])
            assert "error" in data


@pytest.mark.asyncio
class TestExecuteToolLoop:
    @patch("app.assistant.llm.POOLSIDE_API_KEY", "test-key")
    @patch("app.assistant.llm.POOLSIDE_API_URL", "https://api.test")
    async def test_tool_loop_executes_tools(self, client):
        call_count = 0

        async def mock_stream(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                yield "Let me check that."
                yield json.dumps({"tool": "get_tracks", "parameters": {}})
            else:
                yield "Done."

        with patch.object(client, "chat_completion_stream", side_effect=mock_stream):
            tool_executor = AsyncMock(return_value=[{"name": "AI Track"}])
            chunks = []
            async for chunk in client.execute_tool_loop(
                system_prompt="sys",
                history=[],
                user_message="What tracks?",
                tools=[{"type": "function", "function": {"name": "get_tracks"}}],
                tool_executor=tool_executor,
            ):
                chunks.append(chunk)

            assert any("Let me check that." in c for c in chunks)
            tool_executor.assert_awaited_with("get_tracks", {})

    @patch("app.assistant.llm.POOLSIDE_API_KEY", "test-key")
    @patch("app.assistant.llm.POOLSIDE_API_URL", "https://api.test")
    async def test_tool_loop_max_iterations(self, client):
        call_count = 0

        async def mock_stream(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 10:
                yield json.dumps({"tool": "get_tracks", "parameters": {}})
            else:
                yield "Done"

        with patch.object(client, "chat_completion_stream", side_effect=mock_stream):
            tool_executor = AsyncMock(return_value=[])
            chunks = []
            async for chunk in client.execute_tool_loop(
                system_prompt="sys",
                history=[],
                user_message="What tracks?",
                tools=[{"type": "function", "function": {"name": "get_tracks"}}],
                tool_executor=tool_executor,
                max_iterations=2,
            ):
                chunks.append(chunk)

            assert tool_executor.await_count == 2

    @patch("app.assistant.llm.POOLSIDE_API_KEY", "test-key")
    @patch("app.assistant.llm.POOLSIDE_API_URL", "https://api.test")
    async def test_tool_loop_no_tools(self, client):
        async def mock_stream(*args, **kwargs):
            yield "No tools needed."

        with patch.object(client, "chat_completion_stream", side_effect=mock_stream):
            tool_executor = AsyncMock()
            chunks = []
            async for chunk in client.execute_tool_loop(
                system_prompt="sys",
                history=[],
                user_message="Hi",
                tools=[],
                tool_executor=tool_executor,
            ):
                chunks.append(chunk)

            tool_executor.assert_not_called()
            assert any("No tools needed." in c for c in chunks)


class TestGlobalInstance:
    def test_llm_client_singleton(self):
        assert isinstance(llm_client, LLMClient)
