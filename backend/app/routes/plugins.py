"""Plugin registry routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import require_clerk_user
from app.database import get_db
from app.services.plugin_service import PluginService

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


class RegisterPluginRequest(BaseModel):
    name: str
    version: str = "0.1.0"
    description: str | None = None
    enabled: bool = True
    config: dict | None = None


class UpdatePluginRequest(BaseModel):
    version: str | None = None
    description: str | None = None
    enabled: bool | None = None
    config: dict | None = None


@router.post("", status_code=201)
async def register_plugin(
    body: RegisterPluginRequest,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Register a new plugin."""
    service = PluginService()
    try:
        plugin = await service.register_plugin(
            db,
            name=body.name,
            version=body.version,
            description=body.description,
            enabled=body.enabled,
            config=body.config,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "id": str(plugin.id),
        "name": plugin.name,
        "version": plugin.version,
        "enabled": plugin.enabled,
        "created_at": plugin.created_at.isoformat() if plugin.created_at else None,
    }


@router.get("")
async def list_plugins(
    db: AsyncSession = Depends(get_db),
):
    """List all registered plugins."""
    service = PluginService()
    plugins = await service.list_plugins(db)
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "version": p.version,
            "description": p.description,
            "enabled": p.enabled,
            "config": p.config,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in plugins
    ]


@router.get("/{plugin_id}")
async def get_plugin(
    plugin_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a single plugin."""
    service = PluginService()
    plugin = await service.get_plugin(db, UUID(plugin_id))
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return {
        "id": str(plugin.id),
        "name": plugin.name,
        "version": plugin.version,
        "description": plugin.description,
        "enabled": plugin.enabled,
        "config": plugin.config,
        "created_at": plugin.created_at.isoformat() if plugin.created_at else None,
    }


@router.put("/{plugin_id}")
async def update_plugin(
    plugin_id: str,
    body: UpdatePluginRequest,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a plugin."""
    service = PluginService()
    try:
        plugin = await service.update_plugin(
            db,
            UUID(plugin_id),
            version=body.version,
            description=body.description,
            enabled=body.enabled,
            config=body.config,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return {
        "id": str(plugin.id),
        "name": plugin.name,
        "enabled": plugin.enabled,
        "updated": True,
    }


@router.delete("/{plugin_id}", status_code=204)
async def delete_plugin(
    plugin_id: str,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Unregister a plugin."""
    service = PluginService()
    try:
        await service.delete_plugin(db, UUID(plugin_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return None
