"""Generate realistic demo registration data."""

import argparse
import asyncio

# Add parent to path
import os
import random
import sys
import uuid
from datetime import UTC, datetime, timedelta

from faker import Faker
from sqlalchemy import select

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.auth import hash_password
from app.database import async_session
from app.models import Hackathon, Registration, RegistrationStatus, User, UserRole

fake = Faker()

# Sample data
DIETARY_OPTIONS = [None, "vegetarian", "vegan", "gluten-free", "halal", "kosher", "nut allergy"]
SHIRT_SIZES = ["XS", "S", "M", "L", "XL", "XXL"]
EXPERIENCE_LEVELS = ["beginner", "intermediate", "advanced"]
TEAM_NAMES = [
    "Code Wizards",
    "Binary Builders",
    "Stack Overflowers",
    "Git Pushers",
    "Null Pointers",
    "Runtime Errors",
    "Syntax Squad",
    "Debuggers",
    "Bit Shifters",
    "Algorithm Aces",
    "Data Driven",
    "Cloud Ninjas",
    "API Architects",
    "Frontend Fanatics",
    "Backend Bandits",
]


async def create_demo_users(db, count: int) -> list[User]:
    """Create demo participant users."""
    users = []
    for i in range(count):
        user = User(
            id=uuid.uuid4(),
            email=f"demo{i + 1}@example.com",
            name=fake.name(),
            password_hash=hash_password("demo12345"),
            role=UserRole.participant,
        )
        db.add(user)
        users.append(user)
    await db.flush()
    return users


async def create_registrations(
    db, hackathon_id: uuid.UUID, users: list[User], target_count: int = 50
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
        status = random.choices([s for s, _ in status_weights], weights=[w for _, w in status_weights])[0]

        # Registration time within last 30 days
        days_ago = random.randint(0, 30)
        registered_at = datetime.now(UTC) - timedelta(days=days_ago)

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
            t_shirt_size=random.choice(SHIRT_SIZES),
            special_needs=random.choice([None, None, None, "Wheelchair accessible", "Hearing assistance"]),
            experience_level=random.choice(EXPERIENCE_LEVELS),
            school_company=fake.company() if random.random() > 0.3 else fake.university(),
            graduation_year=random.choice([None, 2026, 2027, 2028]) if random.random() > 0.4 else None,
        )

        # Status-specific timestamps
        if status in (RegistrationStatus.accepted, RegistrationStatus.checked_in, RegistrationStatus.offered):
            reg.accepted_at = registered_at + timedelta(days=random.randint(1, 5))

        if status == RegistrationStatus.offered:
            reg.offered_at = datetime.now(UTC) - timedelta(hours=random.randint(1, 20))
            reg.offer_expires_at = reg.offered_at + timedelta(hours=24)

        if status == RegistrationStatus.checked_in:
            reg.checked_in_at = datetime.now(UTC) - timedelta(days=random.randint(0, 2))

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
        result = await db.execute(select(Registration).where(Registration.hackathon_id == hackathon_uuid))
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
