# Waitlist, Email & Registration Data Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement complete waitlist system with auto-promotion, email notifications for status changes, enhanced registration data fields, and bulk demo data seeding.

**Architecture:** Database-first migrations add waitlist and registration fields. Backend implements waitlist promotion logic with row-level locking for race conditions. Email service uses direct async sending with retry. Frontend adds waitlist UI and application wizard fields.

**Tech Stack:** FastAPI, SQLAlchemy (async), PostgreSQL/SQLite, React + TypeScript, SendGrid/SMTP for email, APScheduler for background jobs.

---

## File Structure

### Backend (Python/FastAPI)
```
backend/app/
├── migrations/
│   └── 2026_05_03_add_waitlist_and_registration_fields.py  # Alembic migration
├── models.py              # ADD: declined_count, offered_at, offer_expires_at, new registration fields
├── schemas.py             # ADD: RegistrationCreate schema with new fields
├── email_service.py       # NEW: Email sending abstraction with retry
├── database.py            # MODIFY: Add email_logs table model
├── routes/
│   ├── registrations_organizer.py  # ADD: waitlist endpoints, promote endpoint
│   └── registrations.py            # MODIFY: Add waitlist_position to response, accept-offer endpoint
├── background_jobs.py     # NEW: cleanup_expired_offers, send_event_reminders
└── scripts/
    └── bulk_seed.py       # NEW: Generate 50 realistic demo registrations
```

### Frontend (React/TypeScript)
```
frontend/src/
├── pages/
│   ├── OrganizerRegistrationsPage.tsx   # ADD: Waitlist tab, new field columns
│   ├── RegistrationDetailPage.tsx       # ADD: Display new fields, waitlist actions
│   └── ApplyPage.tsx                    # MODIFY: Add new fields to wizard
├── components/
│   ├── WaitlistManager.tsx      # NEW: Organizer waitlist view with positions
│   ├── WaitlistPosition.tsx     # NEW: Participant waitlist position widget
│   ├── OfferBanner.tsx          # NEW: 24hr countdown banner for offered spots
│   └── wizard/
│       ├── WizardLogistics.tsx   # MODIFY: Add shirt_size, dietary fields
│       └── WizardReview.tsx      # MODIFY: Show new fields in review
├── services/
│   └── api.ts                   # ADD: waitlist API methods
└── types/
    └── registration.ts            # MODIFY: Add new field types
```

---

## Chunk 1: Database Migrations

### Task 1: Create Alembic Migration for Registration Fields

**Files:**
- Create: `backend/alembic/versions/2026_05_03_add_waitlist_and_registration_fields.py`

**Context:** Run `cd backend && alembic revision --autogenerate -m "add waitlist and registration fields"` first to generate base migration, then edit.

- [ ] **Step 1: Generate migration base**

Run: `cd backend && alembic revision --autogenerate -m "add waitlist and registration fields"`
Expected: Creates file in `alembic/versions/`

- [ ] **Step 2: Edit migration to add columns**

```python
"""add waitlist and registration fields

Revision ID: 2026_05_03_add_waitlist_and_registration_fields
Revises: <previous_revision>
Create Date: 2026-05-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2026_05_03_waitlist'
down_revision = '<previous_revision>'  # Update this
branch_labels = None
depends_on = None


def upgrade():
    # Add registration fields
    op.add_column('registrations', sa.Column('offered_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('registrations', sa.Column('offer_expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('registrations', sa.Column('declined_count', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('registrations', sa.Column('dietary_restrictions', sa.Text(), nullable=True))
    op.add_column('registrations', sa.Column('shirt_size', sa.String(length=10), nullable=True))
    op.add_column('registrations', sa.Column('special_needs', sa.Text(), nullable=True))
    op.add_column('registrations', sa.Column('experience_level', sa.String(length=50), nullable=True))
    op.add_column('registrations', sa.Column('school_company', sa.Text(), nullable=True))
    op.add_column('registrations', sa.Column('graduation_year', sa.Integer(), nullable=True))

    # Create index for waitlist queries
    op.create_index(
        'idx_registrations_waitlist',
        'registrations',
        ['hackathon_id', 'status', 'declined_count', 'registered_at'],
        postgresql_where=sa.text("status = 'waitlisted'")
    )

    # Create index for expired offer cleanup
    op.create_index(
        'idx_registrations_offered_expires',
        'registrations',
        ['status', 'offer_expires_at'],
        postgresql_where=sa.text("status = 'offered'")
    )

    # Create email_logs table
    op.create_table(
        'email_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('registration_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('registrations.id'), nullable=True),
        sa.Column('hackathon_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hackathons.id'), nullable=True),
        sa.Column('email_type', sa.String(length=50), nullable=False),
        sa.Column('recipient_email', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('retry_count', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )
    op.create_index('idx_email_logs_status', 'email_logs', ['status', 'retry_count'],
                    postgresql_where=sa.text("status = 'failed'"))
    op.create_index('idx_email_logs_hackathon', 'email_logs', ['hackathon_id', 'created_at'])


def downgrade():
    op.drop_table('email_logs')
    op.drop_index('idx_registrations_offered_expires', table_name='registrations')
    op.drop_index('idx_registrations_waitlist', table_name='registrations')
    op.drop_column('registrations', 'graduation_year')
    op.drop_column('registrations', 'school_company')
    op.drop_column('registrations', 'experience_level')
    op.drop_column('registrations', 'special_needs')
    op.drop_column('registrations', 'shirt_size')
    op.drop_column('registrations', 'dietary_restrictions')
    op.drop_column('registrations', 'declined_count')
    op.drop_column('registrations', 'offer_expires_at')
    op.drop_column('registrations', 'offered_at')
```

- [ ] **Step 3: Run migration locally**

Run: `cd backend && alembic upgrade head`
Expected: Migration completes successfully

- [ ] **Step 4: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat: add waitlist and registration fields migration"
```

---

## Chunk 2: Backend Models Update

### Task 2: Update Registration Model

**Files:**
- Modify: `backend/app/models.py`

- [ ] **Step 1: Add new fields to Registration model**

Add after existing Registration columns (around line 280 in models.py):

```python
    # Waitlist fields
    offered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    offer_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    declined_count: Mapped[int] = mapped_column(Integer, default=0, nullable=True)

    # Additional registration data
    dietary_restrictions: Mapped[str | None] = mapped_column(Text, nullable=True)
    shirt_size: Mapped[str | None] = mapped_column(String(10), nullable=True)
    special_needs: Mapped[str | None] = mapped_column(Text, nullable=True)
    experience_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    school_company: Mapped[str | None] = mapped_column(Text, nullable=True)
    graduation_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

- [ ] **Step 2: Create EmailLog model**

Add at end of models.py before imports close:

```python
class EmailLog(Base):
    """Track email sending for retry and auditing."""
    __tablename__ = "email_logs"

    id: Mapped[uuid.UUID] = mapped_column(Guid, primary_key=True, default=uuid.uuid4)
    registration_id: Mapped[uuid.UUID | None] = mapped_column(Guid, ForeignKey("registrations.id"), nullable=True)
    hackathon_id: Mapped[uuid.UUID | None] = mapped_column(Guid, ForeignKey("hackathons.id"), nullable=True)
    email_type: Mapped[str] = mapped_column(String(50), nullable=False)
    recipient_email: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # pending, sent, failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    registration: Mapped["Registration"] = relationship("Registration", back_populates="email_logs")
```

- [ ] **Step 3: Add email_logs relationship to Registration**

Find Registration class and add:

```python
    email_logs: Mapped[list["EmailLog"]] = relationship("EmailLog", back_populates="registration")
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/models.py
git commit -m "feat: add waitlist fields and EmailLog model"
```

---

## Chunk 3: Email Service

### Task 3: Create Email Service Module

**Files:**
- Create: `backend/app/email_service.py`
- Modify: `backend/app/config.py` (add email settings)

- [ ] **Step 1: Add email config to config.py**

```python
# Email configuration
EMAIL_PROVIDER: str = os.getenv("EMAIL_PROVIDER", "smtp")  # "sendgrid" or "smtp"
SENDGRID_API_KEY: str = os.getenv("SENDGRID_API_KEY", "")
SMTP_HOST: str = os.getenv("SMTP_HOST", "")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER: str = os.getenv("SMTP_USER", "")
SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM: str = os.getenv("EMAIL_FROM", "noreply@hackthevalley.io")
```

- [ ] **Step 2: Create email_service.py**

```python
"""Email service with retry logic and logging."""
import asyncio
import httpx
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import EmailLog, Registration, Hackathon, User
from app.config import EMAIL_PROVIDER, SENDGRID_API_KEY, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM


# Email templates
EMAIL_TEMPLATES = {
    "application_received": {
        "subject": "Application Received - {hackathon_name}",
        "body": """Hi {name},

Your application to {hackathon_name} has been received! We'll review it and get back to you soon.

Best,
{hackathon_name} Team
"""
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
"""
    },
    "status_waitlisted": {
        "subject": "You're on the Waitlist - {hackathon_name}",
        "body": """Hi {name},

Thanks for applying to {hackathon_name}! Unfortunately, we're currently at capacity and have placed you on the waitlist.

Your position: #{waitlist_position}

If a spot opens up, we'll notify you immediately. Hang tight!

Best,
{hackathon_name} Team
"""
    },
    "status_rejected": {
        "subject": "Update on your {hackathon_name} Application",
        "body": """Hi {name},

Thank you for your interest in {hackathon_name}. After careful consideration, we won't be able to accommodate your application this time.

We encourage you to apply to future events!

Best,
{hackathon_name} Team
"""
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
"""
    },
    "event_reminder": {
        "subject": "Tomorrow: {hackathon_name} Starts!",
        "body": """Hi {name},

Just a reminder that {hackathon_name} starts tomorrow ({start_date})!

Check-in opens at {checkin_time}. Don't forget to bring your QR code.

See you soon!
{hackathon_name} Team
"""
    }
}


async def send_email(
    to_email: str,
    email_type: str,
    context: dict[str, Any],
    registration_id: uuid.UUID | None = None,
    hackathon_id: uuid.UUID | None = None,
    db: AsyncSession | None = None
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
            registration_id=registration_id,
            hackathon_id=hackathon_id,
            email_type=email_type,
            recipient_email=to_email,
            status="pending",
            retry_count=0
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
                email_log.sent_at = datetime.now(timezone.utc)
                await db.commit()
            return True

        except Exception as e:
            last_error = str(e)
            if email_log:
                email_log.retry_count = attempt + 1
            if attempt < 2:  # Don't sleep on last attempt
                await asyncio.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s

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
                "content": [{"type": "text/plain", "value": body}]
            }
        )
        response.raise_for_status()


async def _send_smtp(to_email: str, subject: str, body: str) -> None:
    """Send via SMTP."""
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASSWORD]):
        raise ValueError("SMTP not fully configured")

    # Run blocking SMTP in thread pool
    def _send():
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _send)


async def send_email_with_retry(
    to_email: str,
    email_type: str,
    context: dict[str, Any],
    max_retries: int = 3
) -> bool:
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
                await asyncio.sleep(2 ** attempt)
    return False


async def get_failed_emails(db: AsyncSession, hackathon_id: uuid.UUID | None = None) -> list[EmailLog]:
    """Get failed emails for retry (admin function)."""
    query = select(EmailLog).where(EmailLog.status == "failed")
    if hackathon_id:
        query = query.where(EmailLog.hackathon_id == hackathon_id)
    result = await db.execute(query)
    return result.scalars().all()
```

- [ ] **Step 3: Add uuid import**

Add at top of email_service.py:

```python
import uuid
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/email_service.py backend/app/config.py
git commit -m "feat: add email service with retry and logging"
```

---

## Chunk 4: Waitlist Backend Logic

### Task 4: Add Waitlist Functions and Endpoints

**Files:**
- Create: `backend/app/waitlist.py` (waitlist logic module)
- Modify: `backend/app/routes/registrations_organizer.py` (add endpoints)

- [ ] **Step 1: Create waitlist.py with core functions**

```python
"""Waitlist management logic."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Registration, RegistrationStatus, Hackathon, User
from app.email_service import send_email


async def promote_from_waitlist(
    hackathon_id: uuid.UUID,
    db: AsyncSession
) -> Optional[Registration]:
    """
    Promote the top waitlisted registration to 'offered' status.
    Orders by: declined_count ASC (fewer declines = higher priority), then registered_at ASC (FIFO).
    """
    from sqlalchemy import select, func

    # Get top waitlisted (lower declined_count first, then FIFO)
    top_waitlisted = await db.execute(
        select(Registration)
        .where(Registration.hackathon_id == hackathon_id)
        .where(Registration.status == RegistrationStatus.waitlisted)
        .order_by(Registration.declined_count.asc(), Registration.registered_at.asc())
        .limit(1)
    )
    reg = top_waitlisted.scalar_one_or_none()
    if not reg:
        return None

    # Check capacity with row lock
    hackathon_result = await db.execute(
        select(Hackathon)
        .where(Hackathon.id == hackathon_id)
        .with_for_update()
    )
    hackathon = hackathon_result.scalar_one()

    accepted_count = await db.execute(
        select(func.count(Registration.id))
        .where(Registration.hackathon_id == hackathon_id)
        .where(Registration.status == RegistrationStatus.accepted)
    )
    if accepted_count.scalar() >= hackathon.max_participants:
        return None  # No spot available

    # Promote to offered
    now = datetime.now(timezone.utc)
    reg.status = RegistrationStatus.offered
    reg.offered_at = now
    reg.offer_expires_at = now + timedelta(hours=24)
    await db.flush()

    # Send offer email
    user = await db.get(User, reg.user_id)
    if user:
        await send_email(
            to_email=user.email,
            email_type="spot_offered",
            context={
                "name": user.name,
                "hackathon_name": hackathon.name,
                "deadline": reg.offer_expires_at.strftime("%Y-%m-%d %H:%M UTC"),
                "accept_url": f"/dashboard?accept_offer={reg.id}"  # Frontend route
            },
            registration_id=reg.id,
            hackathon_id=hackathon_id,
            db=db
        )

    await db.commit()
    return reg


async def get_waitlist_position(
    registration_id: uuid.UUID,
    hackathon_id: uuid.UUID,
    db: AsyncSession
) -> Optional[int]:
    """Get 1-indexed position of a registration in the waitlist."""
    # Get all waitlisted registrations ordered by priority
    result = await db.execute(
        select(Registration)
        .where(Registration.hackathon_id == hackathon_id)
        .where(Registration.status == RegistrationStatus.waitlisted)
        .order_by(Registration.declined_count.asc(), Registration.registered_at.asc())
    )
    waitlisted = result.scalars().all()

    for idx, reg in enumerate(waitlisted, start=1):
        if reg.id == registration_id:
            return idx
    return None


async def auto_waitlist_if_full(
    hackathon_id: uuid.UUID,
    db: AsyncSession
) -> bool:
    """Check if hackathon is full. Returns True if waitlist should be used."""
    hackathon = await db.get(Hackathon, hackathon_id)
    if not hackathon or not hackathon.max_participants:
        return False

    accepted_count = await db.execute(
        select(func.count(Registration.id))
        .where(Registration.hackathon_id == hackathon_id)
        .where(Registration.status == RegistrationStatus.accepted)
    )
    return accepted_count.scalar() >= hackathon.max_participants
```

- [ ] **Step 2: Add waitlist endpoints to registrations_organizer.py**

Add imports at top:

```python
from app.waitlist import promote_from_waitlist, get_waitlist_position
```

Add after existing endpoints (before line 205):

```python
@router.post("/{hackathon_id}/registrations/{registration_id}/waitlist")
async def move_to_waitlist(
    hackathon_id: uuid.UUID,
    registration_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Move a pending registration to waitlist. Organizer only."""
    user = await _get_organizer(authorization, db)
    hackathon = await _verify_organizer_owns_hackathon(user, hackathon_id, db)

    query = select(Registration).where(
        and_(Registration.id == registration_id, Registration.hackathon_id == hackathon_id)
    )
    result = await db.execute(query)
    reg = result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    if reg.status != RegistrationStatus.pending:
        raise HTTPException(status_code=409, detail=f"Cannot waitlist a {reg.status.value} registration")

    reg.status = RegistrationStatus.waitlisted
    await db.commit()

    return {"id": str(reg.id), "status": reg.status.value}


@router.post("/{hackathon_id}/registrations/{registration_id}/unwaitlist")
async def remove_from_waitlist(
    hackathon_id: uuid.UUID,
    registration_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Move a waitlisted registration back to pending. Organizer only."""
    user = await _get_organizer(authorization, db)
    hackathon = await _verify_organizer_owns_hackathon(user, hackathon_id, db)

    query = select(Registration).where(
        and_(Registration.id == registration_id, Registration.hackathon_id == hackathon_id)
    )
    result = await db.execute(query)
    reg = result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    if reg.status != RegistrationStatus.waitlisted:
        raise HTTPException(status_code=409, detail=f"Cannot unwaitlist a {reg.status.value} registration")

    reg.status = RegistrationStatus.pending
    reg.declined_count = 0
    await db.commit()

    return {"id": str(reg.id), "status": reg.status.value}


@router.post("/{hackathon_id}/waitlist/promote")
async def manual_promote_waitlist(
    hackathon_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Manually promote top waitlisted person to offered. Organizer only."""
    user = await _get_organizer(authorization, db)
    hackathon = await _verify_organizer_owns_hackathon(user, hackathon_id, db)

    promoted = await promote_from_waitlist(hackathon_id, db)
    if not promoted:
        raise HTTPException(status_code=409, detail="No one to promote or hackathon at capacity")

    return {
        "id": str(promoted.id),
        "status": promoted.status.value,
        "offer_expires_at": promoted.offer_expires_at.isoformat()
    }


@router.get("/{hackathon_id}/waitlist")
async def list_waitlist(
    hackathon_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List waitlisted registrations with position. Organizer only."""
    user = await _get_organizer(authorization, db)
    hackathon = await _verify_organizer_owns_hackathon(user, hackathon_id, db)

    # Get waitlist ordered by priority
    result = await db.execute(
        select(Registration)
        .where(Registration.hackathon_id == hackathon_id)
        .where(Registration.status == RegistrationStatus.waitlisted)
        .order_by(Registration.declined_count.asc(), Registration.registered_at.asc())
        .offset(offset).limit(limit)
    )
    registrations = result.scalars().all()

    # Get users
    user_ids = [r.user_id for r in registrations]
    users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
    users = {str(u.id): u for u in users_result.scalars().all()}

    # Calculate positions (1-indexed)
    base_position = offset + 1
    return {
        "waitlist": [
            {
                "id": str(r.id),
                "position": base_position + idx,
                "user_name": users.get(str(r.user_id)).name if str(r.user_id) in users else None,
                "user_email": users.get(str(r.user_id)).email if str(r.user_id) in users else None,
                "registered_at": r.registered_at.isoformat(),
                "declined_count": r.declined_count or 0,
                "dietary_restrictions": r.dietary_restrictions,
                "shirt_size": r.shirt_size,
            }
            for idx, r in enumerate(registrations)
        ],
        "total": len(registrations),
        "offset": offset,
        "limit": limit,
    }
```

- [ ] **Step 3: Modify existing reject endpoint to trigger promotion**

Find the reject endpoint and modify:

```python
@router.post("/{hackathon_id}/registrations/{registration_id}/reject")
async def reject_registration(
    hackathon_id: uuid.UUID,
    registration_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Reject a registration. Organizer only."""
    user = await _get_organizer(authorization, db)
    hackathon = await _verify_organizer_owns_hackathon(user, hackathon_id, db)

    query = select(Registration).where(
        and_(Registration.id == registration_id, Registration.hackathon_id == hackathon_id)
    )
    result = await db.execute(query)
    reg = result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    if reg.status not in (RegistrationStatus.pending, RegistrationStatus.accepted):
        raise HTTPException(status_code=409, detail=f"Cannot reject a {reg.status.value} registration")

    was_accepted = reg.status == RegistrationStatus.accepted
    reg.status = RegistrationStatus.rejected
    reg.qr_token = None

    # If rejecting an accepted registration, promote from waitlist
    if was_accepted:
        await db.flush()
        await promote_from_waitlist(hackathon_id, db)

    await db.commit()

    return {"id": str(reg.id), "status": reg.status.value}
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/waitlist.py backend/app/routes/registrations_organizer.py
git commit -m "feat: add waitlist management endpoints and promotion logic"
```

---

## Chunk 5: Participant Offer Endpoints

### Task 5: Add Participant Offer Acceptance

**Files:**
- Modify: `backend/app/routes/registrations.py`

- [ ] **Step 1: Add accept-offer endpoint**

Add imports:

```python
from sqlalchemy import select, and_
from app.waitlist import promote_from_waitlist
```

Add new endpoint:

```python
@router.post("/{registration_id}/accept-offer")
async def accept_offer(
    registration_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Participant accepts an offered spot from waitlist promotion."""
    # Authenticate
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization.removeprefix("Bearer ")
    payload = decode_token(token)
    user_id = payload.get("sub")

    # Lock registration row to prevent race conditions
    result = await db.execute(
        select(Registration)
        .where(Registration.id == registration_id)
        .where(Registration.user_id == user_id)
        .with_for_update()
    )
    reg = result.scalar_one_or_none()

    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    if reg.status != RegistrationStatus.offered:
        raise HTTPException(status_code=409, detail=f"Cannot accept a {reg.status.value} registration")
    if reg.offer_expires_at and reg.offer_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Offer has expired")

    # Check capacity one more time
    hackathon = await db.get(Hackathon, reg.hackathon_id)
    accepted_count = await db.execute(
        select(func.count(Registration.id))
        .where(Registration.hackathon_id == reg.hackathon_id)
        .where(Registration.status == RegistrationStatus.accepted)
    )

    if accepted_count.scalar() >= hackathon.max_participants:
        # Someone else took the spot
        reg.status = RegistrationStatus.waitlisted
        reg.offer_expires_at = None
        await db.commit()
        raise HTTPException(status_code=409, detail="Spot no longer available")

    # Accept the offer
    reg.status = RegistrationStatus.accepted
    reg.accepted_at = datetime.now(timezone.utc)
    reg.offer_expires_at = None

    # Generate QR token
    from app.auth import create_qr_token
    reg.qr_token = create_qr_token(
        registration_id=str(reg.id),
        user_id=str(reg.user_id),
        hackathon_id=str(reg.hackathon_id),
        hackathon_end=hackathon.end_date,
    )

    await db.commit()

    # Send confirmation email
    user = await db.get(User, reg.user_id)
    if user:
        from app.email_service import send_email
        await send_email(
            to_email=user.email,
            email_type="status_accepted",
            context={
                "name": user.name,
                "hackathon_name": hackathon.name,
                "start_date": hackathon.start_date.strftime("%Y-%m-%d"),
                "end_date": hackathon.end_date.strftime("%Y-%m-%d"),
                "venue": hackathon.venue_address or "TBD",
            },
            registration_id=reg.id,
            hackathon_id=hackathon.id,
            db=db
        )

    return {
        "id": str(reg.id),
        "status": reg.status.value,
        "qr_token": reg.qr_token,
        "accepted_at": reg.accepted_at.isoformat()
    }


@router.post("/{registration_id}/decline-offer")
async def decline_offer(
    registration_id: uuid.UUID,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Participant declines an offered spot. Returns to waitlist with lower priority."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization.removeprefix("Bearer ")
    payload = decode_token(token)
    user_id = payload.get("sub")

    result = await db.execute(
        select(Registration)
        .where(Registration.id == registration_id)
        .where(Registration.user_id == user_id)
    )
    reg = result.scalar_one_or_none()

    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    if reg.status != RegistrationStatus.offered:
        raise HTTPException(status_code=409, detail=f"Cannot decline a {reg.status.value} registration")

    # Decline - return to waitlist with incremented declined_count
    reg.status = RegistrationStatus.waitlisted
    reg.offer_expires_at = None
    reg.declined_count = (reg.declined_count or 0) + 1

    # Trigger promotion of next person
    await db.flush()
    await promote_from_waitlist(reg.hackathon_id, db)

    await db.commit()

    return {"id": str(reg.id), "status": reg.status.value, "declined_count": reg.declined_count}
```

- [ ] **Step 2: Update registration creation to use auto-waitlist**

Find the registration creation endpoint and modify the status assignment:

```python
from app.waitlist import auto_waitlist_if_full

# In the register endpoint, when creating registration:
# Check if should auto-waitlist
should_waitlist = await auto_waitlist_if_full(hackathon_id, db)
if should_waitlist:
    reg.status = RegistrationStatus.waitlisted
else:
    reg.status = RegistrationStatus.pending

# ... after commit, if waitlisted, calculate and return position
if reg.status == RegistrationStatus.waitlisted:
    from app.waitlist import get_waitlist_position
    position = await get_waitlist_position(reg.id, hackathon_id, db)
    response["waitlist_info"] = {"estimated_position": position}
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/routes/registrations.py
git commit -m "feat: add participant offer accept/decline endpoints"
```

---

## Chunk 6: Background Jobs

### Task 6: Create Background Job Scheduler

**Files:**
- Create: `backend/app/background_jobs.py`
- Modify: `backend/app/main.py` (add scheduler startup)

- [ ] **Step 1: Create background_jobs.py**

```python
"""Background jobs for waitlist cleanup and event reminders."""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models import Registration, RegistrationStatus, Hackathon
from app.waitlist import promote_from_waitlist
from app.email_service import send_email_with_retry
from app.discord_bot import send_discord_webhook  # For admin alerts

scheduler = AsyncIOScheduler()


async def cleanup_expired_offers():
    """Run every 5 minutes. Expire old offers and promote next waitlisted."""
    async with async_session() as db:
        try:
            now = datetime.now(timezone.utc)

            # Find expired offers
            result = await db.execute(
                select(Registration)
                .where(Registration.status == RegistrationStatus.offered)
                .where(Registration.offer_expires_at < now)
                .order_by(Registration.offer_expires_at.asc())
            )
            expired_list = result.scalars().all()

            processed_hackathons = set()

            for reg in expired_list:
                # Return to waitlist with lower priority
                reg.status = RegistrationStatus.waitlisted
                reg.offer_expires_at = None
                reg.declined_count = (reg.declined_count or 0) + 1

                # Only promote once per hackathon per run
                if reg.hackathon_id not in processed_hackathons:
                    processed_hackathons.add(reg.hackathon_id)
                    await db.flush()
                    await promote_from_waitlist(reg.hackathon_id, db)

            await db.commit()

        except Exception as e:
            # Log error but don't crash scheduler
            print(f"Error in cleanup_expired_offers: {e}")


async def send_event_reminders():
    """Run daily at 9am. Send reminder emails for events starting tomorrow."""
    async with async_session() as db:
        try:
            tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
            tomorrow_start = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow_end = tomorrow.replace(hour=23, minute=59, second=59)

            # Find hackathons starting tomorrow
            result = await db.execute(
                select(Hackathon)
                .where(Hackathon.start_date >= tomorrow_start)
                .where(Hackathon.start_date <= tomorrow_end)
            )
            hackathons = result.scalars().all()

            for hackathon in hackathons:
                # Get accepted participants
                regs_result = await db.execute(
                    select(Registration)
                    .where(Registration.hackathon_id == hackathon.id)
                    .where(Registration.status == RegistrationStatus.accepted)
                )
                registrations = regs_result.scalars().all()

                for reg in registrations:
                    # Load user
                    from app.models import User
                    user = await db.get(User, reg.user_id)
                    if not user:
                        continue

                    # Send reminder
                    await send_email_with_retry(
                        to_email=user.email,
                        email_type="event_reminder",
                        context={
                            "name": user.name,
                            "hackathon_name": hackathon.name,
                            "start_date": hackathon.start_date.strftime("%A, %B %d"),
                            "checkin_time": "8:00 AM",  # Configurable
                        }
                    )

        except Exception as e:
            print(f"Error in send_event_reminders: {e}")


def start_scheduler():
    """Start background job scheduler."""
    # Cleanup expired offers every 5 minutes
    scheduler.add_job(
        cleanup_expired_offers,
        IntervalTrigger(minutes=5),
        id="cleanup_expired_offers",
        replace_existing=True
    )

    # Event reminders daily at 9am
    scheduler.add_job(
        send_event_reminders,
        CronTrigger(hour=9, minute=0),
        id="send_event_reminders",
        replace_existing=True
    )

    scheduler.start()
    print("Background scheduler started")


def shutdown_scheduler():
    """Shutdown scheduler gracefully."""
    scheduler.shutdown()
    print("Background scheduler stopped")
```

- [ ] **Step 2: Add apscheduler to requirements**

Add to `backend/requirements.txt`:

```
apscheduler>=3.10.0
```

- [ ] **Step 3: Update main.py to start scheduler**

Add imports:

```python
from app.background_jobs import start_scheduler, shutdown_scheduler
```

Add startup/shutdown events:

```python
@app.on_event("startup")
async def startup_event():
    start_scheduler()

@app.on_event("shutdown")
async def shutdown_event():
    shutdown_scheduler()
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/background_jobs.py backend/app/main.py backend/requirements.txt
git commit -m "feat: add background jobs for waitlist cleanup and event reminders"
```

---

## Chunk 7: Bulk Seed Script

### Task 7: Create Demo Data Generator

**Files:**
- Create: `backend/scripts/bulk_seed.py`

- [ ] **Step 1: Create bulk_seed.py**

```python
"""Generate realistic demo registration data."""
import asyncio
import uuid
import random
import argparse
from datetime import datetime, timezone, timedelta
from faker import Faker
from sqlalchemy import select

# Add parent to path
import sys
sys.path.insert(0, "/Users/justi/dev/rowdyhacks/backend")

from app.database import async_session
from app.models import (
    User, Hackathon, Registration, RegistrationStatus, UserRole,
    Track
)
from app.auth import hash_password

fake = Faker()

# Sample data
DIETARY_OPTIONS = [None, "vegetarian", "vegan", "gluten-free", "halal", "kosher", "nut allergy"]
SHIRT_SIZES = ["XS", "S", "M", "L", "XL", "XXL"]
EXPERIENCE_LEVELS = ["beginner", "intermediate", "advanced"]
TEAM_NAMES = [
    "Code Wizards", "Binary Builders", "Stack Overflowers", "Git Pushers",
    "Null Pointers", "Runtime Errors", "Syntax Squad", "Debuggers",
    "Bit Shifters", "Algorithm Aces", "Data Driven", "Cloud Ninjas",
    "API Architects", "Frontend Fanatics", "Backend Bandits"
]


async def create_demo_users(db, count: int) -> list[User]:
    """Create demo participant users."""
    users = []
    for i in range(count):
        user = User(
            id=uuid.uuid4(),
            email=f"demo{i+1}@example.com",
            name=fake.name(),
            password_hash=hash_password("demo12345"),
            role=UserRole.participant,
        )
        db.add(user)
        users.append(user)
    await db.flush()
    return users


async def create_registrations(
    db,
    hackathon_id: uuid.UUID,
    users: list[User],
    target_count: int = 50
) -> list[Registration]:
    """Create registrations with varied statuses."""
    registrations = []

    # Status distribution
    status_weights = [
        (RegistrationStatus.pending, 0.2),
        (RegistrationStatus.accepted, 0.3),
        (RegistrationStatus.waitlisted, 0.25),
        (RegistrationStatus.rejected, 0.1),
        (RegistrationStatus.offered, 0.05),
        (RegistrationStatus.checked_in, 0.1),
    ]

    for i, user in enumerate(users[:target_count]):
        # Weighted random status
        status = random.choices(
            [s for s, _ in status_weights],
            weights=[w for _, w in status_weights]
        )[0]

        # Registration time within last 30 days
        days_ago = random.randint(0, 30)
        registered_at = datetime.now(timezone.utc) - timedelta(days=days_ago)

        # Build registration
        reg = Registration(
            id=uuid.uuid4(),
            hackathon_id=hackathon_id,
            user_id=user.id,
            status=status,
            team_name=random.choice(TEAM_NAMES) if random.random() > 0.3 else None,
            team_members=[fake.first_name() for _ in range(random.randint(0, 4))] if random.random() > 0.5 else [],
            registered_at=registered_at,
            # New fields
            dietary_restrictions=random.choice(DIETARY_OPTIONS),
            shirt_size=random.choice(SHIRT_SIZES),
            special_needs=random.choice([None, None, None, "Wheelchair accessible", "Hearing assistance"]),
            experience_level=random.choice(EXPERIENCE_LEVELS),
            school_company=fake.company() if random.random() > 0.3 else fake.university(),
            graduation_year=random.choice([None, 2026, 2027, 2028]) if random.random() > 0.4 else None,
        )

        # Status-specific timestamps
        if status in (RegistrationStatus.accepted, RegistrationStatus.checked_in, RegistrationStatus.offered):
            reg.accepted_at = registered_at + timedelta(days=random.randint(1, 5))

        if status == RegistrationStatus.offered:
            reg.offered_at = datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 20))
            reg.offer_expires_at = reg.offered_at + timedelta(hours=24)

        if status == RegistrationStatus.checked_in:
            reg.checked_in_at = datetime.now(timezone.utc) - timedelta(days=random.randint(0, 2))

        if status == RegistrationStatus.waitlisted and random.random() > 0.7:
            reg.declined_count = random.randint(1, 2)  # Some have declined before

        db.add(reg)
        registrations.append(reg)

    await db.commit()
    return registrations


async def seed_hackathon(hackathon_id: str, count: int = 50):
    """Seed demo data for a specific hackathon."""
    hackathon_uuid = uuid.UUID(hackathon_id)

    async with async_session() as db:
        # Verify hackathon exists
        hackathon = await db.get(Hackathon, hackathon_uuid)
        if not hackathon:
            print(f"Hackathon {hackathon_id} not found!")
            return

        # Check if already seeded
        result = await db.execute(
            select(Registration).where(Registration.hackathon_id == hackathon_uuid)
        )
        existing = result.scalars().all()
        if existing:
            print(f"Hackathon already has {len(existing)} registrations. Skipping.")
            return

        # Create users
        print(f"Creating {count} demo users...")
        users = await create_demo_users(db, count)

        # Create registrations
        print(f"Creating {count} registrations...")
        regs = await create_registrations(db, hackathon_uuid, users, count)

        # Print summary
        status_counts = {}
        for r in regs:
            status_counts[r.status.value] = status_counts.get(r.status.value, 0) + 1

        print(f"\nSeeded {count} registrations for '{hackathon.name}':")
        for status, count in sorted(status_counts.items()):
            print(f"  {status}: {count}")

        # Update hackathon participant count
        accepted_count = status_counts.get("accepted", 0) + status_counts.get("checked_in", 0)
        hackathon.current_participants = accepted_count
        await db.commit()

        print(f"\nUpdated hackathon.current_participants = {accepted_count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed demo registration data")
    parser.add_argument("--hackathon-id", required=True, help="Hackathon UUID to seed")
    parser.add_argument("--count", type=int, default=50, help="Number of registrations to create")
    args = parser.parse_args()

    asyncio.run(seed_hackathon(args.hackathon_id, args.count))
```

- [ ] **Step 2: Add faker to requirements**

```bash
echo "faker>=22.0.0" >> backend/requirements.txt
```

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/bulk_seed.py backend/requirements.txt
git commit -m "feat: add bulk seed script for demo registration data"
```

---

## Chunk 8: Frontend Types and API

### Task 8: Update Frontend Types and Services

**Files:**
- Modify: `frontend/src/types/registration.ts` (if exists) or create types
- Modify: `frontend/src/services/api.ts`

- [ ] **Step 1: Update or create registration types**

```typescript
// frontend/src/types/registration.ts

export interface Registration {
  id: string;
  hackathon_id: string;
  user_id: string;
  status: 'pending' | 'accepted' | 'rejected' | 'waitlisted' | 'offered' | 'checked_in';
  team_name: string | null;
  team_members: string[];
  registered_at: string;
  accepted_at: string | null;
  checked_in_at: string | null;
  offered_at?: string | null;
  offer_expires_at?: string | null;
  declined_count?: number;
  // New fields
  dietary_restrictions: string | null;
  shirt_size: string | null;
  special_needs: string | null;
  experience_level: string | null;
  school_company: string | null;
  graduation_year: number | null;
  // Joined fields
  user_name?: string;
  user_email?: string;
}

export interface WaitlistEntry {
  id: string;
  position: number;
  user_name: string | null;
  user_email: string | null;
  registered_at: string;
  declined_count: number;
  dietary_restrictions: string | null;
  shirt_size: string | null;
}

export interface WaitlistResponse {
  waitlist: WaitlistEntry[];
  total: number;
  offset: number;
  limit: number;
}
```

- [ ] **Step 2: Add API methods to services/api.ts**

```typescript
// Add to api.ts

// Waitlist endpoints (organizer)
export async function getWaitlist(
  hackathonId: string,
  offset: number = 0,
  limit: number = 50
): Promise<WaitlistResponse> {
  const token = localStorage.getItem('token');
  const response = await fetch(
    `${API_BASE}/hackathons/${hackathonId}/waitlist?offset=${offset}&limit=${limit}`,
    {
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );
  if (!response.ok) throw new Error('Failed to fetch waitlist');
  return response.json();
}

export async function moveToWaitlist(
  hackathonId: string,
  registrationId: string
): Promise<{ id: string; status: string }> {
  const token = localStorage.getItem('token');
  const response = await fetch(
    `${API_BASE}/hackathons/${hackathonId}/registrations/${registrationId}/waitlist`,
    {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );
  if (!response.ok) throw new Error('Failed to move to waitlist');
  return response.json();
}

export async function removeFromWaitlist(
  hackathonId: string,
  registrationId: string
): Promise<{ id: string; status: string }> {
  const token = localStorage.getItem('token');
  const response = await fetch(
    `${API_BASE}/hackathons/${hackathonId}/registrations/${registrationId}/unwaitlist`,
    {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );
  if (!response.ok) throw new Error('Failed to remove from waitlist');
  return response.json();
}

export async function promoteFromWaitlist(
  hackathonId: string
): Promise<{ id: string; status: string; offer_expires_at: string }> {
  const token = localStorage.getItem('token');
  const response = await fetch(
    `${API_BASE}/hackathons/${hackathonId}/waitlist/promote`,
    {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );
  if (!response.ok) throw new Error('Failed to promote from waitlist');
  return response.json();
}

// Participant offer endpoints
export async function acceptOffer(
  registrationId: string
): Promise<{ id: string; status: string; qr_token: string; accepted_at: string }> {
  const token = localStorage.getItem('token');
  const response = await fetch(
    `${API_BASE}/registrations/${registrationId}/accept-offer`,
    {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );
  if (!response.ok) throw new Error('Failed to accept offer');
  return response.json();
}

export async function declineOffer(
  registrationId: string
): Promise<{ id: string; status: string; declined_count: number }> {
  const token = localStorage.getItem('token');
  const response = await fetch(
    `${API_BASE}/registrations/${registrationId}/decline-offer`,
    {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );
  if (!response.ok) throw new Error('Failed to decline offer');
  return response.json();
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/registration.ts frontend/src/services/api.ts
git commit -m "feat: add waitlist types and API methods"
```

---

## Chunk 9: Frontend Waitlist Components

### Task 9: Create Waitlist UI Components

**Files:**
- Create: `frontend/src/components/WaitlistManager.tsx`
- Create: `frontend/src/components/WaitlistPosition.tsx`
- Create: `frontend/src/components/OfferBanner.tsx`

- [ ] **Step 1: Create WaitlistManager.tsx**

```tsx
// frontend/src/components/WaitlistManager.tsx
import { useState, useEffect } from 'react';
import {
  Box,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Button,
  Badge,
  Text,
  Flex,
  useToast,
  Spinner,
  HStack,
  VStack,
} from '@chakra-ui/react';
import { ArrowUpIcon } from '@chakra-ui/icons';
import { WaitlistEntry } from '../types/registration';
import { getWaitlist, promoteFromWaitlist } from '../services/api';

interface WaitlistManagerProps {
  hackathonId: string;
}

export function WaitlistManager({ hackathonId }: WaitlistManagerProps) {
  const [waitlist, setWaitlist] = useState<WaitlistEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [promoting, setPromoting] = useState(false);
  const toast = useToast();

  useEffect(() => {
    loadWaitlist();
  }, [hackathonId]);

  async function loadWaitlist() {
    try {
      const data = await getWaitlist(hackathonId);
      setWaitlist(data.waitlist);
    } catch (error) {
      toast({
        title: 'Error loading waitlist',
        status: 'error',
        duration: 3000,
      });
    } finally {
      setLoading(false);
    }
  }

  async function handlePromote() {
    setPromoting(true);
    try {
      const result = await promoteFromWaitlist(hackathonId);
      toast({
        title: 'Offer sent!',
        description: `Promoted position #1 (expires ${new Date(result.offer_expires_at).toLocaleString()})`,
        status: 'success',
        duration: 5000,
      });
      loadWaitlist(); // Refresh
    } catch (error) {
      toast({
        title: 'Failed to promote',
        description: error instanceof Error ? error.message : 'Unknown error',
        status: 'error',
        duration: 3000,
      });
    } finally {
      setPromoting(false);
    }
  }

  if (loading) return <Spinner />;

  return (
    <Box>
      <Flex justify="space-between" align="center" mb={4}>
        <VStack align="start" spacing={1}>
          <Text fontSize="lg" fontWeight="bold">
            Waitlist ({waitlist.length} people)
          </Text>
          <Text fontSize="sm" color="gray.600">
            First in line gets the next available spot
          </Text>
        </VStack>
        <Button
          leftIcon={<ArrowUpIcon />}
          colorScheme="blue"
          onClick={handlePromote}
          isLoading={promoting}
          isDisabled={waitlist.length === 0}
        >
          Promote #1 to Offered
        </Button>
      </Flex>

      {waitlist.length === 0 ? (
        <Text color="gray.500" textAlign="center" py={8}>
          Waitlist is empty
        </Text>
      ) : (
        <Table size="sm">
          <Thead>
            <Tr>
              <Th>Position</Th>
              <Th>Name</Th>
              <Th>Email</Th>
              <Th>Registered</Th>
              <Th>Shirt Size</Th>
              <Th>Declines</Th>
            </Tr>
          </Thead>
          <Tbody>
            {waitlist.map((entry) => (
              <Tr key={entry.id}>
                <Td>
                  <Badge colorScheme={entry.position === 1 ? 'green' : 'gray'}>
                    #{entry.position}
                  </Badge>
                </Td>
                <Td fontWeight="medium">{entry.user_name}</Td>
                <Td fontSize="sm">{entry.user_email}</Td>
                <Td fontSize="sm">
                  {new Date(entry.registered_at).toLocaleDateString()}
                </Td>
                <Td>{entry.shirt_size || '-'}</Td>
                <Td>
                  {entry.declined_count > 0 && (
                    <Badge colorScheme="orange">{entry.declined_count}</Badge>
                  )}
                </Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      )}
    </Box>
  );
}
```

- [ ] **Step 2: Create WaitlistPosition.tsx**

```tsx
// frontend/src/components/WaitlistPosition.tsx
import { Box, Text, Badge, HStack, VStack, Progress } from '@chakra-ui/react';

interface WaitlistPositionProps {
  position: number;
  totalWaitlist?: number;
}

export function WaitlistPosition({ position, totalWaitlist }: WaitlistPositionProps) {
  // Calculate progress (inverse - lower position is better)
  const progress = totalWaitlist ? Math.max(0, 100 - (position / totalWaitlist) * 100) : 50;

  return (
    <Box
      p={4}
      bg="orange.50"
      borderRadius="md"
      borderWidth={1}
      borderColor="orange.200"
    >
      <VStack align="stretch" spacing={3}>
        <HStack justify="space-between">
          <Text fontSize="sm" color="orange.800" fontWeight="medium">
            Waitlist Status
          </Text>
          <Badge colorScheme="orange">#{position} in line</Badge>
        </HStack>

        <Progress value={progress} colorScheme="orange" size="sm" borderRadius="full" />

        <Text fontSize="sm" color="gray.600">
          {position === 1
            ? "You're first in line! You'll get the next available spot."
            : position <= 5
            ? `You're in the top ${position} spots. A spot may open up soon!`
            : `There are ${position - 1} people ahead of you. We'll notify you if a spot opens.`}
        </Text>
      </VStack>
    </Box>
  );
}
```

- [ ] **Step 3: Create OfferBanner.tsx**

```tsx
// frontend/src/components/OfferBanner.tsx
import { useState, useEffect } from 'react';
import {
  Box,
  Text,
  Button,
  HStack,
  VStack,
  useToast,
  Badge,
  Alert,
  AlertIcon,
} from '@chakra-ui/react';
import { acceptOffer, declineOffer } from '../services/api';

interface OfferBannerProps {
  registrationId: string;
  offerExpiresAt: string;
  hackathonName: string;
  onStatusChange: () => void;
}

export function OfferBanner({
  registrationId,
  offerExpiresAt,
  hackathonName,
  onStatusChange,
}: OfferBannerProps) {
  const [timeLeft, setTimeLeft] = useState('');
  const [loading, setLoading] = useState(false);
  const [expired, setExpired] = useState(false);
  const toast = useToast();

  useEffect(() => {
    const updateTimer = () => {
      const now = new Date().getTime();
      const expires = new Date(offerExpiresAt).getTime();
      const diff = expires - now;

      if (diff <= 0) {
        setTimeLeft('Expired');
        setExpired(true);
        return;
      }

      const hours = Math.floor(diff / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      setTimeLeft(`${hours}h ${minutes}m`);
    };

    updateTimer();
    const interval = setInterval(updateTimer, 60000); // Update every minute

    return () => clearInterval(interval);
  }, [offerExpiresAt]);

  async function handleAccept() {
    setLoading(true);
    try {
      await acceptOffer(registrationId);
      toast({
        title: "You're in!",
        description: `You've been accepted to ${hackathonName}`,
        status: 'success',
        duration: 5000,
      });
      onStatusChange();
    } catch (error) {
      toast({
        title: 'Failed to accept',
        description: error instanceof Error ? error.message : 'Spot may no longer be available',
        status: 'error',
        duration: 3000,
      });
    } finally {
      setLoading(false);
    }
  }

  async function handleDecline() {
    setLoading(true);
    try {
      await declineOffer(registrationId);
      toast({
        title: 'Offer declined',
        description: 'You\'ve been returned to the waitlist',
        status: 'info',
        duration: 3000,
      });
      onStatusChange();
    } catch (error) {
      toast({
        title: 'Failed to decline',
        status: 'error',
        duration: 3000,
      });
    } finally {
      setLoading(false);
    }
  }

  if (expired) {
    return (
      <Alert status="warning" borderRadius="md">
        <AlertIcon />
        <Text>This offer has expired. You've been returned to the waitlist.</Text>
      </Alert>
    );
  }

  return (
    <Box
      p={5}
      bg="green.50"
      borderRadius="md"
      borderWidth={2}
      borderColor="green.300"
    >
      <VStack align="stretch" spacing={4}>
        <HStack justify="space-between">
          <Box>
            <Text fontSize="lg" fontWeight="bold" color="green.800">
              Spot Available: {hackathonName}
            </Text>
            <Text fontSize="sm" color="gray.600">
              A spot opened up and you're next on the waitlist!
            </Text>
          </Box>
          <Badge colorScheme="red" fontSize="md" px={3} py={1}>
            Expires in: {timeLeft}
          </Badge>
        </HStack>

        <Alert status="info" borderRadius="md">
          <AlertIcon />
          <Text fontSize="sm">
            You have 24 hours to accept this offer. If you don't respond, the spot will be offered to the next person.
          </Text>
        </Alert>

        <HStack spacing={3}>
          <Button
            colorScheme="green"
            size="lg"
            flex={1}
            onClick={handleAccept}
            isLoading={loading}
          >
            Accept Spot
          </Button>
          <Button
            variant="outline"
            size="lg"
            onClick={handleDecline}
            isLoading={loading}
            isDisabled={loading}
          >
            Decline
          </Button>
        </HStack>
      </VStack>
    </Box>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/WaitlistManager.tsx frontend/src/components/WaitlistPosition.tsx frontend/src/components/OfferBanner.tsx
git commit -m "feat: add waitlist UI components"
```

---

## Chunk 10: Frontend Wizard Updates

### Task 10: Update Application Wizard with New Fields

**Files:**
- Modify: `frontend/src/components/wizard/WizardLogistics.tsx`
- Modify: `frontend/src/components/wizard/WizardReview.tsx`

- [ ] **Step 1: Update WizardLogistics.tsx**

Add new fields after existing logistics questions:

```tsx
// Add to WizardLogistics.tsx

import {
  // ... existing imports
  Select,
  Textarea,
} from '@chakra-ui/react';

// Add to form state
const [dietaryRestrictions, setDietaryRestrictions] = useState('');
const [shirtSize, setShirtSize] = useState('');
const [specialNeeds, setSpecialNeeds] = useState('');

// Add form fields in render:

<FormControl>
  <FormLabel>T-Shirt Size</FormLabel>
  <Select
    value={shirtSize}
    onChange={(e) => setShirtSize(e.target.value)}
    placeholder="Select size"
  >
    <option value="XS">XS</option>
    <option value="S">S</option>
    <option value="M">M</option>
    <option value="L">L</option>
    <option value="XL">XL</option>
    <option value="XXL">XXL</option>
  </Select>
  <FormHelperText>For event swag</FormHelperText>
</FormControl>

<FormControl>
  <FormLabel>Dietary Restrictions</FormLabel>
  <Select
    value={dietaryRestrictions}
    onChange={(e) => setDietaryRestrictions(e.target.value)}
    placeholder="Select if applicable"
  >
    <option value="">None</option>
    <option value="vegetarian">Vegetarian</option>
    <option value="vegan">Vegan</option>
    <option value="gluten-free">Gluten-free</option>
    <option value="halal">Halal</option>
    <option value="kosher">Kosher</option>
    <option value="nut-allergy">Nut Allergy</option>
  </Select>
  <FormHelperText>For catering purposes</FormHelperText>
</FormControl>

<FormControl>
  <FormLabel>Accessibility / Special Needs</FormLabel>
  <Textarea
    value={specialNeeds}
    onChange={(e) => setSpecialNeeds(e.target.value)}
    placeholder="Any accessibility requirements we should know about?"
    rows={2}
  />
  <FormHelperText>Optional - helps us accommodate everyone</FormHelperText>
</FormControl>
```

- [ ] **Step 2: Update WizardReview.tsx**

Add new fields to review summary:

```tsx
// In review section, add:

<ReviewItem label="T-Shirt Size" value={data.shirtSize || 'Not specified'} />
<ReviewItem label="Dietary" value={data.dietaryRestrictions || 'None'} />
{data.specialNeeds && <ReviewItem label="Special Needs" value={data.specialNeeds} />}
```

- [ ] **Step 3: Update types and submit handler**

Update the wizard types and ensure new fields are included in the submit payload.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/wizard/
git commit -m "feat: add registration fields to application wizard"
```

---

## Chunk 11: Integration & Organizer Dashboard Updates

### Task 11: Update Organizer Dashboard

**Files:**
- Modify: `frontend/src/pages/OrganizerRegistrationsPage.tsx`

- [ ] **Step 1: Add waitlist tab to organizer dashboard**

```tsx
// In OrganizerRegistrationsPage.tsx

import { WaitlistManager } from '../components/WaitlistManager';

// Add to tabs:
<Tabs>
  <TabList>
    <Tab>All ({totalCount})</Tab>
    <Tab>Pending ({pendingCount})</Tab>
    <Tab>Accepted ({acceptedCount})</Tab>
    <Tab>Waitlist ({waitlistCount})</Tab>  {/* NEW */}
    <Tab>Checked In ({checkedInCount})</Tab>
  </TabList>

  <TabPanels>
    {/* ... existing panels ... */}

    <TabPanel>
      <WaitlistManager hackathonId={hackathonId} />
    </TabPanel>
  </TabPanels>
</Tabs>
```

- [ ] **Step 2: Add new columns to registration table**

Add columns for shirt_size and dietary_restrictions in the table view (optional display).

- [ ] **Step 3: Add waitlist action button**

Add "Move to Waitlist" button in registration detail actions for pending registrations.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/OrganizerRegistrationsPage.tsx
git commit -m "feat: add waitlist tab to organizer dashboard"
```

---

## Chunk 12: Testing & Final Integration

### Task 12: Test and Verify

- [ ] **Step 1: Run backend tests**

```bash
cd backend
pytest tests/ -v
```

- [ ] **Step 2: Test waitlist flow manually**

1. Create hackathon with max_participants = 2
2. Register 3 users
3. Verify 3rd user is auto-waitlisted
4. As organizer, reject an accepted user
5. Verify waitlist promotion and email sent
6. As waitlisted user, accept offer
7. Verify QR token generated

- [ ] **Step 3: Run seed script**

```bash
cd backend
python scripts/bulk_seed.py --hackathon-id <your-hackathon-uuid> --count 50
```

- [ ] **Step 4: Build frontend**

```bash
cd frontend
npm run build
```

- [ ] **Step 5: Final commit**

```bash
git commit -m "feat: complete waitlist, email, and registration data implementation"
```

---

## Execution Path

After this plan is approved, use **superpowers:subagent-driven-development** to execute tasks in order:

1. Chunk 1-3: Database + Email service
2. Chunk 4-5: Waitlist backend logic
3. Chunk 6: Background jobs
4. Chunk 7: Seed script
5. Chunk 8-11: Frontend implementation
6. Chunk 12: Testing

---

**Plan complete and saved to `docs/superpowers/plans/2026-05-03-waitlist-email-registration.md`. Ready to execute?**
