from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import settings

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("/branding")
async def get_branding():
    """Public endpoint returning hackathon branding configuration."""
    return {
        "hackathon_name": settings.hackathon_name,
        "hackathon_tagline": settings.hackathon_tagline,
        "hackathon_email": settings.hackathon_email,
        "hackathon_primary_color": settings.hackathon_primary_color,
        "hackathon_logo_url": settings.hackathon_logo_url,
        "hackathon_favicon_url": settings.hackathon_favicon_url,
        "hackathon_year": settings.hackathon_year,
    }


@router.get("/manifest.json")
async def get_manifest():
    """Dynamic Web App Manifest with branding from environment."""
    manifest = {
        "name": settings.hackathon_name,
        "short_name": settings.hackathon_name[:2].upper(),
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0f172a",
        "theme_color": settings.hackathon_primary_color,
        "icons": [
            {
                "src": settings.hackathon_logo_url,
                "sizes": "512x512",
                "type": "image/png",
            }
        ],
    }
    return JSONResponse(
        content=manifest,
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )
