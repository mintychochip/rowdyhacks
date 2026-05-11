# Mail Service Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a self-hosted Mailpit email capture service in Docker and make the backend SMTP client work with no-auth, no-TLS local relays.

**Architecture:** Mailpit runs as a `mail` service in `docker-compose.dev.yml`. The backend sends SMTP to `mail:1025` with no TLS and no auth. A separate `docker-compose.mail.yml` overlay swaps in Postfix for real outbound relay. The backend gains an `SMTP_USE_TLS` toggle so `starttls()` can be skipped for internal Docker-network SMTP hops.

**Tech Stack:** Docker Compose, Mailpit, Postfix, FastAPI, Python `smtplib`, `unittest.mock`

---

## File Structure

| File | Responsibility |
|---|---|
| `docker-compose.dev.yml` | Adds `mail` (Mailpit) service and backend env overrides |
| `docker-compose.mail.yml` | Optional Postfix overlay with backend env overrides |
| `backend/app/config.py` | Adds `smtp_use_tls: bool` setting, backward-compatible defaults |
| `backend/app/email_service.py` | Relaxes SMTP guard, conditional `starttls()`/`login()` |
| `backend/tests/test_email_service.py` | Unit tests for `_send_smtp()` behavior with mocks |
| `backend/tests/test_mailpit_integration.py` | Integration test: send email, verify in Mailpit API |

---

## Chunk 1: Backend Config & SMTP Logic

### Task 1: Add `smtp_use_tls` to config

**Files:**
- Modify: `backend/app/config.py:147-175`
- Test: `backend/tests/test_config.py`

- [ ] **Step 1: Write failing test for `smtp_use_tls`**

In `backend/tests/test_config.py`, add:

```python
def test_smtp_use_tls_default():
    from app.config import Settings
    s = Settings(_env_file=None)
    assert s.smtp_use_tls is True
```

Run: `pytest backend/tests/test_config.py::test_smtp_use_tls_default -v`
Expected: FAIL — `AttributeError: 'Settings' object has no attribute 'smtp_use_tls'`

- [ ] **Step 2: Add `smtp_use_tls` field to `Settings`**

In `backend/app/config.py`, after the `email_from` field (line ~173), add:

```python
smtp_use_tls: bool = Field(default=True, description="Enable STARTTLS for SMTP connections")
```

Run: `pytest backend/tests/test_config.py::test_smtp_use_tls_default -v`
Expected: PASS

- [ ] **Step 3: Export `SMTP_USE_TLS` for backward compatibility**

In `backend/app/config.py`, append at the end of the backward-compat block (after `EMAIL_FROM = settings.email_from`), add:

```python
SMTP_USE_TLS = settings.smtp_use_tls
```

Run: `pytest backend/tests/test_config.py::test_smtp_use_tls_default -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/config.py backend/tests/test_config.py
git commit -m "feat(mail): add SMTP_USE_TLS config toggle"
```

---

### Task 2: Update `_send_smtp()` in email_service.py

**Files:**
- Modify: `backend/app/email_service.py:15,275-329`
- Test: `backend/tests/test_email_service.py` (new file)

- [ ] **Step 1: Import `SMTP_USE_TLS` and write failing tests**

In `backend/app/email_service.py`, update the config import on line 15:

```python
from app.config import EMAIL_FROM, EMAIL_PROVIDER, SENDGRID_API_KEY, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USE_TLS, SMTP_USER
```

Create `backend/tests/test_email_service.py`:

```python
from unittest.mock import MagicMock, patch

import pytest

from app.email_service import _send_smtp


@pytest.mark.asyncio
async def test_send_smtp_no_tls_no_auth():
    """Mailpit mode: no STARTTLS, no login when USE_TLS=False and USER=''."""
    with patch("app.email_service.SMTP_HOST", "mail"), \
         patch("app.email_service.SMTP_PORT", 1025), \
         patch("app.email_service.SMTP_USE_TLS", False), \
         patch("app.email_service.SMTP_USER", ""), \
         patch("app.email_service.SMTP_PASSWORD", ""), \
         patch("app.email_service.EMAIL_FROM", "test@openhack.local"), \
         patch("smtplib.SMTP") as MockSMTP:

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
    with patch("app.email_service.SMTP_HOST", "smtp.example.com"), \
         patch("app.email_service.SMTP_PORT", 587), \
         patch("app.email_service.SMTP_USE_TLS", True), \
         patch("app.email_service.SMTP_USER", "user@example.com"), \
         patch("app.email_service.SMTP_PASSWORD", "secret"), \
         patch("app.email_service.EMAIL_FROM", "test@openhack.local"), \
         patch("smtplib.SMTP") as MockSMTP:

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
    with patch("app.email_service.SMTP_HOST", ""), \
         patch("app.email_service.SMTP_USE_TLS", False), \
         patch("app.email_service.SMTP_USER", ""), \
         patch("app.email_service.SMTP_PASSWORD", ""):

        with pytest.raises(ValueError, match="SMTP host not configured"):
            await _send_smtp("recipient@example.com", "Hello", "Body text")
```

Run: `pytest backend/tests/test_email_service.py -v`
Expected: 2 FAILs, 1 PASS — guard still requires all three vars (tests 1 and 3 fail), while TLS+auth are already unconditional in the old code (test 2 passes).

- [ ] **Step 2: Relax guard and make TLS/login conditional**

Replace `_send_smtp()` in `backend/app/email_service.py` (lines 275-329) with:

```python
async def _send_smtp(to_email: str, subject: str, body: str) -> None:
    """
    Deliver an email via a configured SMTP relay using ``smtplib``.

    Expected Inputs:
        - ``to_email`` (str): Recipient address.
        - ``subject`` (str): Pre-rendered email subject line.
        - ``body`` (str): Pre-rendered plain-text body.

    Step-by-Step Implementation:
        1. Verify ``SMTP_HOST`` is truthy; otherwise raise ``ValueError``.
        2. Build a ``MIMEMultipart`` message:
           - ``From``: ``EMAIL_FROM``
           - ``To``: ``to_email``
           - ``Subject``: subject string
           - Attach a ``MIMEText`` part with the body and MIME type ``"plain"``.
        3. Offload the blocking SMTP call to a thread-pool executor:
           a. Open ``smtplib.SMTP(SMTP_HOST, SMTP_PORT)`` context manager.
           b. If ``SMTP_USE_TLS`` is ``True``, invoke ``server.starttls()``.
           c. If ``SMTP_USER`` is truthy, authenticate with ``server.login(SMTP_USER, SMTP_PASSWORD)``.
           d. Send the message via ``server.send_message(msg)``.
        4. Await the executor future inside the active asyncio event loop.

    Side Effects:
        - Opens a TCP connection to the configured SMTP host.
        - May perform TLS handshake and AUTH login sequence.

    Returns:
        None

    Raises:
        ValueError: If ``SMTP_HOST`` is missing or empty.
        smtplib.SMTPException: On authentication failure, connection error, or
          send rejection by the relay.
        Any network or TLS exception may propagate.
    """
    if not SMTP_HOST:
        raise ValueError("SMTP host not configured")

    # Run blocking SMTP in thread pool
    def _send():
        msg = MIMEMultipart()
        msg["From"] = EMAIL_FROM
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            if SMTP_USE_TLS:
                server.starttls()
            if SMTP_USER:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _send)
```

Run: `pytest backend/tests/test_email_service.py -v`
Expected: 3 PASS

- [ ] **Step 3: Commit**

```bash
git add backend/app/email_service.py backend/tests/test_email_service.py
git commit -m "feat(mail): conditional SMTP TLS and auth for local relays"
```

---

## Chunk 2: Docker Compose Changes

### Task 3: Add Mailpit to `docker-compose.dev.yml`

**Files:**
- Modify: `docker-compose.dev.yml`
- Test: Manual — verify `docker-compose -f docker-compose.dev.yml config` parses

- [ ] **Step 1: Add `mail` service and `mailpit_data` volume**

In `docker-compose.dev.yml`, add the `mail` service after the `frontend` service. Then add `mailpit_data:` to the **existing** `volumes:` block at the bottom.

> **Do NOT add `mail` to `backend.depends_on`.** The backend handles SMTP failures gracefully and should not block startup if Mailpit is slow.

```yaml
  mail:
    image: axllent/mailpit:latest
    restart: unless-stopped
    ports:
      - "127.0.0.1:8025:8025"
      - "127.0.0.1:1025:1025"
    environment:
      MP_MAX_MESSAGES: 5000
      MP_DATABASE: /data/mailpit.db
      MP_SMTP_AUTH_ACCEPT_ANY: 1
      MP_SMTP_AUTH_ALLOW_INSECURE: 1
    volumes:
      - mailpit_data:/data
```

In the existing `volumes:` block, append:

```yaml
  mailpit_data:
```

- [ ] **Step 2: Add backend env overrides for Mailpit**

In the `backend` service `environment` block, add:

```yaml
      HACKVERIFY_SMTP_HOST: mail
      HACKVERIFY_SMTP_PORT: 1025
      HACKVERIFY_SMTP_USE_TLS: "false"
      HACKVERIFY_EMAIL_PROVIDER: smtp
```

Run: `docker-compose -f docker-compose.dev.yml config > /dev/null`
Expected: No errors (valid YAML / compose syntax)

- [ ] **Step 3: Commit**

```bash
git add docker-compose.dev.yml
git commit -m "feat(mail): add Mailpit service to dev compose"
```

---

### Task 4: Create `docker-compose.mail.yml` (Postfix overlay)

**Files:**
- Create: `docker-compose.mail.yml`
- Test: Manual — verify `docker-compose -f docker-compose.yml -f docker-compose.mail.yml config` parses

- [ ] **Step 1: Write the overlay file**

Create `docker-compose.mail.yml`:

```yaml
version: '3.8'

# Optional overlay: replace Mailpit with Postfix for real outbound relay.
# Usage:
#   export SMTP_RELAY_HOST=smtp.mailgun.org
#   export SMTP_RELAY_USER=postmaster@yourdomain.com
#   export SMTP_RELAY_PASSWORD=your-key
#   export MAIL_HOSTNAME=yourdomain.com
#   docker-compose -f docker-compose.yml -f docker-compose.mail.yml up -d
#
# WARNING: Without SPF/DKIM/DMARC on your domain, deliverability will be poor.

services:
  mail:
    image: juanluisbaptiste/postfix:latest
    restart: unless-stopped
    environment:
      SMTP_SERVER: ${SMTP_RELAY_HOST:-}
      SMTP_USERNAME: ${SMTP_RELAY_USER:-}
      SMTP_PASSWORD: ${SMTP_RELAY_PASSWORD:-}
      SERVER_HOSTNAME: ${MAIL_HOSTNAME:-openhack.local}
    ports:
      - "127.0.0.1:25:25"
      - "127.0.0.1:587:587"
    volumes:
      - postfix_spool:/var/spool/postfix

  backend:
    environment:
      # Switch backend from Mailpit defaults to Postfix overlay
      HACKVERIFY_EMAIL_PROVIDER: smtp
      HACKVERIFY_SMTP_HOST: mail
      HACKVERIFY_SMTP_PORT: 587
      HACKVERIFY_SMTP_USE_TLS: "false"

volumes:
  postfix_spool:
```

Run: `docker-compose -f docker-compose.yml -f docker-compose.mail.yml config > /dev/null`
Expected: No errors

- [ ] **Step 2: Commit**

```bash
git add docker-compose.mail.yml
git commit -m "feat(mail): add optional Postfix overlay for real SMTP relay"
```

---

## Chunk 3: Integration Test

### Task 5: Write Mailpit integration test

**Files:**
- Create: `backend/tests/test_mailpit_integration.py`
- Requires: A running Mailpit container (can be spun up in test with `testcontainers` or Docker SDK)

> **Note:** The project currently uses SQLite in-memory for unit tests. The integration test requires a real Mailpit container. If `testcontainers` is not installed, add it to `requirements.txt` or `requirements-dev.txt`.

- [ ] **Step 1: Add `testcontainers` to dev requirements**

Run this command from the repo root:

```bash
grep -q "testcontainers" backend/requirements.txt || echo "testcontainers>=4.0.0" >> backend/requirements.txt
```

- [ ] **Step 2: Write the integration test**

Create `backend/tests/test_mailpit_integration.py`:

```python
import asyncio

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
    original_use_tls = es.SMTP_USE_TLS
    original_user = es.SMTP_USER
    original_from = es.EMAIL_FROM

    es.SMTP_HOST = mailpit_container["smtp_host"]
    es.SMTP_PORT = mailpit_container["smtp_port"]
    es.SMTP_USE_TLS = False
    es.SMTP_USER = ""
    es.EMAIL_FROM = "test@openhack.local"

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
        es.SMTP_USE_TLS = original_use_tls
        es.SMTP_USER = original_user
        es.EMAIL_FROM = original_from
```

- [ ] **Step 3: Run the integration test**

```bash
pytest backend/tests/test_mailpit_integration.py -v -s
```

Expected: PASS — test sends email, finds it in Mailpit API. If Docker is unavailable, the fixture skips with `pytest.skip("Docker not available")`.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_mailpit_integration.py backend/requirements.txt
git commit -m "test(mail): add Mailpit integration test"
```

---

## Chunk 4: Documentation

### Task 6: Update self-hosting docs

**Files:**
- Modify: `DEPLOY.md` or `README.md` (whichever contains deployment instructions)

- [ ] **Step 1: Add mail service section to deployment docs**

In `DEPLOY.md`, find the existing Docker Compose quick-start section and add the following **after** it:

```markdown
### Email

By default, the dev stack uses [Mailpit](https://github.com/axllent/mailpit) to capture all outgoing emails locally. Browse them at http://localhost:8025. No external email provider is required.

For real outbound email, you have two options:

1. **SendGrid** (recommended for production): Set `HACKVERIFY_EMAIL_PROVIDER=sendgrid` and `HACKVERIFY_SENDGRID_API_KEY=SG.xxx` in your `.env`.

2. **Self-hosted Postfix relay** (advanced, poor deliverability without domain DNS records):
   ```bash
   export SMTP_RELAY_HOST=smtp.mailgun.org
   export SMTP_RELAY_USER=postmaster@yourdomain.com
   export SMTP_RELAY_PASSWORD=your-key
   export MAIL_HOSTNAME=yourdomain.com
   docker-compose -f docker-compose.yml -f docker-compose.mail.yml up -d
   ```
```

- [ ] **Step 2: Commit**

```bash
git add DEPLOY.md
git commit -m "docs(mail): add email setup options to deployment guide"
```

---

## Verification Checklist

Before declaring this complete, confirm:

- [ ] `pytest backend/tests/test_email_service.py -v` passes (3 tests)
- [ ] `pytest backend/tests/test_config.py -v` still passes (no regressions)
- [ ] `docker-compose -f docker-compose.dev.yml config` is valid YAML
- [ ] `docker-compose -f docker-compose.yml -f docker-compose.mail.yml config` is valid YAML
- [ ] `docker-compose -f docker-compose.dev.yml up -d` starts mail service, backend can send, Mailpit UI shows emails
- [ ] All changes committed
