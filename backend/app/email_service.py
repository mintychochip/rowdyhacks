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

from app.config import EMAIL_FROM, EMAIL_PROVIDER, SENDGRID_API_KEY, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER
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
}


async def send_email(
    to_email: str,
    email_type: str,
    context: dict[str, Any],
    registration_id: uuid.UUID | None = None,
    hackathon_id: uuid.UUID | None = None,
    db: AsyncSession | None = None,
) -> bool:
    """Send an email with retry logic and logging."""
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
    """Send via SendGrid API."""
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
    """Send via SMTP."""
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASSWORD]):
        raise ValueError("SMTP not fully configured")

    # Run blocking SMTP in thread pool
    def _send():
        msg = MIMEMultipart()
        msg["From"] = EMAIL_FROM
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _send)


async def send_email_with_retry(to_email: str, email_type: str, context: dict[str, Any], max_retries: int = 3) -> bool:
    """Send email without DB logging (for background jobs)."""
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
    """Get failed emails for retry (admin function)."""
    query = select(EmailLog).where(EmailLog.status == "failed")
    if hackathon_id:
        query = query.where(EmailLog.hackathon_id == hackathon_id)
    result = await db.execute(query)
    return result.scalars().all()
