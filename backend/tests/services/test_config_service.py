import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.services.config_service import ConfigService, _CACHE_KEY, _CACHE_TTL


class FakeResult:
    def __init__(self, scalar=None, scalars=None):
        self._scalar = scalar
        self._scalars = scalars if scalars is not None else []

    def scalar_one_or_none(self):
        return self._scalar

    def scalars(self):
        class _FakeScalars:
            def __init__(self, items):
                self._items = items

            def all(self):
                return self._items

        return _FakeScalars(self._scalars)


class FakeRow:
    def __init__(self, value):
        self.value = value


@pytest.fixture
def service():
    return ConfigService()


@pytest.fixture
def db():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.add = Mock()
    return db


@pytest.mark.asyncio
async def test_get_returns_default_when_db_empty(service, db):
    db.execute.return_value = FakeResult(scalar=None)
    with (
        patch("app.services.config_service.cache_get", new_callable=AsyncMock) as mock_cache_get,
        patch("app.services.config_service.cache_set", new_callable=AsyncMock) as mock_cache_set,
        patch("app.services.config_service.cache_delete", new_callable=AsyncMock) as mock_cache_delete,
    ):
        # Use a key with no env_attr so the DB is actually queried
        result = await service.get("hackathon_background_color", db)
        assert result == "#0f172a"
        db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_returns_db_value_over_default(service, db):
    db.execute.return_value = FakeResult(scalar=FakeRow("#1a1a1a"))
    with (
        patch("app.services.config_service.cache_get", new_callable=AsyncMock) as mock_cache_get,
        patch("app.services.config_service.cache_set", new_callable=AsyncMock) as mock_cache_set,
        patch("app.services.config_service.cache_delete", new_callable=AsyncMock) as mock_cache_delete,
    ):
        # Use a key with no env_attr so the DB value is actually read
        result = await service.get("hackathon_background_color", db)
        assert result == "#1a1a1a"
        db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_all_caches_in_redis(service, db):
    db.execute.return_value = FakeResult(scalars=[])
    with (
        patch("app.services.config_service.cache_get", new_callable=AsyncMock, return_value=None) as mock_cache_get,
        patch("app.services.config_service.cache_set", new_callable=AsyncMock) as mock_cache_set,
        patch("app.services.config_service.cache_delete", new_callable=AsyncMock) as mock_cache_delete,
    ):
        result = await service.get_all(db)
        assert isinstance(result, dict)
        assert result["hackathon_name"] == "OpenHack"
        mock_cache_set.assert_awaited_once()
        args, kwargs = mock_cache_set.call_args
        assert args[0] == _CACHE_KEY
        assert isinstance(args[1], dict)
        assert args[2] == _CACHE_TTL


@pytest.mark.asyncio
async def test_set_rejects_unknown_key(service, db):
    with (
        patch("app.services.config_service.cache_get", new_callable=AsyncMock),
        patch("app.services.config_service.cache_set", new_callable=AsyncMock),
        patch("app.services.config_service.cache_delete", new_callable=AsyncMock),
    ):
        with pytest.raises(ValueError, match="Unknown key 'bad_key'"):
            await service.set("bad_key", "val", db)


@pytest.mark.asyncio
async def test_get_theme_css_emits_defaults(service, db):
    db.execute.return_value = FakeResult(scalar=None)
    with (
        patch("app.services.config_service.cache_get", new_callable=AsyncMock),
        patch("app.services.config_service.cache_set", new_callable=AsyncMock),
        patch("app.services.config_service.cache_delete", new_callable=AsyncMock),
    ):
        css = await service.get_theme_css(db)
        assert css.startswith(":root {")
        assert "--oh-primary: #2563eb;" in css
        assert css.endswith("}")


@pytest.mark.asyncio
async def test_set_writes_to_db_and_invalidates_cache(service, db):
    db.execute.return_value = FakeResult(scalar=FakeRow("OldVal"))
    with (
        patch("app.services.config_service.cache_get", new_callable=AsyncMock),
        patch("app.services.config_service.cache_set", new_callable=AsyncMock),
        patch("app.services.config_service.cache_delete", new_callable=AsyncMock) as mock_cache_delete,
    ):
        await service.set("hackathon_name", "NewVal", db)
        db.commit.assert_awaited_once()
        mock_cache_delete.assert_awaited_once_with(_CACHE_KEY)


@pytest.mark.asyncio
async def test_set_many_updates_multiple_keys(service, db):
    db.execute.return_value = FakeResult(scalar=FakeRow("OldVal"))
    with (
        patch("app.services.config_service.cache_get", new_callable=AsyncMock),
        patch("app.services.config_service.cache_set", new_callable=AsyncMock),
        patch("app.services.config_service.cache_delete", new_callable=AsyncMock) as mock_cache_delete,
    ):
        await service.set_many({"hackathon_name": "NewName", "hackathon_tagline": "NewTagline"}, db)
        db.commit.assert_awaited_once()
        mock_cache_delete.assert_awaited_once_with(_CACHE_KEY)


@pytest.mark.asyncio
async def test_get_all_filtered_by_category(service, db):
    db.execute.side_effect = [
        FakeResult(
            scalars=[
                type("R", (), {"key": "hackathon_background_color", "value": "#000000"})(),
                type("R", (), {"key": "hackathon_name", "value": "OpenHack"})(),
            ]
        ),
    ]
    with (
        patch("app.services.config_service.cache_get", new_callable=AsyncMock, return_value=None) as mock_cache_get,
        patch("app.services.config_service.cache_set", new_callable=AsyncMock),
        patch("app.services.config_service.cache_delete", new_callable=AsyncMock),
    ):
        result = await service.get_all(db, category="theme")
        assert "hackathon_background_color" in result
        assert "hackathon_name" not in result
        assert result["hackathon_background_color"] == "#000000"
