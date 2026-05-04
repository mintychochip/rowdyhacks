# Design Specification: Waitlist, Email & Registration Data

**Date:** 2026-05-03
**Project:** Hack the Valley Hackathon Platform
**Scope:** Waitlist management, email notifications, enhanced registration data

---

## 1. Overview

### Goals
1. Implement complete waitlist system with auto-waitlisting, manual controls, and promotion
2. Add email notifications for status changes and event reminders
3. Enhance registration data collection with common hackathon fields
4. Create bulk data generation for demo/seed purposes

### Success Criteria
- Organizer can view waitlist and manually manage it
- System auto-waitlists when max capacity reached
- Emails sent for all status changes
- Additional registration fields stored and displayed

---

## 2. Architecture

### Waitlist System

```
┌─────────────────────────────────────────────────────────────────┐
│                    WAITLIST STATE MACHINE                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────auto/full──────────┐                               │
│   │                            ▼                                │
│   │   pending ───────> waitlisted ──spot opens──> offered       │
│   │      │                 │    ▲                   │          │
│   │      │                 │    └───────────────────┘          │
│   │   manual/reject    decline                                  │
│   │   (organizer)      (24hr timeout or manual decline)         │
│   │                                                             │
│   └───promote next─────┘                                      │
│                                                                 │
│   offered ──24hr timeout──> expired                             │
│      │                         │                                │
│      ├──accept──> accepted     └──auto──> waitlisted            │
│      │                                          │               │
│      └──decline──> waitlisted (lower priority)──┘               │
│                                                                 │
│  Legend:
│  ───> = state transition    ────┐ = automatic trigger
│  ───────> = manual action
└─────────────────────────────────────────────────────────────────┘
```

**New RegistrationStatus values:**
- `offered` - Spot available, waiting for participant response (24hr timeout)

**Note on `expired`:** This is not a stored status. When an offer expires, the registration immediately transitions back to `waitlisted` status with incremented `declined_count`.

**Auto-waitlist logic:**
- Trigger: Registration submitted AND hackathon.current_participants >= hackathon.max_participants
- Waitlist is ordered by `registered_at` timestamp (FIFO)

**Promotion logic:**
- Trigger: Rejection of accepted participant OR cancellation
- Action: Top waitlisted participant gets `offered` status
- Background job checks every 5 minutes for expired offers

**promote_from_waitlist() function:**
```python
async def promote_from_waitlist(hackathon_id: uuid.UUID, db: AsyncSession) -> Registration | None:
    """
    Promote the top waitlisted registration to 'offered' status.
    Returns the promoted registration or None if no waitlisted registrations.
    Orders by: declined_count ASC (fewer declines = higher priority), then registered_at ASC (FIFO).
    """
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

    # Check capacity still available (use row lock to prevent race conditions)
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

    # Promote to offered (use database server time for consistency)
    now = await db.execute(select(func.now()))
    reg.status = RegistrationStatus.offered
    reg.offered_at = now.scalar()
    reg.offer_expires_at = reg.offered_at + timedelta(hours=24)
    await db.flush()

    # Send offer email (async, with retry)
    try:
        await send_email_with_retry(reg.user.email, "spot_offered", {"registration": reg, "hackathon": hackathon})
    except Exception as e:
        # Log failure but don't block - spot is already offered
        await log_email_failure(reg.id, "spot_offered", str(e))
        # Alert admin if repeated failures
        await alert_admin_on_email_failure(hackathon_id, str(e))

    await db.commit()
    return reg
```

### Email System

**Architecture:**
```
┌─────────────┐     ┌─────────────────┐
│  Status     │────>│  Email Service  │
│  Change     │     │  (with retry)   │
└─────────────┘     └─────────────────┘
                          │
                          ▼
                    ┌─────────────┐
                    │ SendGrid/   │
                    │ SMTP        │
                    └─────────────┘
```

**Implementation:** Direct async email sending with 3-attempt retry logic. No persistent queue needed for MVP. Failed sends are logged to database `email_logs` table for manual retry by admin.

**Email types:**
1. `application_received` - Confirmation to participant
2. `status_accepted` - Accepted with QR code info
3. `status_waitlisted` - Waitlisted with position
4. `status_rejected` - Rejected with polite message
5. `spot_offered` - Waitlist promotion (24hr to accept)
6. `event_reminder` - 24hr before event start

**Configuration:**
- Environment variables: `EMAIL_PROVIDER` (sendgrid/smtp), `SENDGRID_API_KEY`, `SMTP_*` settings
- Hackathon-level: custom email templates (optional, future)

### Enhanced Registration Data

**New fields on Registration model:**
```python
dietary_restrictions: str | None  # "vegetarian", "vegan", "gluten-free", etc.
shirt_size: str | None           # "XS", "S", "M", "L", "XL", "XXL"
special_needs: str | None        # Accessibility requirements
experience_level: str | None      # "beginner", "intermediate", "advanced"
school_company: str | None       # Institution or employer
graduation_year: int | None      # For students
```

**UI Flow:**
1. Application wizard collects new fields (optional inputs)
2. Organizer dashboard displays in registration detail view
3. CSV export includes all fields

---

## 3. API Changes

### New Endpoints

**Waitlist Management:**
```
POST /api/hackathons/{id}/registrations/{reg_id}/waitlist
  - Organizer moves registration to waitlist

POST /api/hackathons/{id}/registrations/{reg_id}/unwaitlist
  - Remove from waitlist (back to pending)

POST /api/hackathons/{id}/waitlist/promote
  - Manually promote top waitlisted to offered

GET /api/hackathons/{id}/waitlist
  - List waitlisted registrations with position
  - Position is 1-indexed (1 = first in line, next to be promoted)
  - Position calculated dynamically using same ordering as promotion: `ORDER BY declined_count ASC, registered_at ASC`

POST /api/registrations/{id}/accept-offer
  - Participant accepts offered spot
  - Race condition handling: Uses database row-level lock (SELECT FOR UPDATE)
  - If spot was taken by another concurrent request, returns 409 with "Spot no longer available"

POST /api/registrations/{id}/decline-offer
  - Participant declines offered spot (returns to waitlist, marked as lower priority)
```

**Email Testing:**
```
POST /api/hackathons/{id}/test-email
  - Send test email to organizer (verify config)
```

### Modified Endpoints

**Registration creation:**
```
POST /api/hackathons/{id}/register
  - Body now includes: dietary_restrictions, shirt_size, special_needs, etc.
  - Response: if waitlisted, includes "waitlist_info" object with "estimated_position" (calculated dynamically)
```

**List registrations:**
```
GET /api/hackathons/{id}/registrations
  - Response includes new fields: dietary_restrictions, shirt_size, etc.
  - Status filter now supports: "offered", "expired"
```

---

## 4. Database Schema

### Migration: Add columns to registrations table
```sql
ALTER TABLE registrations ADD COLUMN offered_at TIMESTAMP;
ALTER TABLE registrations ADD COLUMN offer_expires_at TIMESTAMP;
CREATE INDEX idx_registrations_waitlist ON registrations(hackathon_id, status, declined_count, registered_at) WHERE status = 'waitlisted';
ALTER TABLE registrations ADD COLUMN dietary_restrictions TEXT;
ALTER TABLE registrations ADD COLUMN shirt_size VARCHAR(10);
ALTER TABLE registrations ADD COLUMN special_needs TEXT;
ALTER TABLE registrations ADD COLUMN experience_level VARCHAR(50);
ALTER TABLE registrations ADD COLUMN school_company TEXT;
ALTER TABLE registrations ADD COLUMN graduation_year INTEGER;
ALTER TABLE registrations ADD COLUMN declined_count INTEGER DEFAULT 0;  -- For lower priority on re-waitlist

-- Email tracking table for retry/auditing
CREATE TABLE email_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    registration_id UUID REFERENCES registrations(id),
    hackathon_id UUID REFERENCES hackathons(id),  -- For filtering by event
    email_type VARCHAR(50) NOT NULL,
    recipient_email TEXT NOT NULL,
    status VARCHAR(20) NOT NULL,  -- 'pending', 'sent', 'failed'
    error_message TEXT,
    sent_at TIMESTAMP,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_email_logs_status ON email_logs(status, retry_count) WHERE status = 'failed';
CREATE INDEX idx_email_logs_hackathon ON email_logs(hackathon_id, created_at);
```

---

## 5. Frontend Changes

### New Components
1. `WaitlistManager` - Organizer view of waitlist (FIFO ordered, not reorderable)
2. `WaitlistPosition` - Participant widget showing "You are #3 in line" (1-indexed position)
3. `OfferBanner` - Prominent banner when spot is offered (24hr countdown)
4. `RegistrationFields` - Additional form fields in application wizard

### Modified Components
1. `OrganizerRegistrationsPage` - Add waitlist tab, new column filters
2. `RegistrationDetailPage` - Display new fields, add waitlist action button
3. `ApplyPage` wizard - Add new optional fields step

---

## 6. Background Jobs

### Expired Offer Cleanup
```python
# Run every 5 minutes via APScheduler or cron
async def cleanup_expired_offers():
    expired = await db.execute(
        select(Registration)
        .where(Registration.status == RegistrationStatus.offered)
        .where(Registration.offer_expires_at < now())
        .order_by(Registration.offer_expires_at.asc())  # Process oldest first
    )
    processed_hackathons = set()
    expired_list = expired.scalars().all()

    for reg in expired_list:
        # Mark as waitlisted with lower priority
        reg.status = RegistrationStatus.waitlisted
        reg.offer_expires_at = None
        reg.declined_count = (reg.declined_count or 0) + 1

        # Only promote once per hackathon per run
        if reg.hackathon_id not in processed_hackathons:
            processed_hackathons.add(reg.hackathon_id)
            promoted = await promote_from_waitlist(reg.hackathon_id, db)
            # promoted may be None (capacity full or no waitlist) - that's OK

    await db.commit()
```

**Promotion Failure Handling:** If `promote_from_waitlist` fails (email service down, etc.):
1. Log failure to `email_logs` table
2. Send admin alert via Discord webhook after 3 consecutive failures
3. Do not block cleanup - continue processing other hackathons
4. Next cleanup run will retry promotion if capacity is still available

### Event Reminder Job
```python
# Run daily at 9am
async def send_event_reminders():
    tomorrow = now() + timedelta(days=1)
    hackathons = await db.execute(
        select(Hackathon)
        .where(func.date(Hackathon.start_date) == tomorrow.date())
    )
    for hack in hackathons:
        accepted = await db.execute(
            select(Registration)
            .where(Registration.hackathon_id == hack.id)
            .where(Registration.status == RegistrationStatus.accepted)
        )
        for reg in accepted:
            await send_email(reg.user.email, "event_reminder", {"hackathon": hack})
```

---

## 7. Data Seeding Script

### bulk_seed.py
Generates realistic registration data:
- 50 registrations across multiple statuses
- Realistic names, emails, schools
- Mix of dietary restrictions, shirt sizes
- Various registration dates
- Some with team members, some solo

Usage:
```bash
python bulk_seed.py --hackathon-id <uuid> --count 50
```

---

## 8. Error Handling

| Scenario | Behavior |
|----------|----------|
| Email service down | Log error, don't block registration, admin can retry from email_logs table |
| Email rate limit exceeded | Return 429 to API caller, log for retry |
| Offer expires | Auto-return to waitlist, no notification |
| Waitlist promotion fails | Retry on next cleanup job |
| Max capacity increased | Auto-promote from waitlist to fill new spots |
| Concurrent accept-offer | First request wins (row lock), second gets 409 "Spot no longer available" |

---

## 9. Security Considerations

1. **Email rate limiting** - Max 5 emails per user per hour (throttle on test endpoint too)
2. **Offer links** - Signed URLs with expiration, not guessable
3. **Waitlist manipulation** - Only organizers can view/promote, not edit order (FIFO enforced)
4. **Data privacy** - Dietary/special needs data access restricted to organizers of that specific hackathon only

---

## 10. Implementation Order

1. Database migrations (add columns)
2. Backend: waitlist endpoints and logic
3. Backend: email service abstraction
4. Backend: background job for expired offers
5. Frontend: waitlist UI components
6. Frontend: application wizard new fields
7. Seed script for demo data
8. Integration testing
9. Deploy and verify

---

**Approved by:** [Pending user review]
