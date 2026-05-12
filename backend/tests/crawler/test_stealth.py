"""Tests for stealth crawling utilities."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.crawler.stealth import (
    USER_AGENTS,
    get_stealth_headers,
    human_like_delay,
    randomize_fingerprint,
    ProxyRotator,
    StealthClient,
)


@pytest.mark.anyio
async def test_get_stealth_headers_structure():
    """get_stealth_headers must return a dict with required browser-like keys."""
    headers = get_stealth_headers()
    assert "User-Agent" in headers
    assert "Accept" in headers
    assert "Accept-Language" in headers
    assert "Accept-Encoding" in headers
    assert "DNT" in headers
    assert "Connection" in headers
    assert "Upgrade-Insecure-Requests" in headers
    assert "Sec-Fetch-Dest" in headers
    assert "Sec-Fetch-Mode" in headers
    assert "Sec-Fetch-Site" in headers
    assert "Cache-Control" in headers
    assert "Referer" in headers
    assert headers["User-Agent"] in USER_AGENTS


@pytest.mark.anyio
async def test_get_stealth_headers_json_content_type():
    """get_stealth_headers with json content_type must use json Accept header."""
    headers = get_stealth_headers(content_type="json")
    assert "application/json" in headers["Accept"]


@pytest.mark.anyio
async def test_get_stealth_headers_custom_referer():
    """get_stealth_headers must use the provided referer when given."""
    headers = get_stealth_headers(referer="https://example.com/")
    assert headers["Referer"] == "https://example.com/"
    assert headers["Sec-Fetch-Site"] == "cross-site"


@pytest.mark.anyio
async def test_get_stealth_headers_random_viewport():
    """get_stealth_headers may include a Viewport-Width header."""
    found = False
    for _ in range(20):
        headers = get_stealth_headers()
        if "Viewport-Width" in headers:
            found = True
            assert headers["Viewport-Width"] in ["1280", "1366", "1440", "1920", "2560"]
            break
    assert found


@pytest.mark.anyio
async def test_proxy_rotator_empty():
    """ProxyRotator must return None when no proxies are configured."""
    rotator = ProxyRotator()
    assert rotator.get_next_proxy() is None


@pytest.mark.anyio
async def test_proxy_rotator_round_robin():
    """ProxyRotator must cycle through proxies in round-robin order."""
    rotator = ProxyRotator(["http://proxy1", "http://proxy2", "http://proxy3"])
    assert rotator.get_next_proxy() == "http://proxy1"
    assert rotator.get_next_proxy() == "http://proxy2"
    assert rotator.get_next_proxy() == "http://proxy3"
    assert rotator.get_next_proxy() == "http://proxy1"


@pytest.mark.asyncio
async def test_human_like_delay():
    """human_like_delay must sleep for a duration within the expected range."""
    slept = []
    with patch("asyncio.sleep", side_effect=lambda x: slept.append(x)):
        await human_like_delay(min_seconds=0.5, max_seconds=2.0, action="unknown_action")
    assert len(slept) == 1
    assert 0.5 <= slept[0] <= 2.0


@pytest.mark.asyncio
async def test_human_like_delay_action_lookup():
    """human_like_delay must resolve known actions to their delay ranges."""
    slept = []
    with patch("asyncio.sleep", side_effect=lambda x: slept.append(x)):
        await human_like_delay(action="click")
    assert len(slept) == 1
    assert 0.2 <= slept[0] <= 0.8


@pytest.mark.anyio
async def test_randomize_fingerprint():
    """randomize_fingerprint must return a dict with expected viewport and display fields."""
    fp = randomize_fingerprint()
    assert "viewport" in fp
    assert "width" in fp["viewport"]
    assert "height" in fp["viewport"]
    assert "color_depth" in fp
    assert "pixel_ratio" in fp
    assert "timezone_offset" in fp
    assert fp["viewport"]["width"] in [1280, 1366, 1440, 1536, 1920]
    assert fp["viewport"]["height"] in [720, 768, 900, 1080, 1200]


@pytest.mark.asyncio
async def test_stealth_client_context_manager():
    """StealthClient must open and close the underlying httpx client via async context manager."""
    client = StealthClient()
    mock_async_client = AsyncMock()
    mock_async_client.aclose = AsyncMock()
    with patch("httpx.AsyncClient", return_value=mock_async_client):
        async with client:
            assert client._client is mock_async_client
    mock_async_client.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_stealth_client_get_success():
    """StealthClient.get must return the response on a successful request."""
    client = StealthClient()
    response = MagicMock()
    response.status_code = 200
    response.raise_for_status = MagicMock()
    mock_async_client = AsyncMock()
    mock_async_client.get = AsyncMock(return_value=response)
    with patch("httpx.AsyncClient", return_value=mock_async_client):
        async with client:
            resp = await client.get("https://example.com")
    assert resp == response
    assert client._request_count == 1


@pytest.mark.asyncio
async def test_stealth_client_get_retry_on_500():
    """StealthClient.get must retry on 500-level errors."""
    client = StealthClient(max_retries=3)

    def _raise_on_500():
        raise httpx.HTTPStatusError(
            "500",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )

    bad_response = MagicMock()
    bad_response.status_code = 500
    bad_response.raise_for_status = MagicMock(side_effect=_raise_on_500)

    good_response = MagicMock()
    good_response.status_code = 200
    good_response.raise_for_status = MagicMock()

    mock_async_client = AsyncMock()
    mock_async_client.get = AsyncMock(side_effect=[bad_response, good_response])
    with patch("httpx.AsyncClient", return_value=mock_async_client):
        async with client:
            resp = await client.get("https://example.com")
    assert resp == good_response
    assert mock_async_client.get.call_count == 2


@pytest.mark.asyncio
async def test_stealth_client_post():
    """StealthClient.post must send a POST request with JSON headers."""
    client = StealthClient()
    response = MagicMock()
    mock_async_client = AsyncMock()
    mock_async_client.post = AsyncMock(return_value=response)
    with patch("httpx.AsyncClient", return_value=mock_async_client):
        async with client:
            resp = await client.post("https://example.com", data={"key": "value"})
    assert resp == response
    call_kwargs = mock_async_client.post.call_args.kwargs
    assert "headers" in call_kwargs
    assert "application/json" in call_kwargs["headers"]["Accept"]
