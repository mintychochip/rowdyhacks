"""Content page management routes for organizer-editable markdown pages."""

import re
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi_limiter.depends import RateLimiter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import decode_token
from app.cache import cache_delete_pattern, cached
from app.database import get_db
from app.models import ContentPage, User, UserRole

router = APIRouter(prefix="/api/content", tags=["content"])

CONTENT_CACHE_TTL = 300  # 5 minutes
CACHE_PFX = "content"


def _slugify(title: str) -> str:
    """Convert title to URL-friendly slug."""
    slug = re.sub(r"[^\w\s-]", "", title.lower())
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug.strip("-")[:100]


def _get_current_user_payload(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization.removeprefix("Bearer ")
    try:
        return decode_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def _require_organizer(db: AsyncSession, authorization: str | None) -> User:
    """Verify user is an organizer."""
    payload = _get_current_user_payload(authorization)
    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role != UserRole.organizer:
        raise HTTPException(status_code=403, detail="Only organizers can manage content")
    return user


def _page_to_response(page: ContentPage) -> dict:
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
    query = select(ContentPage).where(ContentPage.is_published == True)
    if tab_group:
        query = query.where(ContentPage.tab_group == tab_group)
    query = query.order_by(ContentPage.tab_group_order, ContentPage.sort_order)
    result = await db.execute(query)
    pages = result.scalars().all()
    return {
        "pages": [_page_to_response(p) for p in pages],
        "tab_groups": list(set(p.tab_group for p in pages)),
    }


@router.get("/pages/{slug}")
@cached(ttl_seconds=CONTENT_CACHE_TTL, key_prefix=CACHE_PFX)
async def get_page(slug: str, db: AsyncSession = Depends(get_db)):
    """Get a single content page by slug."""
    result = await db.execute(
        select(ContentPage).where(ContentPage.slug == slug, ContentPage.is_published == True)
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return _page_to_response(page)


@router.post(
    "/pages",
    status_code=201,
    dependencies=[Depends(RateLimiter(times=30, seconds=60))],
)
async def create_page(
    request: Request,
    body: dict,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Create a new content page (organizer only)."""
    user = await _require_organizer(db, authorization)

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


@router.put(
    "/pages/{slug}",
    dependencies=[Depends(RateLimiter(times=30, seconds=60))],
)
async def update_page(
    request: Request,
    slug: str,
    body: dict,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Update a content page (organizer only)."""
    await _require_organizer(db, authorization)

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

    # Invalidate caches
    await _bust_content_cache()
    await cache_delete_pattern(f"{CACHE_PFX}:get_page:{slug}")

    return _page_to_response(page)


@router.delete(
    "/pages/{slug}",
    status_code=200,
    dependencies=[Depends(RateLimiter(times=30, seconds=60))],
)
async def delete_page(
    request: Request,
    slug: str,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Delete a content page (organizer only)."""
    await _require_organizer(db, authorization)

    result = await db.execute(select(ContentPage).where(ContentPage.slug == slug))
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    await db.delete(page)
    await db.commit()

    # Invalidate caches
    await _bust_content_cache()
    await cache_delete_pattern(f"{CACHE_PFX}:get_page:{slug}")

    return {"detail": "ok"}


async def _bust_content_cache():
    """Invalidate all content page caches after mutations."""
    await cache_delete_pattern(f"{CACHE_PFX}:list_pages:*")
