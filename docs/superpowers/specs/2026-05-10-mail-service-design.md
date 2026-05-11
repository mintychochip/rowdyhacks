# Mail Service Design Spec

**Project:** OpenHack (formerly RowdyHacks)
**Date:** 2026-05-10
**Topic:** Self-Hosted Mail Service

---

## 1. Purpose

Provide a self-contained email sending and inspection capability for the OpenHack hackathon framework so that:

- Developers can run the full stack locally without external email API keys (SendGrid, Mailgun, etc.).
- Hackathon organizers deploying on their own infrastructure have a zero-external-dependency option for transactional emails.
- Emails are inspectable during development and testing.

The service is **not** intended as a production-grade, high-deliverability mail relay. For that, organizers should still use a transactional email provider with proper DKIM/SPF/DMARC on a real domain. This spec optimizes for local development and simple self-hosting.

---

## 2. Architecture

### 2.1 Default Mode — Mailpit (Development / Simple Self-Host)

```
┌─────────────┐     ┌─────────────┐
│   Backend   │────▶│   Mailpit   │
│  (FastAPI)  │ SMTP│  :1025      │
└─────────────┘     │  Web: :8025 │──▶ Browser (inspect emails)
                    └─────────────┘
```

- Mailpit listens on SMTP port `1025` and captures every message.
- A web UI on port `8025` lets anyone with network access browse, search, and preview emails.
- No authentication on SMTP (dev only). Mailpit accepts any `MAIL FROM` / `RCPT TO`.
- Auto-cleanup after a configured max message count.

### 2.2 Optional Overlay — Postfix (Real Relay)

For people who want actual outbound delivery without an external API:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Backend   │────▶│   Postfix   │────▶│  Internet   │
│  (FastAPI)  │ SMTP│  :25 / :587 │relay│  (real mail)│
└─────────────┘     └─────────────┘     └─────────────┘
```

- A separate `docker-compose.mail.yml` overlay swaps in a Postfix container.
- Backend config changes the target host and port via environment variables.
- **Caveat:** Without DKIM/SPF/DMARC on a real domain, deliverability is poor. This is documented as an advanced/optional path.

---

## 3. Docker Compose Changes

### 3.1 `docker-compose.dev.yml` — Add Mailpit Service

Add the `mail` service and a `mailpit_data` volume:

```yaml
services:
  # ... existing services (db, redis, qdrant, backend, frontend) ...

  mail:
    image: axllent/mailpit:latest
    restart: unless-stopped
    ports:
      - "127.0.0.1:8025:8025"   # Web UI
      - "127.0.0.1:1025:1025"   # SMTP
    environment:
      MP_MAX_MESSAGES: 5000
      MP_DATABASE: /data/mailpit.db
      MP_SMTP_AUTH_ACCEPT_ANY: 1
      MP_SMTP_AUTH_ALLOW_INSECURE: 1
    volumes:
      - mailpit_data:/data
    # No healthcheck — Mailpit is a Go binary image that may not include /bin/sh or wget.
    # Nothing depends on mail being healthy; backend handles send failures without blocking requests.

volumes:
  # ... existing volumes ...
  mailpit_data:
```

Backend `depends_on` should **not** require `mail` to be healthy. If the `mail` container is down, the backend's SMTP send will fail with a connection error. The existing `send_email()` already catches all exceptions and retries up to 3 times before marking the email as failed in the `EmailLog` table, so the calling request is not blocked.

Also add Mailpit overrides to the `backend` service environment in `docker-compose.dev.yml`:

```yaml
  backend:
    # ... existing config ...
    environment:
      # ... existing env vars ...
      HACKVERIFY_SMTP_HOST: mail
      HACKVERIFY_SMTP_PORT: 1025
      HACKVERIFY_SMTP_USE_TLS: "false"
      HACKVERIFY_EMAIL_PROVIDER: smtp
```

### 3.2 Optional `docker-compose.mail.yml` — Postfix Overlay

```yaml
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
    # No healthcheck; Postfix starts fast enough

  backend:
    # ... existing backend config merged from base compose ...
    environment:
      # Override the dev Mailpit defaults for the Postfix overlay
      HACKVERIFY_EMAIL_PROVIDER: smtp
      HACKVERIFY_SMTP_HOST: mail
      HACKVERIFY_SMTP_PORT: 587
      HACKVERIFY_SMTP_USE_TLS: "false"

volumes:
  postfix_spool:
```

Run with:

```bash
docker-compose -f docker-compose.yml -f docker-compose.mail.yml up -d
```

---

## 4. Backend Config Updates

### 4.1 `backend/app/config.py`

Keep defaults backward-compatible so existing production deployments are not broken. The Mailpit values are injected via `docker-compose.dev.yml` environment variables instead.

Add one new field:

```python
smtp_use_tls: bool = Field(default=True, description="Enable STARTTLS for SMTP connections")
```

Existing fields stay as-is:

```python
smtp_host: str = Field(default="", description="SMTP server hostname")
smtp_port: int = Field(default=587, description="SMTP server port")
smtp_user: str = Field(default="", description="SMTP username")
smtp_password: str = Field(default="", description="SMTP password")
```

The `EMAIL_PROVIDER` enum stays (`sendgrid` vs `smtp`). When set to `smtp`, the backend sends via the configured `smtp_host:smtp_port`.

### 4.2 `backend/app/email_service.py`

Two changes to `_send_smtp()`:

1. **Relax the guard** so it only requires `SMTP_HOST` (not `SMTP_USER` or `SMTP_PASSWORD`). Mailpit does not need credentials.
2. **Make `starttls()` conditional** on `SMTP_USE_TLS`, and make `login()` conditional on `SMTP_USER` being set. This avoids TLS errors against a Postfix container inside the Docker network that lacks a valid certificate.

Only the inner `_send()` logic changes; the outer `async def _send_smtp(...)` and `loop.run_in_executor(...)` scaffolding stays the same.

```python
async def _send_smtp(to_email: str, subject: str, body: str) -> None:
    if not SMTP_HOST:
        raise ValueError("SMTP host not configured")

    def _send():
        msg = MIMEMultipart()
        # EMAIL_FROM is the existing module-level constant from app.config
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

---

## 5. Email Inspection (Mailpit Web UI)

- **URL:** `http://localhost:8025`
- **Features:**
  - List view with subject, from, to, date
  - HTML and plain-text body preview
  - Raw headers inspection
  - Search by subject, from, to
  - Auto-cleanup after `MP_MAX_MESSAGES` (default 5000)
- **Security:** Only bound to `127.0.0.1` in dev. In production-like deploys, the port should not be exposed publicly unless behind auth.

---

## 6. Self-Hosting Documentation (Add to README / DEPLOY.md)

### Quick Start (Default — No External Email Provider)

1. Start the stack:
   ```bash
   docker-compose -f docker-compose.dev.yml up -d
   ```
2. The app sends emails to `mail:1025` automatically.
3. Browse captured emails at `http://localhost:8025`.
4. No API keys needed.

### With a Real SMTP Relay (Advanced)

1. Set environment variables:
   ```bash
   export SMTP_RELAY_HOST=smtp.mailgun.org
   export SMTP_RELAY_USER=postmaster@yourdomain.com
   export SMTP_RELAY_PASSWORD=your-mailgun-key
   export MAIL_HOSTNAME=yourdomain.com
   ```
2. Start with the overlay:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.mail.yml up -d
   ```
3. Ensure your domain has SPF/DKIM/DMARC records for deliverability.

### With SendGrid (Existing Behavior)

1. Set in `.env`:
   ```
   HACKVERIFY_EMAIL_PROVIDER=sendgrid
   HACKVERIFY_SENDGRID_API_KEY=SG.xxx
   ```
2. Restart the backend. Emails go through SendGrid instead of the local SMTP host.

---

## 7. Testing Plan

1. **Unit test:** `_send_smtp()` with `SMTP_USE_TLS=False` and `SMTP_USER=""` skips both `starttls()` and `login()`.
2. **Integration test:** Spin up Mailpit in Docker, send an email via the backend, assert the message appears in Mailpit's API (`GET http://mail:8025/api/v1/messages` from inside the container network).
3. **Config test:** Changing `HACKVERIFY_EMAIL_PROVIDER=sendgrid` routes through SendGrid; changing back to `smtp` routes to local Mailpit.

---

## 8. Security Considerations

- Mailpit's `MP_SMTP_AUTH_ACCEPT_ANY=1` and `MP_SMTP_AUTH_ALLOW_INSECURE=1` are **dev-only**. They are never used in production compose files.
- The Mailpit web UI is bound to `127.0.0.1` so only localhost can browse emails.
- Postfix overlay is documented with a clear warning about deliverability and domain setup.
