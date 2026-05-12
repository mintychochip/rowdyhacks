"""Tests for content page routes."""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ContentPage, User, UserRole
from app.routes.content import router as content_router

app = FastAPI()
app.include_router(content_router)


async def _override_require_organizer():
    return {
        "sub": "test-organizer-id",
        "email": "organizer@test.com",
        "user": type(
            "FakeUser",
            (),
            {
                "role": UserRole.organizer,
                "id": "test-organizer-id",
                "email": "organizer@test.com",
                "name": "Test Organizer",
            },
        )(),
        "payload": {},
    }


@pytest_asyncio.fixture(autouse=True)
async def clear_content_cache():
    from app.cache import _memory_cache

    _memory_cache.clear()
    yield


@pytest_asyncio.fixture
async def content_client(engine):
    async_session_maker = __import__("sqlalchemy.ext.asyncio", fromlist=["async_sessionmaker"]).async_sessionmaker

    async def override_get_db():
        async with async_session_maker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
            yield session

    from app.clerk_auth import require_organizer

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_organizer] = _override_require_organizer
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def sample_pages(db_session: AsyncSession):
    from datetime import UTC, datetime

    await db_session.execute(delete(ContentPage))
    await db_session.execute(delete(User))
    await db_session.commit()

    user = User(id="test-organizer-id", email="organizer@test.com", name="Test Organizer", role=UserRole.organizer)
    db_session.add(user)
    await db_session.commit()

    pages = []
    for i, (title, slug, tab_group) in enumerate(
        [
            ("Getting Started", "getting-started", "resources"),
            ("Rules", "rules", "info"),
            ("FAQ", "faq", "resources"),
        ]
    ):
        page = ContentPage(
            slug=slug,
            title=title,
            content=f"Content for {title}",
            tab_group=tab_group,
            sort_order=i,
            tab_group_order=0,
            is_published=True,
            created_by=user.id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session.add(page)
        pages.append(page)

    unpublished = ContentPage(
        slug="draft",
        title="Draft Page",
        content="Draft content",
        tab_group="resources",
        sort_order=3,
        tab_group_order=0,
        is_published=False,
        created_by=user.id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(unpublished)
    await db_session.commit()

    for p in pages:
        await db_session.refresh(p)
    await db_session.refresh(unpublished)

    return pages + [unpublished]


@pytest.mark.anyio
async def test_list_pages(content_client, sample_pages):
    resp = await content_client.get("/api/content/pages")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["pages"]) == 3  # only published
    slugs = {p["slug"] for p in data["pages"]}
    assert slugs == {"getting-started", "rules", "faq"}
    assert "resources" in data["tab_groups"]
    assert "info" in data["tab_groups"]


@pytest.mark.anyio
async def test_list_pages_with_tab_group(content_client, sample_pages):
    resp = await content_client.get("/api/content/pages?tab_group=resources")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["pages"]) == 2
    assert all(p["tab_group"] == "resources" for p in data["pages"])
    assert data["tab_groups"] == ["resources"]


@pytest.mark.anyio
async def test_get_page(content_client, sample_pages):
    resp = await content_client.get("/api/content/pages/getting-started")
    assert resp.status_code == 200
    data = resp.json()
    assert data["slug"] == "getting-started"
    assert data["title"] == "Getting Started"
    assert data["content"] == "Content for Getting Started"


@pytest.mark.anyio
async def test_get_page_not_found(content_client):
    resp = await content_client.get("/api/content/pages/nonexistent")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Page not found"


@pytest.mark.anyio
async def test_create_page(content_client):
    resp = await content_client.post(
        "/api/content/pages",
        json={
            "title": "New Page",
            "content": "New content",
            "slug": "new-page",
            "tab_group": "resources",
            "sort_order": 1,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["slug"] == "new-page"
    assert data["title"] == "New Page"
    assert data["content"] == "New content"
    assert data["tab_group"] == "resources"
    assert data["sort_order"] == 1
    assert data["is_published"] is True


@pytest.mark.anyio
async def test_create_page_missing_title(content_client):
    resp = await content_client.post("/api/content/pages", json={"content": "No title"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Title is required"


@pytest.mark.anyio
async def test_create_page_duplicate_slug(content_client, sample_pages):
    resp = await content_client.post(
        "/api/content/pages",
        json={"title": "Getting Started 2", "slug": "getting-started"},
    )
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]


@pytest.mark.anyio
async def test_update_page(content_client, sample_pages):
    resp = await content_client.put(
        "/api/content/pages/getting-started",
        json={"title": "Updated Title", "content": "Updated content"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Updated Title"
    assert data["content"] == "Updated content"
    assert data["slug"] == "getting-started"


@pytest.mark.anyio
async def test_update_page_not_found(content_client):
    resp = await content_client.put(
        "/api/content/pages/nonexistent",
        json={"title": "Updated Title"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Page not found"


@pytest.mark.anyio
async def test_delete_page(content_client, sample_pages):
    resp = await content_client.delete("/api/content/pages/rules")
    assert resp.status_code == 200
    assert resp.json()["detail"] == "ok"

    get_resp = await content_client.get("/api/content/pages/rules")
    assert get_resp.status_code == 404
