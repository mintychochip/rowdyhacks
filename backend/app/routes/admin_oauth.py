from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import encrypt_secret, require_organizer
from app.database import get_db
from app.models import OAuthProvider
from app.routes.oauth import OAUTH_PRESETS

router = APIRouter(prefix="/api/admin/oauth", tags=["admin-oauth"])


@router.get("/providers")
async def list_providers(
    db: AsyncSession = Depends(get_db),
    user=Depends(require_organizer),
):
    result = await db.execute(select(OAuthProvider))
    providers = result.scalars().all()
    return [
        {
            "name": p.name,
            "display_name": p.display_name,
            "client_id": p.client_id,
            "client_secret": "***",
            "is_active": p.is_active,
        }
        for p in providers
    ]


@router.post("/providers")
async def add_provider(
    name: str,
    client_id: str,
    client_secret: str,
    preset: str | None = None,
    authorize_url: str | None = None,
    token_url: str | None = None,
    userinfo_url: str | None = None,
    scope: str | None = None,
    display_name: str | None = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_organizer),
):
    # Check for duplicate
    existing = await db.execute(select(OAuthProvider).where(OAuthProvider.name == name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Provider already exists")

    # Apply preset if specified
    if preset and preset in OAUTH_PRESETS:
        preset_data = OAUTH_PRESETS[preset]
        authorize_url = authorize_url or preset_data["authorize_url"]
        token_url = token_url or preset_data["token_url"]
        userinfo_url = userinfo_url or preset_data["userinfo_url"]
        scope = scope or preset_data["scope"]
        display_name = display_name or preset_data["display_name"]

    if not all([authorize_url, token_url, userinfo_url, scope]):
        raise HTTPException(status_code=400, detail="Missing required OAuth endpoint URLs")

    provider = OAuthProvider(
        name=name,
        display_name=display_name or name.capitalize(),
        client_id=client_id,
        client_secret_encrypted=encrypt_secret(client_secret),
        authorize_url=authorize_url,
        token_url=token_url,
        userinfo_url=userinfo_url,
        scope=scope,
    )
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    return {"name": provider.name, "display_name": provider.display_name}


@router.delete("/providers/{name}")
async def remove_provider(
    name: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_organizer),
):
    result = await db.execute(select(OAuthProvider).where(OAuthProvider.name == name))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    provider.is_active = False
    await db.commit()
    return {"message": f"Provider {name} deactivated"}
