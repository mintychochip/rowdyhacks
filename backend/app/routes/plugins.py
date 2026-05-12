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
    """Request body for registering a plugin.

    Behavior:
    1. Define the schema for a plugin registration request.
    2. Provide name, version, description, enabled, and config fields.

    Side Effects: None (schema definition).
    Dependencies: pydantic.BaseModel.
    Consumers: POST /api/plugins, plugin registry.
    """

    name: str
    version: str = "0.1.0"
    description: str | None = None
    enabled: bool = True
    config: dict | None = None


class UpdatePluginRequest(BaseModel):
    """Request body for updating a plugin.

    Behavior:
    1. Define the schema for a plugin update request.
    2. Provide version, description, enabled, and config fields.

    Side Effects: None (schema definition).
    Dependencies: pydantic.BaseModel.
    Consumers: PUT /api/plugins/{plugin_id}, plugin update.
    """

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
    """Register a new plugin.

    Behavior:
    1. Call PluginService to register the plugin with the given fields.
    2. Catch ValueError and raise 400 for duplicate names.
    3. Return the created plugin details.

    Raises: HTTPException(400) if registration fails (e.g. duplicate name).
    Side Effects: Inserts Plugin row via PluginService.
    Dependencies: app.services.plugin_service.PluginService, app.clerk_auth.require_clerk_user.
    Consumers: POST /api/plugins, plugin registry.
    """
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
    """List all registered plugins.

    Behavior:
    1. Query all registered plugins via PluginService.
    2. Serialize each plugin to a dict with full details.
    3. Return the list.

    Side Effects: None (read-only).
    Dependencies: app.services.plugin_service.PluginService.
    Consumers: GET /api/plugins, plugin registry.
    """
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
    """Get a single plugin by ID.

    Behavior:
    1. Load the plugin via PluginService.
    2. Raise 404 if the plugin does not exist.
    3. Return the plugin details.

    Raises: HTTPException(404) if plugin not found.
    Side Effects: None (read-only).
    Dependencies: app.services.plugin_service.PluginService.
    Consumers: GET /api/plugins/{plugin_id}, plugin registry.
    """
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
    """Update a plugin.

    Behavior:
    1. Call PluginService to update the plugin by UUID with the given fields.
    2. Catch ValueError and raise 404 if the plugin is not found.
    3. Return the updated plugin id, name, enabled flag, and updated flag.

    Raises: HTTPException(404) if plugin not found.
    Side Effects: Mutates Plugin row via PluginService.
    Dependencies: app.services.plugin_service.PluginService, app.clerk_auth.require_clerk_user.
    Consumers: PUT /api/plugins/{plugin_id}, plugin registry.
    """
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
    """Unregister a plugin.

    Behavior:
    1. Call PluginService to delete the plugin by UUID.
    2. Catch ValueError and raise 404 if the plugin is not found.
    3. Return None (204 response).

    Raises: HTTPException(404) if plugin not found.
    Side Effects: Deletes Plugin row via PluginService.
    Dependencies: app.services.plugin_service.PluginService, app.clerk_auth.require_clerk_user.
    Consumers: DELETE /api/plugins/{plugin_id}, plugin registry.
    """
    service = PluginService()
    try:
        await service.delete_plugin(db, UUID(plugin_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return None
