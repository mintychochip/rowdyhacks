"""Tests for QR code generation route."""

from unittest.mock import patch

import pytest


@pytest.mark.anyio
async def test_get_qr_image(client):
    with patch("app.routes.qr.generate_qr_png", return_value=b"\x89PNG\r\n\x1a\n") as mock_generate:
        resp = await client.get("/api/qr?data=https://example.com")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"
        assert resp.content == b"\x89PNG\r\n\x1a\n"
        mock_generate.assert_called_once_with("https://example.com")


@pytest.mark.anyio
async def test_get_qr_image_missing_param(client):
    resp = await client.get("/api/qr")
    assert resp.status_code == 422
