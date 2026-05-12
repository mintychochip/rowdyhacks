"""Email service with retry logic and logging."""

import asyncio
import smtplib
import uuid
from datetime import UTC, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import (
    EMAIL_FROM,
    EMAIL_PROVIDER,
    SENDGRID_API_KEY,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USE_TLS,
    SMTP_USER,
)
from app.models import EmailLog

# Email templates
EMAIL_TEMPLATES = {
    "application_received": {
        "subject": "Application Received - {hackathon_name}",
        "body": """Hi {name},

Your application to {hackathon_name} has been received! We'll review it and get back to you soon.

Best,
{hackathon_name} Team
""",
    },
    "status_accepted": {
        "subject": "You're In! {hackathon_name} Application Accepted",
        "body": """Hi {name},

Congratulations! Your application to {hackathon_name} has been accepted.

Your QR code for check-in is ready. You can view it in your dashboard.

Event Details:
Date: {start_date} - {end_date}
Location: {venue}

See you there!
{hackathon_name} Team
""",
    },
    "status_waitlisted": {
        "subject": "You're on the Waitlist - {hackathon_name}",
        "body": """Hi {name},

Thanks for applying to {hackathon_name}! Unfortunately, we're currently at capacity and have placed you on the waitlist.

Your position: #{waitlist_position}

If a spot opens up, we'll notify you immediately. Hang tight!

Best,
{hackathon_name} Team
""",
    },
    "status_rejected": {
        "subject": "Update on your {hackathon_name} Application",
        "body": """Hi {name},

Thank you for your interest in {hackathon_name}. After careful consideration, we won't be able to accommodate your application this time.

We encourage you to apply to future events!

Best,
{hackathon_name} Team
""",
    },
    "spot_offered": {
        "subject": "Spot Available! Accept by {deadline} - {hackathon_name}",
        "body": """Hi {name},

Great news! A spot has opened up for {hackathon_name} and you're next on the waitlist.

You have 24 hours to accept this offer (until {deadline}).

Accept your spot: {accept_url}

If you don't respond within 24 hours, we'll offer the spot to the next person.

Best,
{hackathon_name} Team
""",
    },
    "event_reminder": {
        "subject": "Tomorrow: {hackathon_name} Starts!",
        "body": """Hi {name},

Just a reminder that {hackathon_name} starts tomorrow ({start_date})!

Check-in opens at {checkin_time}. Don't forget to bring your QR code.

See you soon!
{hackathon_name} Team
""",
    },
    "custom_blast": {
        "subject": "{subject}",
        "body": """Hi {name},

{body}

Best,
The Organizing Team
""",
    },
    "password_reset": {
        "subject": "Password Reset Request",
        "body": """Hi,

You requested a password reset. Click the link below to reset your password:

{reset_url}

This link will expire in 1 hour.

If you did not request this, please ignore this email.
""",
    },
}


async def send_email(
    to_email: str,
    email_type: str,
    context: dict[str, Any],
    registration_id: uuid.UUID | None = None,
    hackathon_id: uuid.UUID | None = None,
    db: AsyncSession | None = None,
) -> bool:
    """Send a templated email with 3-attempt exponential-backoff retry and database logging.

    Behavior:
    1. Look up the template from ``EMAIL_TEMPLATES``; raise ValueError if unknown.
    2. Render subject and body via ``str.format(**context)``.
    3. If a database session is provided, create a pending EmailLog row and flush.
    4. Initialize ``last_error`` to None.
    5. Loop up to 3 attempts:
       a. Dispatch via SendGrid or SMTP based on ``EMAIL_PROVIDER``.
       b. On success, update the EmailLog to ``sent``, commit, and return True.
       c. On failure, capture the error, increment retry_count, and sleep ``2**attempt`` seconds.
    6. After all retries fail, update the EmailLog to ``failed``, commit, and return False.

    Raises: ValueError if ``email_type`` is not a key in ``EMAIL_TEMPLATES``. Database errors may propagate.
    Side Effects: Inserts/updates an EmailLog row; commits the DB transaction; sends an external email.
    Dependencies: app.email_service._send_sendgrid, app.email_service._send_smtp, app.models.EmailLog.
    Consumers: Background jobs, registration status change handlers, and internal services.
    """
    template = EMAIL_TEMPLATES.get(email_type)
    if not template:
        raise ValueError(f"Unknown email type: {email_type}")

    subject = template["subject"].format(**context)
    body = template["body"].format(**context)

    # Log attempt
    email_log = None
    if db:
        email_log = EmailLog(
            id=uuid.uuid4(),
            registration_id=registration_id,
            hackathon_id=hackathon_id,
            email_type=email_type,
            recipient_email=to_email,
            status="pending",
            retry_count=0,
        )
        db.add(email_log)
        await db.flush()

    # Try sending with 3-attempt retry
    last_error = None
    for attempt in range(3):
        try:
            if EMAIL_PROVIDER == "sendgrid":
                await _send_sendgrid(to_email, subject, body)
            else:
                await _send_smtp(to_email, subject, body)

            # Success
            if email_log:
                email_log.status = "sent"
                email_log.sent_at = datetime.now(UTC)
                await db.commit()
            return True

        except Exception as e:
            last_error = str(e)
            if email_log:
                email_log.retry_count = attempt + 1
            if attempt < 2:  # Don't sleep on last attempt
                await asyncio.sleep(2**attempt)  # Exponential backoff: 1s, 2s

    # All retries failed
    if email_log:
        email_log.status = "failed"
        email_log.error_message = last_error
        await db.commit()

    return False


async def _send_sendgrid(to_email: str, subject: str, body: str) -> None:
    """Deliver an email via the SendGrid v3 Mail Send API.

    Behavior:
    1. Verify ``SENDGRID_API_KEY`` is configured; raise ValueError if missing.
    2. Build a SendGrid personalizations payload with the recipient, sender, subject, and plain-text body.
    3. POST the payload to ``https://api.sendgrid.com/v3/mail/send`` with Bearer authorization.
    4. Raise on non-2xx HTTP responses.

    Raises: ValueError if ``SENDGRID_API_KEY`` is missing. httpx.HTTPStatusError on non-2xx responses.
    Side Effects: Performs one outbound HTTPS request to SendGrid.
    Dependencies: httpx.AsyncClient, app.config.SENDGRID_API_KEY, app.config.EMAIL_FROM.
    Consumers: app.email_service.send_email, app.email_service.send_email_with_retry.
    """
    if not SENDGRID_API_KEY:
        raise ValueError("SENDGRID_API_KEY not configured")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={"Authorization": f"Bearer {SENDGRID_API_KEY}"},
            json={
                "personalizations": [{"to": [{"email": to_email}]}],
                "from": {"email": EMAIL_FROM},
                "subject": subject,
                "content": [{"type": "text/plain", "value": body}],
            },
        )
        response.raise_for_status()


async def _send_smtp(to_email: str, subject: str, body: str) -> None:
    """Deliver an email via a configured SMTP relay using ``smtplib``.

    Behavior:
    1. Verify ``SMTP_HOST`` is configured; raise ValueError if missing.
    2. Build a ``MIMEMultipart`` message with From, To, Subject, and a plain-text MIME part.
    3. Offload the blocking SMTP call to a thread-pool executor:
       a. Open ``smtplib.SMTP`` to the configured host and port.
       b. Start TLS if ``SMTP_USE_TLS`` is enabled.
       c. Authenticate with ``server.login`` when credentials are present.
       d. Send the message via ``server.send_message``.
    4. Await the executor future and return.

    Raises: ValueError if SMTP host is missing. smtplib.SMTPException on relay errors.
    Side Effects: Opens a TCP connection to the SMTP host; may perform TLS and AUTH.
    Dependencies: smtplib.SMTP, email.mime.multipart.MIMEMultipart, email.mime.text.MIMEText, asyncio.get_event_loop.
    Consumers: app.email_service.send_email, app.email_service.send_email_with_retry.
    """
    if not SMTP_HOST:
        raise ValueError("SMTP host not configured")

    # Run blocking SMTP in thread pool
    def _send():
        """Build and send the SMTP message in a blocking call.

        Behavior:
        1. Construct a MIMEMultipart message with From, To, and Subject headers.
        2. Attach the plaintext body.
        3. Connect to the configured SMTP host and port.
        4. Start TLS and authenticate if credentials are configured.
        5. Send the message and close the connection.

        Raises: ValueError if SMTP host is not configured.
        Side Effects: Opens a network connection to the SMTP server and sends an email.
        Dependencies: smtplib, email.mime modules.
        Consumers: _send_email async wrapper.
        """
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


async def send_email_with_retry(to_email: str, email_type: str, context: dict[str, Any], max_retries: int = 3) -> bool:
    """Fire-and-forget email helper for background jobs that do not require DB logging.

    Behavior:
    1. Look up the template from ``EMAIL_TEMPLATES``; return False if unknown.
    2. Render subject and body via ``str.format(**context)``.
    3. Loop up to ``max_retries`` attempts:
       a. Dispatch via SendGrid or SMTP based on ``EMAIL_PROVIDER``.
       b. On success, return True.
       c. On failure, sleep ``2**attempt`` seconds before retrying.
    4. Return False if all attempts are exhausted.

    Raises: None (all exceptions are swallowed internally).
    Side Effects: Sends an external email via SendGrid or SMTP; does not touch the database.
    Dependencies: app.email_service._send_sendgrid, app.email_service._send_smtp.
    Consumers: Background job scheduler (e.g., event reminders, waitlist offers).
    """
    template = EMAIL_TEMPLATES.get(email_type)
    if not template:
        return False

    subject = template["subject"].format(**context)
    body = template["body"].format(**context)

    for attempt in range(max_retries):
        try:
            if EMAIL_PROVIDER == "sendgrid":
                await _send_sendgrid(to_email, subject, body)
            else:
                await _send_smtp(to_email, subject, body)
            return True
        except Exception:
            if attempt < max_retries - 1:
                await asyncio.sleep(2**attempt)
    return False


async def get_failed_emails(db: AsyncSession, hackathon_id: uuid.UUID | None = None) -> list[EmailLog]:
    """Retrieve all failed email log records, optionally scoped to one hackathon.

    Behavior:
    1. Build a base query selecting EmailLog rows where status equals ``failed``.
    2. If a hackathon_id is provided, add an additional filter on ``hackathon_id``.
    3. Execute the query and return all matching ORM objects.

    Raises: None under normal conditions. Database errors propagate.
    Side Effects: None (read-only).
    Dependencies: sqlalchemy.select, app.models.EmailLog.
    Consumers: Admin dashboard and monitoring routes.
    """
    query = select(EmailLog).where(EmailLog.status == "failed")
    if hackathon_id:
        query = query.where(EmailLog.hackathon_id == hackathon_id)
    result = await db.execute(query)
    return result.scalars().all()
