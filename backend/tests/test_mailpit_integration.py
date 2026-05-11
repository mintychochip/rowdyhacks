import asyncio
import smtplib

import httpx
import pytest
from testcontainers.core.container import DockerContainer


@pytest.fixture(scope="module")
def mailpit_container():
    """Spin up Mailpit and yield its API URL."""
    try:
        import docker
        docker.from_env().ping()
    except Exception:
        pytest.skip("Docker not available")

    container = (
        DockerContainer("axllent/mailpit:latest")
        .with_exposed_ports(8025, 1025)
        .with_env("MP_MAX_MESSAGES", "5000")
        .with_env("MP_SMTP_AUTH_ACCEPT_ANY", "1")
        .with_env("MP_SMTP_AUTH_ALLOW_INSECURE", "1")
    )
    container.start()
    api_url = f"http://{container.get_container_host_ip()}:{container.get_exposed_port(8025)}"
    smtp_host = container.get_container_host_ip()
    smtp_port = container.get_exposed_port(1025)
    yield {"api_url": api_url, "smtp_host": smtp_host, "smtp_port": smtp_port}
    container.stop()


@pytest.mark.asyncio
async def test_email_appears_in_mailpit(mailpit_container):
    """Send an email via _send_smtp against a live Mailpit and verify capture."""
    import app.email_service as es

    # Patch config to point at the running Mailpit
    original_host = es.SMTP_HOST
    original_port = es.SMTP_PORT
    original_user = es.SMTP_USER
    original_password = es.SMTP_PASSWORD
    original_from = es.EMAIL_FROM

    es.SMTP_HOST = mailpit_container["smtp_host"]
    es.SMTP_PORT = mailpit_container["smtp_port"]
    es.SMTP_USER = "testuser"
    es.SMTP_PASSWORD = "testpass"
    es.EMAIL_FROM = "test@openhack.local"

    # Mailpit uses a self-signed cert; starttls would fail verification.
    # Monkeypatch it to a no-op for this test.
    original_starttls = smtplib.SMTP.starttls
    smtplib.SMTP.starttls = lambda *args, **kwargs: None

    try:
        await es._send_smtp("hacker@example.com", "Test Subject", "Test body content")

        # Give Mailpit a moment to ingest
        await asyncio.sleep(0.5)

        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{mailpit_container['api_url']}/api/v1/messages")
            resp.raise_for_status()
            data = resp.json()

        messages = data.get("messages", [])
        assert len(messages) >= 1
        latest = messages[0]
        assert latest["Subject"] == "Test Subject"
        assert latest["To"][0]["Address"] == "hacker@example.com"
        assert latest["From"]["Address"] == "test@openhack.local"
    finally:
        es.SMTP_HOST = original_host
        es.SMTP_PORT = original_port
        es.SMTP_USER = original_user
        es.SMTP_PASSWORD = original_password
        es.EMAIL_FROM = original_from
        smtplib.SMTP.starttls = original_starttls
