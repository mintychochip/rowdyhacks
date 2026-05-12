"""Tests for PluginService."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.plugin_service import PluginService


@pytest.mark.anyio
async def test_register_plugin(db_session: AsyncSession):
    """register_plugin must create and return a new plugin."""
    service = PluginService()
    plugin = await service.register_plugin(
        db_session,
        name=f"plugin-{uuid.uuid4().hex[:8]}",
        version="0.2.0",
        description="Does something",
        enabled=False,
        config={"foo": "bar"},
    )
    assert plugin.version == "0.2.0"
    assert plugin.enabled is False
    assert plugin.config == {"foo": "bar"}


@pytest.mark.anyio
async def test_register_plugin_duplicate_raises(db_session: AsyncSession):
    """register_plugin must raise ValueError when name already exists."""
    service = PluginService()
    name = f"dup-{uuid.uuid4().hex[:8]}"
    await service.register_plugin(db_session, name=name)
    with pytest.raises(ValueError, match="already registered"):
        await service.register_plugin(db_session, name=name)


@pytest.mark.anyio
async def test_list_plugins(db_session: AsyncSession):
    """list_plugins must return all plugins ordered by name."""
    service = PluginService()
    name1 = f"alpha-{uuid.uuid4().hex[:8]}"
    name2 = f"beta-{uuid.uuid4().hex[:8]}"
    await service.register_plugin(db_session, name=name1)
    await service.register_plugin(db_session, name=name2)
    plugins = await service.list_plugins(db_session)
    names = [p.name for p in plugins]
    assert name1 in names
    assert name2 in names
    assert names == sorted(names)


@pytest.mark.anyio
async def test_get_plugin_found(db_session: AsyncSession):
    """get_plugin must return the plugin when it exists."""
    service = PluginService()
    plugin = await service.register_plugin(db_session, name=f"get-{uuid.uuid4().hex[:8]}")
    found = await service.get_plugin(db_session, plugin.id)
    assert found is not None
    assert found.id == plugin.id


@pytest.mark.anyio
async def test_get_plugin_not_found(db_session: AsyncSession):
    """get_plugin must return None when plugin does not exist."""
    service = PluginService()
    found = await service.get_plugin(db_session, uuid.uuid4())
    assert found is None


@pytest.mark.anyio
async def test_update_plugin(db_session: AsyncSession):
    """update_plugin must apply non-None field changes."""
    service = PluginService()
    plugin = await service.register_plugin(db_session, name=f"upd-{uuid.uuid4().hex[:8]}")
    updated = await service.update_plugin(
        db_session,
        plugin.id,
        version="2.0.0",
        description="Updated",
        enabled=False,
        config={"new": "config"},
    )
    assert updated.version == "2.0.0"
    assert updated.description == "Updated"
    assert updated.enabled is False
    assert updated.config == {"new": "config"}


@pytest.mark.anyio
async def test_update_plugin_partial(db_session: AsyncSession):
    """update_plugin must leave unspecified fields unchanged."""
    service = PluginService()
    plugin = await service.register_plugin(db_session, name=f"part-{uuid.uuid4().hex[:8]}", version="1.0.0")
    original_version = plugin.version
    updated = await service.update_plugin(db_session, plugin.id, enabled=False)
    assert updated.version == original_version
    assert updated.enabled is False


@pytest.mark.anyio
async def test_update_plugin_not_found(db_session: AsyncSession):
    """update_plugin must raise ValueError when plugin does not exist."""
    service = PluginService()
    with pytest.raises(ValueError, match="Plugin not found"):
        await service.update_plugin(db_session, uuid.uuid4(), version="1.0.0")


@pytest.mark.anyio
async def test_delete_plugin(db_session: AsyncSession):
    """delete_plugin must remove the plugin from the database."""
    service = PluginService()
    plugin = await service.register_plugin(db_session, name=f"del-{uuid.uuid4().hex[:8]}")
    await service.delete_plugin(db_session, plugin.id)
    found = await service.get_plugin(db_session, plugin.id)
    assert found is None


@pytest.mark.anyio
async def test_delete_plugin_not_found(db_session: AsyncSession):
    """delete_plugin must raise ValueError when plugin does not exist."""
    service = PluginService()
    with pytest.raises(ValueError, match="Plugin not found"):
        await service.delete_plugin(db_session, uuid.uuid4())
