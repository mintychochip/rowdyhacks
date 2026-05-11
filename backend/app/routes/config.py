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
    """Generate CSS custom properties from theme config."""
    css = await config_service.get_theme_css(db)
    return PlainTextResponse(content=css, media_type="text/css")


@router.get("/custom.css")
async def get_custom_css(db: AsyncSession = Depends(get_db)):
    """Return custom CSS if set."""
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
    """Dynamic Web App Manifest from site config."""
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
    """Backward-compat branding endpoint (deprecated)."""
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
    try:
        value = await config_service.get(key, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"key": key, "value": value}


@router.get("/", response_model=dict[str, str])
async def get_all_config(category: str | None = None, db: AsyncSession = Depends(get_db)):
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
