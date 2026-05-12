"""Public resource page routes backed by MinIO markdown files."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from starlette.status import (
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
)

from app.auth import require_organizer
from app.models import User
from app.services.resource_service import (
    create_resource,
    delete_resource,
    get_resource,
    list_resources,
    update_resource,
)

router = APIRouter(prefix="/api/resources", tags=["resources"])


class _ResourceCreate(BaseModel):
    slug: str = Field(..., pattern=r"^[a-z0-9-]+$")
    title: str = Field(..., min_length=1)
    content: str = ""
    tab_group: str | None = None
    sort_order: int | None = None
    tab_group_order: int | None = None


class _ResourceUpdate(BaseModel):
    title: str = Field(..., min_length=1)
    content: str = ""
    tab_group: str | None = None
    sort_order: int | None = None
    tab_group_order: int | None = None


@router.get("")
async def resources_list():
    """List all published resource pages.

    Response shape mirrors the legacy DB endpoint::

        {"pages": [ {id, title, slug, content, tab_group, ...} ]}

    Raises: None.
    Side Effects: May read from S3 and write to cache.
    """
    pages = await list_resources()
    return {"pages": pages}


@router.get("/{slug}")
async def resource_detail(slug: str):
    """Fetch a single resource page by slug.

    Response shape mirrors the legacy DB endpoint::

        {id, title, slug, content, tab_group, tab_group_order, sort_order,
         is_published, created_at, updated_at}

    Raises:
        HTTPException: 404 if the file does not exist; 422 if frontmatter is invalid.
    Side Effects: May read from S3.
    """
    try:
        page = await get_resource(slug)
    except ValueError as exc:
        raise HTTPException(status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Resource not found") from exc
    return page


@router.post("")
async def resource_create(
    data: _ResourceCreate,
    user: User = Depends(require_organizer),
):
    """Create a new resource markdown file in MinIO.

    Raises:
        HTTPException: 409 if slug already exists; 422 on validation error.
    Side Effects: Writes to S3; busts cache.
    """
    try:
        page = await create_resource(
            slug=data.slug,
            title=data.title,
            content=data.content,
            tab_group=data.tab_group,
            sort_order=data.sort_order,
            tab_group_order=data.tab_group_order,
        )
    except FileExistsError as exc:
        raise HTTPException(status_code=HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return page


@router.put("/{slug}")
async def resource_update(
    slug: str,
    data: _ResourceUpdate,
    user: User = Depends(require_organizer),
):
    """Overwrite an existing resource markdown file in MinIO.

    The slug is read from the URL path and is immutable.

    Raises:
        HTTPException: 404 if resource does not exist; 422 on validation error.
    Side Effects: Writes to S3; busts cache.
    """
    try:
        page = await update_resource(
            slug=slug,
            title=data.title,
            content=data.content,
            tab_group=data.tab_group,
            sort_order=data.sort_order,
            tab_group_order=data.tab_group_order,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return page


@router.delete("/{slug}")
async def resource_delete(
    slug: str,
    user: User = Depends(require_organizer),
):
    """Delete a resource markdown file from MinIO.

    Raises: None (missing object is silently ignored).
    Side Effects: Removes from S3; busts cache.
    """
    await delete_resource(slug)
    return {"detail": "Resource deleted"}
