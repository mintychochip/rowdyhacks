"""Lightweight plugin registry service."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Plugin


class PluginService:
    """CRUD operations for plugin registry."""

    async def register_plugin(
        self,
        db: AsyncSession,
        name: str,
        version: str = "0.1.0",
        description: str | None = None,
        enabled: bool = True,
        config: dict | None = None,
    ) -> Plugin:
        """Register a new plugin."""
        result = await db.execute(select(Plugin).where(Plugin.name == name))
        existing = result.scalar_one_or_none()
        if existing:
            raise ValueError(f"Plugin {name} already registered")

        plugin = Plugin(
            name=name,
            version=version,
            description=description,
            enabled=enabled,
            config=config,
        )
        db.add(plugin)
        await db.commit()
        await db.refresh(plugin)
        return plugin

    async def list_plugins(self, db: AsyncSession) -> list[Plugin]:
        """List all registered plugins."""
        result = await db.execute(select(Plugin).order_by(Plugin.name))
        return list(result.scalars().all())

    async def get_plugin(self, db: AsyncSession, plugin_id) -> Plugin | None:
        """Get a plugin by ID."""
        result = await db.execute(select(Plugin).where(Plugin.id == plugin_id))
        return result.scalar_one_or_none()

    async def update_plugin(
        self,
        db: AsyncSession,
        plugin_id,
        version: str | None = None,
        description: str | None = None,
        enabled: bool | None = None,
        config: dict | None = None,
    ) -> Plugin:
        """Update plugin fields."""
        plugin = await self.get_plugin(db, plugin_id)
        if not plugin:
            raise ValueError("Plugin not found")

        if version is not None:
            plugin.version = version
        if description is not None:
            plugin.description = description
        if enabled is not None:
            plugin.enabled = enabled
        if config is not None:
            plugin.config = config

        await db.commit()
        await db.refresh(plugin)
        return plugin

    async def delete_plugin(self, db: AsyncSession, plugin_id) -> None:
        """Unregister a plugin."""
        plugin = await self.get_plugin(db, plugin_id)
        if not plugin:
            raise ValueError("Plugin not found")
        await db.delete(plugin)
        await db.commit()
