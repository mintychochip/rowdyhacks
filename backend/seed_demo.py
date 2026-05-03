"""Seed demo data: create org + user + hackathon + accepted registration with QR."""

import asyncio
import uuid
from datetime import UTC, datetime

from app.auth import create_qr_token, hash_password
from app.database import async_session
from app.models import Hackathon, Registration, RegistrationStatus, User, UserRole
from sqlalchemy import select


async def seed():
    async with async_session() as db:
        # Check if already seeded
        result = await db.execute(select(Hackathon).where(Hackathon.name == "Demo Hack"))
        if result.scalar_one_or_none():
            print("Already seeded!")
            return

        # Create organizer
        org = User(
            id=uuid.uuid4(),
            email="org@demo.com",
            name="Demo Organizer",
            password_hash=hash_password("demo12345"),
            role=UserRole.organizer,
        )
        db.add(org)

        # Create judge
        judge = User(
            id=uuid.uuid4(),
            email="judge@demo.com",
            name="Demo Judge",
            password_hash=hash_password("demo12345"),
            role=UserRole.judge,
        )
        db.add(judge)

        # Create participant
        user = User(
            id=uuid.uuid4(),
            email="alice@demo.com",
            name="Alice",
            password_hash=hash_password("demo12345"),
            role=UserRole.participant,
        )
        db.add(user)
        await db.flush()

        # Create hackathon
        hack = Hackathon(
            id=uuid.uuid4(),
            name="Demo Hack",
            start_date=datetime(2026, 5, 1, tzinfo=UTC),
            end_date=datetime(2026, 5, 8, tzinfo=UTC),
            organizer_id=org.id,
        )
        db.add(hack)
        await db.flush()

        # Create accepted registration with QR
        reg = Registration(
            id=uuid.uuid4(),
            hackathon_id=hack.id,
            user_id=user.id,
            status=RegistrationStatus.accepted,
            team_name="Dream Team",
            team_members=["Alice", "Bob", "Charlie"],
            qr_token=create_qr_token(
                registration_id="",
                user_id=str(user.id),
                hackathon_id=str(hack.id),
                hackathon_end=hack.end_date,
            ),
            registered_at=datetime.now(UTC),
            accepted_at=datetime.now(UTC),
        )
        # Fix qr_token with actual reg id
        reg.qr_token = create_qr_token(
            registration_id=str(reg.id),
            user_id=str(user.id),
            hackathon_id=str(hack.id),
            hackathon_end=hack.end_date,
        )
        db.add(reg)
        await db.commit()

        print(f"Organizer: org@demo.com / demo12345  (id: {org.id})")
        print(f"Judge: judge@demo.com / demo12345  (id: {judge.id})")
        print(f"Participant: alice@demo.com / demo12345  (id: {user.id})")
        print(f"Hackathon: Demo Hack  (id: {hack.id})")
        print(f"Registration: {reg.id}  (status: accepted, QR ready!)")
        print(f"QR URL: http://localhost:8000/api/checkin/scan?token={reg.qr_token}")


if __name__ == "__main__":
    asyncio.run(seed())
