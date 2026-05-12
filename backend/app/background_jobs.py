"""Background jobs for waitlist cleanup and event reminders."""

from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from app.database import async_session
from app.email_service import send_email_with_retry
from app.models import Hackathon, Registration, RegistrationStatus, User
from app.waitlist import promote_from_waitlist

scheduler = AsyncIOScheduler()


async def cleanup_expired_offers():
    """Expire stale spot offers and promote the next waitlisted applicant.

    Behavior:
    1. Open an async database session.
    2. Query all registrations whose ``offered`` status has passed the expiry timestamp.
    3. For each expired offer, revert the status to ``waitlisted`` and increment the declined count.
    4. Trigger promotion from the waitlist once per affected hackathon.
    5. Commit the transaction.
    6. Catch and print any exception to prevent the scheduler from crashing.

    Raises: None (exceptions are caught and logged).
    Side Effects: Updates Registration rows; may send offer emails via promote_from_waitlist.
    Dependencies: app.database.async_session, app.models.Registration, app.models.RegistrationStatus, app.waitlist.promote_from_waitlist.
    Consumers: APScheduler job running every 5 minutes.
    """
    async with async_session() as db:
        try:
            now = datetime.now(UTC)

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
    """Send reminder emails to accepted participants for hackathons starting tomorrow.

    Behavior:
    1. Open an async database session.
    2. Compute tomorrow's date window (midnight to 23:59:59).
    3. Query hackathons whose start_date falls within that window.
    4. For each matching hackathon, query all accepted registrations.
    5. Load the user record for each registration.
    6. Dispatch an event-reminder email via send_email_with_retry.
    7. Catch and print any exception to prevent the scheduler from crashing.

    Raises: None (exceptions are caught and logged).
    Side Effects: Sends external emails via SendGrid or SMTP.
    Dependencies: app.database.async_session, app.models.Hackathon, app.models.Registration, app.models.RegistrationStatus, app.models.User, app.email_service.send_email_with_retry.
    Consumers: APScheduler job running daily at 9:00 AM.
    """
    async with async_session() as db:
        try:
            tomorrow = datetime.now(UTC) + timedelta(days=1)
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
                        },
                    )

        except Exception as e:
            print(f"Error in send_event_reminders: {e}")


def start_scheduler():
    """Start the APScheduler background job scheduler.

    Behavior:
    1. Register the cleanup_expired_offers job to run every 5 minutes.
    2. Register the send_event_reminders job to run daily at 9:00 AM.
    3. Start the scheduler event loop.
    4. Print a startup confirmation message.

    Raises: None
    Side Effects: Starts the APScheduler event loop and registers persistent jobs.
    Dependencies: apscheduler.schedulers.asyncio.AsyncIOScheduler, apscheduler.triggers.interval.IntervalTrigger, apscheduler.triggers.cron.CronTrigger.
    Consumers: app.main.lifespan startup sequence.
    """
    # Cleanup expired offers every 5 minutes
    scheduler.add_job(
        cleanup_expired_offers, IntervalTrigger(minutes=5), id="cleanup_expired_offers", replace_existing=True
    )

    # Event reminders daily at 9am
    scheduler.add_job(
        send_event_reminders, CronTrigger(hour=9, minute=0), id="send_event_reminders", replace_existing=True
    )

    scheduler.start()
    print("Background scheduler started")


def shutdown_scheduler():
    """Shut down the APScheduler background job scheduler gracefully.

    Behavior:
    1. Invoke the scheduler's shutdown method.
    2. Print a shutdown confirmation message.

    Raises: None
    Side Effects: Stops the APScheduler event loop and terminates pending jobs.
    Dependencies: apscheduler.schedulers.asyncio.AsyncIOScheduler.
    Consumers: app.main.lifespan shutdown sequence.
    """
    scheduler.shutdown()
    print("Background scheduler stopped")
