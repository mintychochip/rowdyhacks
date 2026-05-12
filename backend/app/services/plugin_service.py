"""Lightweight plugin registry service.

Provides CRUD operations for a plugin registry, including version tracking,
enablement toggles, and arbitrary JSON configuration storage.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Plugin


class PluginService:
    """CRUD operations for the plugin registry.

    Plugins are uniquely identified by name and support versioning,
    enablement flags, and structured configuration.
    """

    async def register_plugin(
        self,
        db: AsyncSession,
        name: str,
        version: str = "0.1.0",
        description: str | None = None,
        enabled: bool = True,
        config: dict | None = None,
    ) -> Plugin:
        """Register a new plugin in the registry.

        Behavior:
        1. Query for an existing plugin with the same name.
        2. Raise if a plugin with that name already exists.
        3. Build a new Plugin instance with the provided fields.
        4. Add the plugin to the async session, commit, and refresh.
        5. Return the persisted plugin.

        Raises: ValueError if a plugin with the same name is already registered.
        Side Effects: Inserts a new Plugin row into the database.
        Dependencies: app.models.Plugin.
        Consumers: POST /api/plugins, authenticated users registering plugins.
        """
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
        """List all registered plugins ordered by name.

        Behavior:
        1. Query all Plugin records ordered by name ascending.
        2. Return the list of plugins.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models.Plugin.
        Consumers: GET /api/plugins, public plugin listing.
        """
        result = await db.execute(select(Plugin).order_by(Plugin.name))
        return list(result.scalars().all())

    async def get_plugin(self, db: AsyncSession, plugin_id) -> Plugin | None:
        """Get a single plugin by its ID.

        Behavior:
        1. Query Plugin by the given plugin_id.
        2. Return the record if found, otherwise None.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models.Plugin.
        Consumers: GET /api/plugins/{plugin_id}, public plugin detail view.
        """
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
        """Update plugin fields selectively.

        Behavior:
        1. Load the plugin by ID.
        2. Validate the plugin exists.
        3. Apply any provided non-None field updates.
        4. Commit and refresh the record.

        Raises: ValueError if the plugin is not found.
        Side Effects: Updates Plugin row fields in the database.
        Dependencies: app.models.Plugin.
        Consumers: PUT /api/plugins/{plugin_id}, authenticated users updating plugins.
        """
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
        """Unregister a plugin from the registry.

        Behavior:
        1. Load the plugin by ID.
        2. Validate the plugin exists.
        3. Delete the record from the session and commit.

        Raises: ValueError if the plugin is not found.
        Side Effects: Deletes a Plugin row from the database.
        Dependencies: app.models.Plugin.
        Consumers: DELETE /api/plugins/{plugin_id}, authenticated users deleting plugins.
        """
        plugin = await self.get_plugin(db, plugin_id)
        if not plugin:
            raise ValueError("Plugin not found")
        await db.delete(plugin)
        await db.commit()
