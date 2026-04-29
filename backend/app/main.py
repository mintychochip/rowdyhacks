from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine
from app.models import Base
from app.routes.auth import router as auth_router
from app.routes.checks import router as checks_router
from app.routes.dashboard import router as dashboard_router
from app.routes.hackathons import router as hackathons_router
from app.routes.registrations import router as registrations_router
from app.routes.registrations_organizer import router as registrations_org_router
from app.routes.checkin import router as checkin_router
from app.routes.qr import router as qr_router
from app.routes.crawler import router as crawler_router
from app.routes.judging import router as judging_router
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.crawler.scheduler import run_crawl
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup and start the crawler scheduler."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        await _seed_demo_data()
    except Exception:
        import traceback
        traceback.print_exc()

    # Start the crawler scheduler
    scheduler = AsyncIOScheduler()
    cron_parts = settings.crawler_schedule.split()
    scheduler.add_job(
        run_crawl,
        trigger="cron",
        minute=cron_parts[0],
        hour=cron_parts[1],
        day=cron_parts[2],
        month=cron_parts[3],
        day_of_week=cron_parts[4],
        id="devpost_crawl",
    )
    scheduler.start()

    yield

    scheduler.shutdown(wait=False)


async def _seed_demo_data():
    """Create or update demo accounts on startup so they always work."""
    from app.database import async_session
    from app.models import User, UserRole
    from app.auth import hash_password
    from sqlalchemy import select

    async with async_session() as db:
        for email, name, role in [
            ("alice@demo.com", "Alice", UserRole.organizer),
            ("bob@demo.com", "Bob", UserRole.participant),
            ("carol@demo.com", "Carol", UserRole.organizer),
            ("dave@demo.com", "Dave", UserRole.judge),
        ]:
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            if user:
                # Update existing demo account — reset password and role
                user.name = name
                user.role = role
                user.password_hash = hash_password("demo1234")
            else:
                db.add(User(email=email, name=name, role=role, password_hash=hash_password("demo1234")))
        await db.commit()


app = FastAPI(
    title="HackVerify API",
    description="Devpost/github hackathon submission integrity checker",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(checks_router)
app.include_router(dashboard_router)
app.include_router(hackathons_router)
app.include_router(registrations_router)
app.include_router(registrations_org_router)
app.include_router(checkin_router)
app.include_router(qr_router)
app.include_router(crawler_router, prefix="/api/crawler", tags=["crawler"])
app.include_router(judging_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
