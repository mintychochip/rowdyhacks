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
    """Convert title to URL-friendly slug."""
    slug = re.sub(r"[^\w\s-]", "", title.lower())
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug.strip("-")[:100]


def _page_to_response(page: ContentPage, author_name: str | None = None) -> dict:
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
    """List content pages, optionally filtered by tab_group."""
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
    """Get a single content page by slug."""
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
    """Create a new content page (organizer only)."""
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
    """Update a content page (organizer only)."""
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
    """Delete a content page (organizer only)."""
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
