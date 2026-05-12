"""Site configuration and theming routes."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import require_organizer
from app.database import get_db
from app.schemas.config import AssetUploadResponse, BrandingResponse, ConfigKeyResponse, ConfigUpdateResponse
from app.services.config_service import ConfigService
from app.storage import StorageService

router = APIRouter(prefix="/api/config", tags=["config"])
config_service = ConfigService()
storage_service = StorageService()

_ALLOWED_CATEGORIES = {"general", "theme", "email", "features", "assets"}


@router.get("/theme.css")
async def get_theme_css(db: AsyncSession = Depends(get_db)):
    """Generate CSS custom properties from theme config.

    Behavior:
    1. Fetch theme CSS from config service.
    2. Return it as a PlainTextResponse with text/css media type.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.services.config_service.ConfigService.
    Consumers: GET /api/config/theme.css, frontend theming.
    """
    css = await config_service.get_theme_css(db)
    return PlainTextResponse(content=css, media_type="text/css")


@router.get("/custom.css")
async def get_custom_css(db: AsyncSession = Depends(get_db)):
    """Return custom CSS if set.

    Behavior:
    1. Fetch custom CSS from config service.
    2. Return empty PlainTextResponse if none is configured, otherwise return the CSS with nosniff header.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.services.config_service.ConfigService.
    Consumers: GET /api/config/custom.css, frontend theming.
    """
    custom = await config_service.get_custom_css(db)
    if custom is None:
        return PlainTextResponse(content="", media_type="text/css")
    return PlainTextResponse(
        content=custom,
        media_type="text/css",
        headers={"X-Content-Type-Options": "nosniff"},
    )


@router.get("/manifest.json")
async def get_manifest(db: AsyncSession = Depends(get_db)):
    """Dynamic Web App Manifest from site config.

    Behavior:
    1. Load all config values from the config service.
    2. Build a manifest dict with name, short_name, icons, and theme colors.
    3. Return as a JSONResponse with no-cache headers.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.services.config_service.ConfigService.
    Consumers: GET /api/config/manifest.json, PWA support.
    """
    config = await config_service.get_all(db)

    name = config.get("hackathon_name", "OpenHack")
    short_name = name[:2].upper()

    logo_url = config.get("hackathon_logo_url", "/openhack-logo.png")

    manifest = {
        "name": name,
        "short_name": short_name,
        "start_url": "/",
        "display": "standalone",
        "background_color": config.get("hackathon_background_color", "#0f172a"),
        "theme_color": config.get("hackathon_primary_color", "#2563eb"),
        "icons": [{"src": logo_url, "sizes": "512x512", "type": "image/png"}],
    }
    return JSONResponse(
        content=manifest,
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@router.get("/branding", response_model=BrandingResponse)
async def get_branding(db: AsyncSession = Depends(get_db)):
    """Backward-compat branding endpoint (deprecated).

    Behavior:
    1. Load all config values.
    2. Parse the hackathon year integer (default 2025).
    3. Return branding fields as a dict.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.services.config_service.ConfigService.
    Consumers: GET /api/config/branding, legacy frontend views.
    """
    config = await config_service.get_all(db)
    try:
        year = int(config.get("hackathon_year", "2025"))
    except (ValueError, TypeError):
        year = 2025
    return {
        "hackathon_name": config.get("hackathon_name", "OpenHack"),
        "hackathon_tagline": config.get("hackathon_tagline", "The open-source hackathon framework"),
        "hackathon_email": config.get("hackathon_email", "noreply@example.com"),
        "hackathon_primary_color": config.get("hackathon_primary_color", "#2563eb"),
        "hackathon_logo_url": config.get("hackathon_logo_url", "/openhack-logo.png"),
        "hackathon_favicon_url": config.get("hackathon_favicon_url", "/openhack-logo.png"),
        "hackathon_year": year,
    }


@router.get("/keys/{key}", response_model=ConfigKeyResponse)
async def get_single_key(key: str, db: AsyncSession = Depends(get_db)):
    """Get a single config value by key.

    Behavior:
    1. Look up the config key via config service.
    2. Return 400 if the key is invalid or not found.
    3. Return the key and its value.

    Raises: HTTPException(400) if the key is invalid or not found.
    Side Effects: None (read-only).
    Dependencies: app.services.config_service.ConfigService.
    Consumers: GET /api/config/keys/{key}, frontend settings.
    """
    try:
        value = await config_service.get(key, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"key": key, "value": value}


@router.get("/", response_model=dict[str, str])
async def get_all_config(category: str | None = None, db: AsyncSession = Depends(get_db)):
    """Get all config values, optionally filtered by category.

    Behavior:
    1. Validate the category against allowed set if provided; 400 if invalid.
    2. Fetch all config values (optionally filtered) from the config service.
    3. Return the config dict.

    Raises: HTTPException(400) if an invalid category is provided.
    Side Effects: None (read-only).
    Dependencies: app.services.config_service.ConfigService.
    Consumers: GET /api/config/, frontend settings panel.
    """
    if category and category not in _ALLOWED_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category '{category}'. Allowed: {sorted(_ALLOWED_CATEGORIES)}",
        )
    config = await config_service.get_all(db, category=category)
    return config


@router.put("/", response_model=ConfigUpdateResponse)
async def update_config(
    updates: dict[str, str],
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_organizer),
):
    """Update multiple config values (organizer only).

    Behavior:
    1. Validate and persist the key-value updates via config service; 400 if invalid.
    2. Return the list of updated keys.

    Raises: HTTPException(400) if any key or value is invalid.
    Side Effects: Mutates config store.
    Dependencies: app.services.config_service.ConfigService, app.clerk_auth.require_organizer.
    Consumers: PUT /api/config/, organizer settings panel.
    """
    try:
        await config_service.set_many(updates, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"updated": list(updates.keys())}


@router.post("/assets", response_model=AssetUploadResponse)
async def upload_asset(
    file: UploadFile = File(...),
    key: str | None = Form(None),
    auth: dict = Depends(require_organizer),
):
    """Upload a file asset to storage (organizer only).

    Behavior:
    1. Receive uploaded file and optional key name.
    2. Upload via storage service; 400 if file invalid, 502 if storage backend fails.
    3. Return asset key and public URL.

    Raises: HTTPException(400) if the file is invalid. HTTPException(502) if the storage backend fails.
    Side Effects: Writes file to storage backend.
    Dependencies: app.storage.StorageService, app.clerk_auth.require_organizer.
    Consumers: POST /api/config/assets, organizer asset manager.
    """
    try:
        result = await storage_service.upload(file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Storage error: {e}")

    return {
        "key": key or result["key"].split("/")[-1].split("-", 1)[-1],
        "url": result["url"],
    }
