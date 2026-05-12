"""Storage browser routes for organizers to inspect MinIO/S3 contents."""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import require_organizer
from app.models import User
from app.storage import StorageService

storage_service = StorageService()

router = APIRouter(prefix="/api/storage", tags=["storage"])


@router.get("/objects")
async def list_objects(
    prefix: str = Query(default="", description="S3 prefix / folder path"),
    _user: User = Depends(require_organizer),
):
    """List objects in the configured S3 bucket for organizers.

    Behavior:
    1. Verify the caller is an organizer.
    2. Call StorageService.list_objects with the optional prefix.
    3. Enrich each object with a public URL.
    4. Return the list.

    Raises:
        HTTPException(502): If the S3 call fails.
    """
    try:
        objects = await storage_service.list_objects(prefix=prefix)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Storage error: {e}") from e

    # Build public URLs for each object
    base = storage_service._public_base
    for obj in objects:
        obj["url"] = f"{base}/{obj['key']}"

    return {"objects": objects, "prefix": prefix, "bucket": storage_service._bucket}
