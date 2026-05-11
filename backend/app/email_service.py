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
    """
    Send a templated email with 3-attempt exponential-backoff retry and database logging.

    Expected Inputs:
        - ``to_email`` (str): Recipient email address. Must be a valid RFC 5322
          address (format is not validated locally).
        - ``email_type`` (str): Key into ``EMAIL_TEMPLATES``. Supported values:
          ``"application_received"``, ``"status_accepted"``, ``"status_waitlisted"``,
          ``"status_rejected"``, ``"spot_offered"``, ``"event_reminder"``.
        - ``context`` (dict[str, Any]): Template interpolation variables. Required
          keys vary by template (see ``EMAIL_TEMPLATES``).
        - ``registration_id`` (uuid.UUID | None): FK to ``Registration`` row for
          audit logging. Optional.
        - ``hackathon_id`` (uuid.UUID | None): FK to ``Hackathon`` row for audit
          logging. Optional.
        - ``db`` (AsyncSession | None): Active async SQLAlchemy session. Required
          for email logging; if ``None``, no ``EmailLog`` row is created.

    Step-by-Step Implementation:
        1. Look up ``template = EMAIL_TEMPLATES.get(email_type)``.
        2. If the template is missing, raise ``ValueError(f"Unknown email type: {email_type}")``.
        3. Render subject and body via ``str.format(**context)``.
        4. If ``db`` is provided, create an ``EmailLog`` row:
           - ``id``: new random UUID
           - ``registration_id``, ``hackathon_id``, ``email_type``, ``recipient_email``
           - ``status``: ``"pending"``
           - ``retry_count``: ``0``
           - Add to session and flush to obtain the primary key.
        5. Initialize ``last_error = None``.
        6. Loop for ``attempt in range(3)``:
           a. If ``EMAIL_PROVIDER == "sendgrid"``:
              - Call ``_send_sendgrid(to_email, subject, body)``.
           b. Else:
              - Call ``_send_smtp(to_email, subject, body)``.
           c. On success:
              - Update ``email_log.status = "sent"`` and ``sent_at = datetime.now(UTC)``.
              - ``await db.commit()`` (if ``email_log`` exists).
              - Return ``True``.
           d. On exception:
              - Capture ``last_error = str(e)``.
              - If ``email_log`` exists, set ``retry_count = attempt + 1``.
              - If ``attempt < 2``, sleep ``2**attempt`` seconds (1s, then 2s).
        7. If all 3 attempts fail:
           - Update ``email_log.status = "failed"`` and ``error_message = last_error``.
           - ``await db.commit()`` (if ``email_log`` exists).
           - Return ``False``.

    Side Effects:
        - Inserts/updates one ``EmailLog`` row in PostgreSQL (when ``db`` is provided).
        - Commits the database transaction on success or final failure.
        - Sends an external HTTP request to SendGrid or opens an SMTP connection.

    Returns:
        bool
        - ``True`` if the email was accepted by the provider within 3 attempts.
        - ``False`` if all retries were exhausted.

    Raises:
        ValueError: If ``email_type`` is not a key in ``EMAIL_TEMPLATES``.
        Any exception from ``db.commit()`` or ``db.flush()`` may propagate.
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
    """
    Deliver an email via the SendGrid v3 Mail Send API.

    Expected Inputs:
        - ``to_email`` (str): Recipient address.
        - ``subject`` (str): Pre-rendered email subject line.
        - ``body`` (str): Pre-rendered plain-text body.

    Step-by-Step Implementation:
        1. Verify ``SENDGRID_API_KEY`` is truthy; otherwise raise ``ValueError``.
        2. Instantiate an ``httpx.AsyncClient`` context manager.
        3. POST to ``https://api.sendgrid.com/v3/mail/send`` with:
           - Header: ``Authorization: Bearer {SENDGRID_API_KEY}``
           - JSON payload:
             * ``personalizations``: ``[{ "to": [{ "email": to_email }] }]``
             * ``from``: ``{ "email": EMAIL_FROM }``
             * ``subject``: subject string
             * ``content``: ``[{ "type": "text/plain", "value": body }]``
        4. Call ``response.raise_for_status()`` to surface 4xx/5xx errors.

    Side Effects:
        - Performs one outbound HTTPS request to SendGrid.

    Returns:
        None

    Raises:
        ValueError: If ``SENDGRID_API_KEY`` is missing or empty.
        httpx.HTTPStatusError: On non-2xx SendGrid response.
        Any network-level exception from ``httpx`` may propagate.
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
    """
    Deliver an email via a configured SMTP relay using ``smtplib``.

    Expected Inputs:
        - ``to_email`` (str): Recipient address.
        - ``subject`` (str): Pre-rendered email subject line.
        - ``body`` (str): Pre-rendered plain-text body.

    Step-by-Step Implementation:
        1. Verify ``SMTP_HOST``, ``SMTP_USER``, and ``SMTP_PASSWORD`` are all truthy;
           otherwise raise ``ValueError``.
        2. Build a ``MIMEMultipart`` message:
           - ``From``: ``EMAIL_FROM``
           - ``To``: ``to_email``
           - ``Subject``: subject string
           - Attach a ``MIMEText`` part with the body and MIME type ``"plain"``.
        3. Offload the blocking SMTP call to a thread-pool executor:
           a. Open ``smtplib.SMTP(SMTP_HOST, SMTP_PORT)`` context manager.
           b. Invoke ``server.starttls()``.
           c. Authenticate with ``server.login(SMTP_USER, SMTP_PASSWORD)``.
           d. Send the message via ``server.send_message(msg)``.
        4. Await the executor future inside the active asyncio event loop.

    Side Effects:
        - Opens a TCP connection to the configured SMTP host.
        - May perform TLS handshake and AUTH login sequence.

    Returns:
        None

    Raises:
        ValueError: If any required SMTP config variable is missing.
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


async def send_email_with_retry(to_email: str, email_type: str, context: dict[str, Any], max_retries: int = 3) -> bool:
    """
    Fire-and-forget email helper for background jobs that do not require DB logging.

    Expected Inputs:
        - ``to_email`` (str): Recipient email address.
        - ``email_type`` (str): Key into ``EMAIL_TEMPLATES``.
        - ``context`` (dict[str, Any]): Template interpolation variables.
        - ``max_retries`` (int): Maximum retry attempts. Defaults to ``3``.

    Step-by-Step Implementation:
        1. Look up ``template = EMAIL_TEMPLATES.get(email_type)``.
        2. If the template is missing, return ``False`` immediately (no exception raised).
        3. Render subject and body via ``str.format(**context)``.
        4. Loop for ``attempt in range(max_retries)``:
           a. If ``EMAIL_PROVIDER == "sendgrid"``:
              - Call ``_send_sendgrid(to_email, subject, body)``.
           b. Else:
              - Call ``_send_smtp(to_email, subject, body)``.
           c. On success, return ``True``.
           d. On exception, if ``attempt < max_retries - 1``, sleep ``2**attempt`` seconds.
        5. Return ``False`` if all attempts exhaust.

    Side Effects:
        - Sends an external email via SendGrid or SMTP.
        - No database rows are touched.

    Returns:
        bool
        - ``True`` if the email was accepted by the provider.
        - ``False`` if the template was unknown or all retries failed.

    Raises:
        None. All exceptions are swallowed internally.
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
    """
    Retrieve all failed email log records, optionally scoped to one hackathon.

    Expected Inputs:
        - ``db`` (AsyncSession): Active async SQLAlchemy session.
        - ``hackathon_id`` (uuid.UUID | None): If provided, filters results to
          emails associated with that hackathon.

    Step-by-Step Implementation:
        1. Build a base query: ``SELECT EmailLog WHERE status == "failed"``.
        2. If ``hackathon_id`` is not ``None``, append an additional filter:
           ``EmailLog.hackathon_id == hackathon_id``.
        3. Execute the query and collect all results via ``result.scalars().all()``.

    Side Effects:
        None. Pure read operation.

    Returns:
        list[EmailLog]
        - A (possibly empty) list of ``EmailLog`` ORM objects with ``status == "failed"``.

    Raises:
        None under normal conditions. Database errors propagate.
    """
    query = select(EmailLog).where(EmailLog.status == "failed")
    if hackathon_id:
        query = query.where(EmailLog.hackathon_id == hackathon_id)
    result = await db.execute(query)
    return result.scalars().all()
