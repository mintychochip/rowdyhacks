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
    """Run every 5 minutes. Expire old offers and promote next waitlisted."""
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
    """Run daily at 9am. Send reminder emails for events starting tomorrow."""
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
    """Start background job scheduler."""
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
    """Shutdown scheduler gracefully."""
    scheduler.shutdown()
    print("Background scheduler stopped")
