from unittest.mock import MagicMock, patch

import pytest

from app.email_service import _send_smtp


@pytest.mark.asyncio
async def test_send_smtp_no_tls_no_auth():
    """Mailpit mode: no STARTTLS, no login when USE_TLS=False and USER=''."""
    with (
        patch("app.email_service.SMTP_HOST", "mail"),
        patch("app.email_service.SMTP_PORT", 1025),
        patch("app.email_service.SMTP_USE_TLS", False),
        patch("app.email_service.SMTP_USER", ""),
        patch("app.email_service.SMTP_PASSWORD", ""),
        patch("app.email_service.EMAIL_FROM", "test@openhack.local"),
        patch("smtplib.SMTP") as MockSMTP,
    ):
        mock_server = MagicMock()
        MockSMTP.return_value.__enter__.return_value = mock_server

        await _send_smtp("recipient@example.com", "Hello", "Body text")

        MockSMTP.assert_called_once_with("mail", 1025)
        mock_server.starttls.assert_not_called()
        mock_server.login.assert_not_called()
        mock_server.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_send_smtp_with_tls_and_auth():
    """Production mode: STARTTLS + login when USE_TLS=True and USER is set."""
    with (
        patch("app.email_service.SMTP_HOST", "smtp.example.com"),
        patch("app.email_service.SMTP_PORT", 587),
        patch("app.email_service.SMTP_USE_TLS", True),
        patch("app.email_service.SMTP_USER", "user@example.com"),
        patch("app.email_service.SMTP_PASSWORD", "secret"),
        patch("app.email_service.EMAIL_FROM", "test@openhack.local"),
        patch("smtplib.SMTP") as MockSMTP,
    ):
        mock_server = MagicMock()
        MockSMTP.return_value.__enter__.return_value = mock_server

        await _send_smtp("recipient@example.com", "Hello", "Body text")

        MockSMTP.assert_called_once_with("smtp.example.com", 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user@example.com", "secret")
        mock_server.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_send_smtp_missing_host_raises():
    """Guard: empty SMTP_HOST raises ValueError."""
    with (
        patch("app.email_service.SMTP_HOST", ""),
        patch("app.email_service.SMTP_USE_TLS", False),
        patch("app.email_service.SMTP_USER", ""),
        patch("app.email_service.SMTP_PASSWORD", ""),
    ):
        with pytest.raises(ValueError, match="SMTP host not configured"):
            await _send_smtp("recipient@example.com", "Hello", "Body text")
