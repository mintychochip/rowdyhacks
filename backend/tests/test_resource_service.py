"""Tests for the MinIO-backed resource page service."""

import asyncio

import pytest
import pytest_asyncio
from fastapi import HTTPException, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

from app.cache import _memory_cache
from app.main import app
from app.services.resource_service import (
    create_resource,
    delete_resource,
    get_resource,
    list_resources,
    parse_frontmatter,
    update_resource,
    validate_resource,
)
from app.storage import StorageService


class TestParseFrontmatter:
    """Unit tests for the pure frontmatter parser."""

    def test_empty_frontmatter(self):
        raw = b"# Hello\n\nWorld"
        meta, body = parse_frontmatter(raw)
        assert meta == {}
        assert body == "# Hello\n\nWorld"

    def test_valid_frontmatter(self):
        raw = b"""---
title: APIs
tab_group: Guides
sort_order: 2
---

# APIs & Services

Some content here.
"""
        meta, body = parse_frontmatter(raw)
        assert meta["title"] == "APIs"
        assert meta["tab_group"] == "Guides"
        assert meta["sort_order"] == 2
        assert body.startswith("# APIs & Services")

    def test_no_closing_delimiter(self):
        raw = b"---\ntitle: Foo\n\n# Body"
        meta, body = parse_frontmatter(raw)
        # Should return empty metadata when closing delimiter is missing
        assert meta == {}
        assert "# Body" in body

    def test_invalid_yaml_raises(self):
        raw = b"---\n{ bad yaml: [\n---\n\nBody"
        with pytest.raises(ValueError, match="Invalid YAML frontmatter"):
            parse_frontmatter(raw)


class TestValidateResource:
    """Unit tests for resource metadata validation."""

    def test_valid_metadata(self):
        validate_resource({"title": "Getting Started"}, "getting-started")

    def test_missing_title(self):
        with pytest.raises(ValueError, match="missing required 'title' frontmatter"):
            validate_resource({}, "foo")

    def test_empty_title(self):
        with pytest.raises(ValueError, match="missing required 'title' frontmatter"):
            validate_resource({"title": "   "}, "foo")

    def test_invalid_slug(self):
        with pytest.raises(ValueError, match="Invalid slug"):
            validate_resource({"title": "Foo"}, "Bad_Slug")


class TestResourceServiceIntegration:
    """Integration tests against real MinIO/S3.

    Skipped automatically when S3/MinIO is not configured or unreachable.
    """

    @pytest.fixture(autouse=True)
    async def _skip_if_no_minio(self):
        from app.config import settings

        if not settings.s3_endpoint:
            pytest.skip("S3/MinIO endpoint not configured")

        storage = StorageService()
        try:
            await storage.object_exists("__health_check__")
        except Exception as exc:
            pytest.skip(f"S3/MinIO unreachable: {exc}")

    @pytest.fixture(autouse=True)
    async def _cleanup_test_files(self):
        """Remove test objects and clear cache before/after each test."""
        _memory_cache.clear()
        yield
        storage = StorageService()
        try:
            objects = await storage.list_objects("resources/")
            for obj in objects:
                if obj["key"].startswith("resources/test-"):
                    await asyncio.to_thread(
                        storage._get_client().delete_object,
                        Bucket=storage._bucket,
                        Key=obj["key"],
                    )
        except Exception:
            pass
        _memory_cache.clear()

    async def test_list_and_get_resource(self):
        storage = StorageService()

        test_body = """---
title: Test Resource
tab_group: Testing
sort_order: 42
tab_group_order: 7
---

# Test Resource

This is a test markdown body.
"""
        await storage.put_object(
            "resources/test-resource.md",
            test_body.encode("utf-8"),
            content_type="text/markdown; charset=utf-8",
        )

        pages = await list_resources()
        slugs = [p["slug"] for p in pages]
        assert "test-resource" in slugs

        page = next(p for p in pages if p["slug"] == "test-resource")
        assert page["title"] == "Test Resource"
        assert page["tab_group"] == "Testing"
        assert page["sort_order"] == 42
        assert page["tab_group_order"] == 7
        assert page["is_published"] is True
        assert page["id"] == "test-resource"
        assert "# Test Resource" in page["content"]

        # get_resource should return the same shape
        detail = await get_resource("test-resource")
        assert detail["title"] == "Test Resource"
        assert detail["slug"] == "test-resource"
        assert detail["tab_group"] == "Testing"
        assert detail["sort_order"] == 42
        assert "# Test Resource" in detail["content"]

    async def test_get_resource_not_found(self):
        with pytest.raises(FileNotFoundError):
            await get_resource("test-does-not-exist")

    async def test_malformed_resource_skipped_in_list(self):
        storage = StorageService()

        # Upload a file with missing title frontmatter
        bad_body = b"---\nfoo: bar\n---\n\nNo title here."
        await storage.put_object(
            "resources/test-bad.md",
            bad_body,
            content_type="text/markdown; charset=utf-8",
        )

        pages = await list_resources()
        slugs = [p["slug"] for p in pages]
        assert "test-bad" not in slugs

    async def test_create_resource(self):
        page = await create_resource(
            slug="test-create",
            title="Created Resource",
            content="# Hello",
            tab_group="Guides",
            sort_order=1,
            tab_group_order=2,
        )

        assert page["slug"] == "test-create"
        assert page["title"] == "Created Resource"

        # Verify it exists in S3 and list
        pages = await list_resources()
        slugs = [p["slug"] for p in pages]
        assert "test-create" in slugs

        detail = await get_resource("test-create")
        assert detail["title"] == "Created Resource"
        assert detail["tab_group"] == "Guides"
        assert detail["sort_order"] == 1
        assert detail["tab_group_order"] == 2
        assert detail["content"] == "# Hello"

    async def test_create_resource_duplicate_slug(self):
        storage = StorageService()
        await storage.put_object(
            "resources/test-dup.md",
            b"---\ntitle: Dup\n---\n\nBody",
            content_type="text/markdown; charset=utf-8",
        )

        with pytest.raises(FileExistsError, match="already exists"):
            await create_resource(slug="test-dup", title="Duplicate", content="")

    async def test_create_resource_invalid_slug(self):
        with pytest.raises(ValueError, match="Invalid slug"):
            await create_resource(slug="Bad_Slug", title="Bad", content="")

    async def test_create_resource_missing_title(self):
        with pytest.raises(ValueError, match="Title is required"):
            await create_resource(slug="test-no-title", title="", content="")

    async def test_update_resource(self):
        # Create first
        await create_resource(slug="test-update", title="Original", content="Old")

        # Update
        page = await update_resource(
            slug="test-update",
            title="Updated",
            content="New",
            tab_group="Updated Group",
            sort_order=99,
        )

        assert page["title"] == "Updated"

        detail = await get_resource("test-update")
        assert detail["title"] == "Updated"
        assert detail["content"] == "New"
        assert detail["tab_group"] == "Updated Group"
        assert detail["sort_order"] == 99

    async def test_update_resource_not_found(self):
        with pytest.raises(FileNotFoundError, match="Resource not found"):
            await update_resource(slug="test-missing", title="Missing", content="")

    async def test_update_resource_invalid_slug(self):
        with pytest.raises(ValueError, match="Invalid slug"):
            await update_resource(slug="Bad_Slug", title="Bad", content="")

    async def test_update_resource_missing_title(self):
        with pytest.raises(ValueError, match="Title is required"):
            await update_resource(slug="test-update", title="", content="")

    async def test_delete_resource(self):
        await create_resource(slug="test-delete", title="To Delete", content="Bye")

        # Verify exists
        pages = await list_resources()
        assert "test-delete" in [p["slug"] for p in pages]

        # Delete
        await delete_resource("test-delete")

        # Verify gone
        pages = await list_resources()
        assert "test-delete" not in [p["slug"] for p in pages]

        with pytest.raises(FileNotFoundError):
            await get_resource("test-delete")


class TestResourceRoutesIntegration:
    """Route handler integration tests against real MinIO/S3."""

    @pytest.fixture(autouse=True)
    async def _skip_if_no_minio(self):
        from app.config import settings

        if not settings.s3_endpoint:
            pytest.skip("S3/MinIO endpoint not configured")

        storage = StorageService()
        try:
            await storage.object_exists("__health_check__")
        except Exception as exc:
            pytest.skip(f"S3/MinIO unreachable: {exc}")

    @pytest.fixture(autouse=True)
    async def _cleanup_test_files(self):
        """Remove test objects and clear cache before/after each test."""
        _memory_cache.clear()
        yield
        storage = StorageService()
        try:
            objects = await storage.list_objects("resources/")
            for obj in objects:
                if obj["key"].startswith("resources/test-"):
                    await asyncio.to_thread(
                        storage._get_client().delete_object,
                        Bucket=storage._bucket,
                        Key=obj["key"],
                    )
        except Exception:
            pass
        _memory_cache.clear()

    @pytest_asyncio.fixture
    async def route_client(self):
        from app.auth import require_organizer
        from app.database import get_db
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

        # Use the same test DB as conftest
        test_db_url = "sqlite+aiosqlite:///:memory:"
        engine = create_async_engine(test_db_url, echo=False)
        from app.models import Base

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async def override_get_db():
            async with async_session_maker() as session:
                yield session

        async def override_require_organizer():
            from app.models import UserRole

            return type(
                "FakeUser",
                (),
                {
                    "role": UserRole.organizer,
                    "id": "test-organizer-id",
                    "email": "organizer@test.com",
                    "name": "Test Organizer",
                    "password_hash": "hash",
                    "email_verified": True,
                },
            )()

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[require_organizer] = override_require_organizer

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

        app.dependency_overrides.clear()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    async def test_post_resource(self, route_client):
        res = await route_client.post(
            "/api/resources",
            json={
                "slug": "test-route-create",
                "title": "Route Created",
                "content": "# Route\n\nBody",
                "tab_group": "Routes",
                "sort_order": 3,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["slug"] == "test-route-create"
        assert data["title"] == "Route Created"

    async def test_post_resource_duplicate_slug(self, route_client):
        # Create first
        await route_client.post(
            "/api/resources",
            json={
                "slug": "test-route-dup",
                "title": "First",
                "content": "Body",
            },
        )

        # Try duplicate
        res = await route_client.post(
            "/api/resources",
            json={
                "slug": "test-route-dup",
                "title": "Second",
                "content": "Body",
            },
        )
        assert res.status_code == 409

    async def test_post_resource_invalid_slug(self, route_client):
        res = await route_client.post(
            "/api/resources",
            json={
                "slug": "Bad_Slug",
                "title": "Bad",
            },
        )
        assert res.status_code == 422

    async def test_post_resource_missing_title(self, route_client):
        res = await route_client.post(
            "/api/resources",
            json={
                "slug": "test-no-title",
                "title": "",
            },
        )
        assert res.status_code == 422

    async def test_put_resource(self, route_client):
        # Create first
        await route_client.post(
            "/api/resources",
            json={
                "slug": "test-route-update",
                "title": "Original",
                "content": "Old",
            },
        )

        res = await route_client.put(
            "/api/resources/test-route-update",
            json={
                "title": "Updated",
                "content": "New",
                "tab_group": "Updated",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["title"] == "Updated"

    async def test_put_resource_not_found(self, route_client):
        res = await route_client.put(
            "/api/resources/test-route-missing",
            json={
                "title": "Missing",
                "content": "",
            },
        )
        assert res.status_code == 404

    async def test_delete_resource(self, route_client):
        # Create first
        await route_client.post(
            "/api/resources",
            json={
                "slug": "test-route-delete",
                "title": "To Delete",
                "content": "Bye",
            },
        )

        res = await route_client.delete("/api/resources/test-route-delete")
        assert res.status_code == 200

        # Verify gone
        res2 = await route_client.get("/api/resources/test-route-delete")
        assert res2.status_code == 404

    async def test_auth_rejection(self, route_client):
        from app.auth import require_organizer

        # Override require_organizer to reject
        def reject_organizer():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organizer access required")

        original = app.dependency_overrides.get(require_organizer)
        app.dependency_overrides[require_organizer] = reject_organizer
        try:
            res = await route_client.post(
                "/api/resources",
                json={
                    "slug": "test-auth",
                    "title": "Auth Test",
                },
            )
            assert res.status_code == 403
        finally:
            if original:
                app.dependency_overrides[require_organizer] = original
            else:
                app.dependency_overrides.pop(require_organizer, None)
