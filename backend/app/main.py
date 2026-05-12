"""FastAPI application entrypoint and lifespan management.

Configures the web server, registers all API routers, initializes
services (scheduler, Discord bot, vector store) on startup, and
tears them down gracefully on shutdown.
"""

from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.background_jobs import shutdown_scheduler, start_scheduler
from app.cache import close_redis
from app.config import settings
from app.discord_bot import bot as discord_bot
from app.discord_bot import start_bot
from app.logging_config import configure_logging
from app.routes import content_router
from app.routes.auth import router as auth_router
from app.routes.backup import router as backup_router
from app.routes.config import router as config_router
from app.routes.assistant import router as assistant_router
from app.routes.checkin import router as checkin_router
from app.routes.checks import router as checks_router
from app.routes.crawler import router as crawler_router
from app.routes.dashboard import router as dashboard_router
from app.routes.hackathons import router as hackathons_router
from app.routes.hacker_dashboard import router as hacker_dashboard_router
from app.routes.judging import router as judging_router
from app.routes.monitoring import router as monitoring_router
from app.routes.monitoring import track_request
from app.routes.qr import router as qr_router
from app.routes.registrations import router as registrations_router
from app.routes.registrations_organizer import router as registrations_org_router
from app.routes.registration_questions import router as registration_questions_router
from app.routes.registration_notes import router as registration_notes_router
from app.routes.teams import router as teams_router
from app.routes.tracks import router as tracks_router
from app.routes.workshops import router as workshops_router
from app.routes.help_requests import router as help_requests_router
from app.routes.prizes import router as prizes_router
from app.routes.sponsors import router as sponsors_router
from app.routes.plugins import router as plugins_router
from app.routes.webhooks import router as webhooks_router
from app.routes.websocket import router as websocket_router
from app.routes.oauth import router as oauth_router
from app.routes.admin_oauth import router as admin_oauth_router
from app.routes.invites import router as invites_router
from app.routes.notifications import router as notifications_router
from app.routes.notifications import hackathon_router as hackathon_notifications_router
from app.routes.profiles import router as profiles_router, public_router as profiles_public_router
from app.routes.team_finder import router as team_finder_router
from app.routes.chat import router as chat_router
from app.routes.mentorship import router as mentorship_router
from app.routes.project_expo import router as project_expo_router
from app.routes.surveys import router as surveys_router
from app.routes.admin import router as admin_router

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
    """Initialize and tear down application-wide services.

    Behavior:
    1. Seed demo user accounts if they don't exist.
    2. Seed default content pages into the database.
    3. Seed default site configuration values.
    4. Initialize the Qdrant vector store for the assistant.
    5. Index static site pages into the vector store.
    6. Start the Discord bot (if token configured).
    7. Start the APScheduler background job scheduler.
    8. Yield control to the application runtime.
    9. On shutdown, stop the Discord bot, shutdown the scheduler, and close Redis.

    Raises: None (exceptions are caught and logged).
    Side Effects: Creates database rows, spawns background tasks, initializes external clients.
    Dependencies: app.background_jobs.start_scheduler, app.background_jobs.shutdown_scheduler, app.discord_bot.start_bot, app.seed_content.seed_default_content, app.services.config_service.ConfigService.
    Consumers: FastAPI app factory (main.py app instantiation).
    """
    # Note: Tables are created via alembic migrations, not here

    try:
        await _seed_demo_data()
    except Exception:
        import traceback

        traceback.print_exc()

    try:
        await _bootstrap_admin()
    except Exception:
        import traceback

        traceback.print_exc()

    # Seed default content pages
    try:
        from app.database import async_session
        from app.seed_content import seed_default_content

        async with async_session() as db:
            await seed_default_content(db)
    except Exception:
        import traceback

        traceback.print_exc()

    # Seed default site config
    try:
        from app.database import async_session
        from app.services.config_service import ConfigService

        async with async_session() as db:
            service = ConfigService()
            await service._seed_defaults(db)
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

    # Index site pages into vector store for assistant navigation
    try:
        from app.assistant.site_pages import index_site_pages

        await index_site_pages()
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Site page indexing failed: {e}")

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
    """Create demo accounts on startup if they don't exist.

    Behavior:
    1. Open an async database session.
    2. For each demo account (alice, bob, carol, dave), query by email.
    3. If the user exists, update their name and role.
    4. If the user does not exist, insert a new User record.
    5. Commit the transaction.

    Raises: None (exceptions are caught and logged by the caller).
    Side Effects: Inserts or updates User rows in the database.
    Dependencies: app.database.async_session, app.models.User, app.models.UserRole, sqlalchemy.select.
    Consumers: lifespan startup sequence.
    """
    from sqlalchemy import select

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
                # Update existing demo account
                user.name = name
                user.role = role
            else:
                # Create local DB record - Auth0 auth0_id will be linked on first login
                db.add(User(email=email, name=name, role=role))
        await db.commit()


async def _bootstrap_admin():
    """Create first organizer from env vars if no users exist."""
    from sqlalchemy import select, func
    from app.database import async_session
    from app.models import User, UserRole
    from app.auth import hash_password

    if not settings.admin_email or not settings.admin_password:
        return

    async with async_session() as db:
        result = await db.execute(select(func.count()).select_from(User))
        count = result.scalar()
        if count and count > 0:
            return

        user = User(
            email=settings.admin_email,
            name="Admin",
            role=UserRole.organizer,
            password_hash=hash_password(settings.admin_password),
        )
        db.add(user)
        await db.commit()


app = FastAPI(
    title="HackVerify API",
    description="Devpost/github hackathon submission integrity checker",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS: allow localhost for dev, and wildcard for production (no credentials)
import os

if os.getenv("HACKVERIFY_DEBUG", "false").lower() == "true":
    # Local development: explicit origins with credentials
    origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    creds = True
else:
    # Production: allow all origins, no credentials (handled by Nginx)
    origins = ["*"]
    creds = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=creds,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(oauth_router)
app.include_router(admin_oauth_router)
app.include_router(assistant_router, prefix="/api/assistant", tags=["assistant"])

# LLM proxy — separate router at /api/llm (not nested under /api/assistant)
from app.routes.assistant import llm_chat_proxy  # noqa: E402

llm_router = APIRouter(prefix="/api/llm", tags=["llm"])
llm_router.add_api_route("/chat", llm_chat_proxy, methods=["POST"])
app.include_router(llm_router)

app.include_router(checks_router)
app.include_router(dashboard_router)
app.include_router(hackathons_router)
app.include_router(tracks_router)
app.include_router(hacker_dashboard_router)
app.include_router(registrations_router)
app.include_router(registrations_org_router)
app.include_router(registration_questions_router)
app.include_router(registration_notes_router)
app.include_router(teams_router)
app.include_router(workshops_router)
app.include_router(sponsors_router)
app.include_router(prizes_router)
app.include_router(help_requests_router)
app.include_router(backup_router)
app.include_router(invites_router)
app.include_router(checkin_router)
app.include_router(qr_router)
app.include_router(crawler_router, prefix="/api/crawler", tags=["crawler"])
app.include_router(judging_router)
app.include_router(webhooks_router)
app.include_router(websocket_router)
app.include_router(monitoring_router)
app.include_router(content_router)
app.include_router(config_router)
app.include_router(plugins_router)
app.include_router(notifications_router)
app.include_router(hackathon_notifications_router)
app.include_router(profiles_router)
app.include_router(profiles_public_router)
app.include_router(team_finder_router)
app.include_router(mentorship_router)
app.include_router(project_expo_router)
app.include_router(chat_router)
app.include_router(surveys_router)
app.include_router(admin_router)


# Add request tracking middleware
@app.middleware("http")
async def metrics_middleware(request, call_next):
    """Track request metrics for monitoring.

    Behavior:
    1. Delegate to app.routes.monitoring.track_request to record latency and status.
    2. Return the downstream handler's response unchanged.

    Raises: None
    Side Effects: Increments Prometheus-style request counters (via track_request).
    Dependencies: app.routes.monitoring.track_request.
    Consumers: FastAPI middleware registration on the app instance.
    """
    return await track_request(request, call_next)


@app.get("/api/health")
async def health():
    """Return a simple health check response.

    Behavior:
    1. Return a static JSON payload indicating the API is alive.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: None.
    Consumers: GET /api/health, load balancers and uptime monitors.
    """
    return {"status": "ok"}


@app.get("/api/discord/invite-url")
async def discord_invite_url():
    """Get the Discord bot invite URL.

    Behavior:
    1. Import and call get_bot_invite_url to compute the OAuth invite link.
    2. Return the URL if the client ID is configured, otherwise return an error dict.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.discord_bot.get_bot_invite_url.
    Consumers: GET /api/discord/invite-url, frontend admin settings panel.
    """
    from app.discord_bot import get_bot_invite_url

    url = get_bot_invite_url()
    if not url:
        return {"error": "discord_client_id not configured"}
    return {"url": url}


@app.get("/api/discord/bot-status")
async def bot_status():
    """Check Discord bot connection state.

    Behavior:
    1. Import the global Discord bot instance.
    2. Read connection readiness, bot user string, and guild list.
    3. Return a dict with ready flag, user name, guild count, and guild summaries.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.discord_bot.bot.
    Consumers: GET /api/discord/bot-status, frontend admin dashboard.
    """
    from app.discord_bot import bot

    return {
        "ready": bot.is_ready(),
        "user": str(bot.user) if bot.user else None,
        "guild_count": len(bot.guilds),
        "guilds": [{"name": g.name, "id": g.id} for g in bot.guilds],
    }
