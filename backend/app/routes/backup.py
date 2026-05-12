"""Backup and restore routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import require_clerk_user
from app.database import get_db
from app.services.backup_service import BackupService

router = APIRouter(prefix="/api/backup", tags=["backup"])


class RestoreRequest(BaseModel):
    """Request body for restoring a hackathon from exported data.

    Attributes:
        data: Full exported hackathon payload previously returned by the backup endpoint.
    """

    data: dict


@router.get("/{hackathon_id}")
async def backup_hackathon(
    hackathon_id: str,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Export a hackathon and all related data.

    Behavior:
    1. Validate hackathon_id UUID and invoke BackupService.export_hackathon.
    2. Return 404 if the hackathon is not found.
    3. Return the full hackathon snapshot dict.

    Raises: HTTPException(404) if the hackathon is not found.
    Side Effects: None (read-only).
    Dependencies: app.services.backup_service.BackupService.
    Consumers: GET /api/backup/{hackathon_id}, organizer backup tool.
    """
    service = BackupService()
    try:
        data = await service.export_hackathon(db, UUID(hackathon_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return data


@router.post("/restore")
async def restore_hackathon(
    body: RestoreRequest,
    user_payload: dict = Depends(require_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Restore a hackathon from exported data.

    Behavior:
    1. Invoke BackupService.restore_hackathon with the user's sub as organizer.
    2. Return the restored hackathon's id, name, and restored flag.

    Raises: None
    Side Effects: Inserts hackathon and related rows into the database.
    Dependencies: app.services.backup_service.BackupService.
    Consumers: POST /api/backup/restore, organizer backup tool.
    """
    service = BackupService()
    hackathon = await service.restore_hackathon(db, user_payload["sub"], body.data)
    return {
        "id": str(hackathon.id),
        "name": hackathon.name,
        "restored": True,
    }
