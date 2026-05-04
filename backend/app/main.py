from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.background_jobs import shutdown_scheduler, start_scheduler
from app.cache import close_redis
from app.config import settings
from app.database import engine
from app.discord_bot import bot as discord_bot
from app.discord_bot import start_bot
from app.logging_config import configure_logging
from app.models import Base
from app.routes.assistant import router as assistant_router
from app.routes.auth import router as auth_router
from app.routes.checkin import router as checkin_router
from app.routes.checks import router as checks_router
from app.routes.crawler import router as crawler_router
from app.routes.dashboard import router as dashboard_router
from app.routes.hackathons import router as hackathons_router
from app.routes.hacker_dashboard import router as hacker_dashboard_router
from app.routes.judging import router as judging_router
from app.routes.monitoring import router as monitoring_router
from app.routes.monitoring import track_request
from app.routes.oauth import router as oauth_router
from app.routes.qr import router as qr_router
from app.routes.registrations import router as registrations_router
from app.routes.registrations_organizer import router as registrations_org_router
from app.routes.tracks import router as tracks_router
from app.routes.websocket import router as websocket_router

# Configure structured logging
configure_logging(log_level=settings.log_level, json_logs=settings.json_logs)

# Initialize Sentry if configured
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup and start the crawler scheduler."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Add track_type column if missing (on existing DBs without this column)
        try:
            await conn.execute(text("ALTER TABLE tracks ADD COLUMN IF NOT EXISTS track_type VARCHAR(50)"))
            # Backfill existing tracks with correct track_type values
            await conn.execute(
                text("UPDATE tracks SET track_type = 'prize' WHERE track_type IS NULL AND name = ANY(:names)"),
                {"names": ("Deep Space Exploration", "Orbital Commerce", "Mission Control AI")},
            )
            await conn.execute(
                text("UPDATE tracks SET track_type = 'themed' WHERE track_type IS NULL AND name = ANY(:names)"),
                {"names": ("Cosmic Commons", "Nebula Arts", "Lunar Settlements")},
            )
        except Exception:
            pass  # Column may already exist or table not yet created

    try:
        await _seed_demo_data()
    except Exception:
        import traceback
        traceback.print_exc()

    # Initialize vector store for assistant
    try:
        from app.assistant.indexer import initialize_vector_store
        await initialize_vector_store()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Vector store init failed: {e}")

    # Start Discord bot (if token configured, fails gracefully)
    await start_bot()

    # Start background job scheduler
    start_scheduler()

    yield

    # Shutdown Discord bot
    try:
        if discord_bot.is_ready():
            await discord_bot.close()
    except Exception:
        pass

    # Shutdown background scheduler
    shutdown_scheduler()

    # Close Redis connection
    await close_redis()


async def _seed_demo_data():
    """Create or update demo accounts on startup so they always work."""
    from sqlalchemy import select

    from app.auth import hash_password
    from app.database import async_session
    from app.models import User, UserRole

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
app.include_router(assistant_router, prefix="/api/assistant", tags=["assistant"])
app.include_router(checks_router)
app.include_router(dashboard_router)
app.include_router(hackathons_router)
app.include_router(tracks_router)
app.include_router(hacker_dashboard_router)
app.include_router(registrations_router)
app.include_router(registrations_org_router)
app.include_router(checkin_router)
app.include_router(qr_router)
app.include_router(crawler_router, prefix="/api/crawler", tags=["crawler"])
app.include_router(judging_router)
app.include_router(oauth_router, prefix="/api/auth/oauth", tags=["oauth"])
app.include_router(websocket_router)
app.include_router(monitoring_router)


# Add request tracking middleware
@app.middleware("http")
async def metrics_middleware(request, call_next):
    return await track_request(request, call_next)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/discord/invite-url")
async def discord_invite_url():
    """Get the Discord bot invite URL."""
    from app.discord_bot import get_bot_invite_url

    url = get_bot_invite_url()
    if not url:
        return {"error": "discord_client_id not configured"}
    return {"url": url}


@app.get("/api/discord/bot-status")
async def bot_status():
    """Check Discord bot connection state."""
    from app.discord_bot import bot

    return {
        "ready": bot.is_ready(),
        "user": str(bot.user) if bot.user else None,
        "guild_count": len(bot.guilds),
        "guilds": [{"name": g.name, "id": g.id} for g in bot.guilds],
    }
