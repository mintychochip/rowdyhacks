"""Content page management routes for organizer-editable markdown pages."""

import re
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import cache_delete_pattern, cached
from app.clerk_auth import require_organizer
from app.database import get_db
from app.models import ContentPage, User

router = APIRouter(prefix="/api/content", tags=["content"])

CONTENT_CACHE_TTL = 300  # 5 minutes
CACHE_PFX = "content"


def _slugify(title: str) -> str:
    """Convert a page title to a URL-friendly slug.

    Behavior:
    1. Strip non-alphanumeric characters and lowercase the title.
    2. Collapse spaces and hyphens into a single hyphen.
    3. Trim to a maximum of 100 characters.

    Raises: None
    Side Effects: None (pure function).
    Dependencies: re module.
    Consumers: content.py create_page helper.
    """
    slug = re.sub(r"[^\w\s-]", "", title.lower())
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug.strip("-")[:100]


def _page_to_response(page: ContentPage, author_name: str | None = None) -> dict:
    """Serialize a ContentPage model to a response dict."""
    return {
        "id": str(page.id),
        "slug": page.slug,
        "title": page.title,
        "content": page.content,
        "tab_group": page.tab_group,
        "sort_order": page.sort_order,
        "tab_group_order": page.tab_group_order,
        "is_published": page.is_published,
        "created_by": str(page.created_by),
        "author_name": author_name or "Unknown",
        "created_at": page.created_at.isoformat() if page.created_at else None,
        "updated_at": page.updated_at.isoformat() if page.updated_at else None,
    }


@router.get("/pages")
@cached(ttl_seconds=CONTENT_CACHE_TTL, key_prefix=CACHE_PFX)
async def list_pages(
    tab_group: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List published content pages, optionally filtered by tab_group.

    Behavior:
    1. Query published ContentPage rows joined with author names.
    2. Optionally filter by tab_group query parameter.
    3. Order results by tab_group_order and sort_order.
    4. Return serialized pages and the set of present tab_groups.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.models.ContentPage, app.models.User, app.cache.cached.
    Consumers: GET /api/content/pages, public page listing.
    """
    query = (
        select(ContentPage, User.name)
        .outerjoin(User, ContentPage.created_by == User.id)
        .where(ContentPage.is_published.is_(True))
    )
    if tab_group:
        query = query.where(ContentPage.tab_group == tab_group)
    query = query.order_by(ContentPage.tab_group_order, ContentPage.sort_order)
    result = await db.execute(query)
    rows = result.all()
    pages = [_page_to_response(page, author_name=name) for page, name in rows]
    return {
        "pages": pages,
        "tab_groups": list(set(p.tab_group for p in [r[0] for r in rows])),
    }


@router.get("/pages/{slug}")
@cached(ttl_seconds=CONTENT_CACHE_TTL, key_prefix=CACHE_PFX)
async def get_page(slug: str, db: AsyncSession = Depends(get_db)):
    """Get a single published content page by slug.

    Behavior:
    1. Query ContentPage by slug where is_published is True, joined with author name.
    2. Return 404 if no matching page exists.
    3. Return serialized page details.

    Raises: HTTPException(404) if the page is not found or unpublished.
    Side Effects: None (read-only).
    Dependencies: app.models.ContentPage, app.models.User.
    Consumers: GET /api/content/pages/{slug}, public page viewer.
    """
    result = await db.execute(
        select(ContentPage, User.name)
        .outerjoin(User, ContentPage.created_by == User.id)
        .where(ContentPage.slug == slug, ContentPage.is_published.is_(True))
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Page not found")
    page, author_name = row
    return _page_to_response(page, author_name=author_name)


@router.post("/pages", status_code=201)
async def create_page(
    request: Request,
    body: dict,
    user_payload: dict = Depends(require_organizer),
    db: AsyncSession = Depends(get_db),
):
    """Create a new content page (organizer only).

    Behavior:
    1. Validate the title is present; 422 if missing.
    2. Generate or validate the slug (lowercase alphanumeric with hyphens); 422 if invalid.
    3. Check for slug conflicts; 409 if duplicate.
    4. Create and persist the ContentPage row.
    5. Bust the content cache.
    6. Return the created page's serialized details.

    Raises: HTTPException(422) if title is missing or slug is invalid. HTTPException(409) if slug already exists.
    Side Effects: Inserts ContentPage row; clears content cache.
    Dependencies: app.models.ContentPage, app.cache.cache_delete_pattern.
    Consumers: POST /api/content/pages, organizer dashboard.
    """
    user = user_payload["user"]

    # Validate slug or generate from title
    title = body.get("title", "").strip()
    if not title:
        raise HTTPException(status_code=422, detail="Title is required")

    slug = body.get("slug", "").strip()
    if not slug:
        slug = _slugify(title)
    if not re.match(r"^[a-z0-9-]+$", slug):
        raise HTTPException(status_code=422, detail="Slug must be lowercase alphanumeric with hyphens only")

    # Check for slug conflict
    existing = await db.execute(select(ContentPage).where(ContentPage.slug == slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Page with slug '{slug}' already exists")

    page = ContentPage(
        slug=slug,
        title=title,
        content=body.get("content", ""),
        tab_group=body.get("tab_group", "resources"),
        sort_order=body.get("sort_order", 0),
        tab_group_order=body.get("tab_group_order", 0),
        is_published=body.get("is_published", True),
        created_by=user.id,
    )
    db.add(page)
    await db.commit()
    await db.refresh(page)

    await _bust_content_cache()
    return _page_to_response(page)


@router.put("/pages/{slug}")
async def update_page(
    request: Request,
    slug: str,
    body: dict,
    user_payload: dict = Depends(require_organizer),
    db: AsyncSession = Depends(get_db),
):
    """Update a content page (organizer only).

    Behavior:
    1. Look up the page by slug; 404 if not found.
    2. Apply allowed field updates from the body (title, content, tab_group, sort_order, tab_group_order, is_published).
    3. Update the updated_at timestamp.
    4. Commit changes and bust the content cache.
    5. Return the updated page's serialized details.

    Raises: HTTPException(404) if the page is not found.
    Side Effects: Mutates ContentPage row; clears content cache.
    Dependencies: app.models.ContentPage.
    Consumers: PUT /api/content/pages/{slug}, organizer dashboard.
    """
    result = await db.execute(select(ContentPage).where(ContentPage.slug == slug))
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    # Update fields
    if "title" in body:
        page.title = body["title"].strip()
    if "content" in body:
        page.content = body["content"]
    if "tab_group" in body:
        page.tab_group = body["tab_group"]
    if "sort_order" in body:
        page.sort_order = body["sort_order"]
    if "tab_group_order" in body:
        page.tab_group_order = body["tab_group_order"]
    if "is_published" in body:
        page.is_published = body["is_published"]

    page.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(page)

    await _bust_content_cache()
    return _page_to_response(page)


@router.delete("/pages/{slug}", status_code=200)
async def delete_page(
    request: Request,
    slug: str,
    user_payload: dict = Depends(require_organizer),
    db: AsyncSession = Depends(get_db),
):
    """Delete a content page (organizer only).

    Behavior:
    1. Look up the page by slug; 404 if not found.
    2. Delete the page from the database and commit.
    3. Bust the content cache.
    4. Return confirmation dict.

    Raises: HTTPException(404) if the page is not found.
    Side Effects: Deletes ContentPage row; clears content cache.
    Dependencies: app.models.ContentPage.
    Consumers: DELETE /api/content/pages/{slug}, organizer dashboard.
    """
    result = await db.execute(select(ContentPage).where(ContentPage.slug == slug))
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    await db.delete(page)
    await db.commit()

    await _bust_content_cache()
    return {"detail": "ok"}


async def _bust_content_cache():
    """Invalidate all content page caches after mutations."""
    await cache_delete_pattern(f"{CACHE_PFX}:*")
