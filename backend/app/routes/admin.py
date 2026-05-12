"""Admin user management routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import require_clerk_user_with_db
from app.database import get_db
from app.models import UserRole
from app.services.admin_service import AdminService

router = APIRouter(prefix="/api/admin", tags=["admin"])


class ChangeRoleRequest(BaseModel):
    """Request body for changing a user's role."""

    role: str


@router.get("/users")
async def list_users(
    search: str | None = Query(None),
    role: str | None = Query(None),
    banned: bool | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    auth: dict = Depends(require_clerk_user_with_db),
    db: AsyncSession = Depends(get_db),
):
    """List all users with optional search and filter (organizer only).

    Behavior:
    1. Verify the user is an organizer.
    2. Query users via AdminService with filters.
    3. Return paginated results.

    Raises: HTTPException(403) if not organizer.
    """
    user = auth["user"]
    if user.role != UserRole.organizer:
        raise HTTPException(status_code=403, detail="Organizer access required")

    service = AdminService()
    users, total = await service.list_users(db, search=search, role=role, banned=banned, limit=limit, offset=offset)

    return {
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "name": u.name,
                "role": u.role.value if u.role else None,
                "is_banned": u.is_banned,
                "banned_at": u.banned_at.isoformat() if u.banned_at else None,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/users/{user_id}/ban")
async def ban_user(
    user_id: str,
    auth: dict = Depends(require_clerk_user_with_db),
    db: AsyncSession = Depends(get_db),
):
    """Ban a user (organizer only).

    Behavior:
    1. Verify organizer role.
    2. Ban the user via AdminService.
    3. Return confirmation.

    Raises: HTTPException(403) if not organizer, HTTPException(404) if user not found.
    """
    current_user = auth["user"]
    if current_user.role != UserRole.organizer:
        raise HTTPException(status_code=403, detail="Organizer access required")

    service = AdminService()
    try:
        user = await service.ban_user(db, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return {
        "id": user.id,
        "is_banned": user.is_banned,
        "banned_at": user.banned_at.isoformat() if user.banned_at else None,
    }


@router.post("/users/{user_id}/unban")
async def unban_user(
    user_id: str,
    auth: dict = Depends(require_clerk_user_with_db),
    db: AsyncSession = Depends(get_db),
):
    """Unban a user (organizer only).

    Behavior:
    1. Verify organizer role.
    2. Unban the user via AdminService.
    3. Return confirmation.

    Raises: HTTPException(403) if not organizer, HTTPException(404) if user not found.
    """
    current_user = auth["user"]
    if current_user.role != UserRole.organizer:
        raise HTTPException(status_code=403, detail="Organizer access required")

    service = AdminService()
    try:
        user = await service.unban_user(db, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return {
        "id": user.id,
        "is_banned": user.is_banned,
        "banned_at": user.banned_at.isoformat() if user.banned_at else None,
    }


@router.post("/users/{user_id}/role")
async def change_user_role(
    user_id: str,
    body: ChangeRoleRequest,
    auth: dict = Depends(require_clerk_user_with_db),
    db: AsyncSession = Depends(get_db),
):
    """Change a user's role (organizer only).

    Behavior:
    1. Verify organizer role.
    2. Change role via AdminService.
    3. Return confirmation.

    Raises: HTTPException(403) if not organizer, HTTPException(400/404) on errors.
    """
    current_user = auth["user"]
    if current_user.role != UserRole.organizer:
        raise HTTPException(status_code=403, detail="Organizer access required")

    service = AdminService()
    try:
        user = await service.change_role(db, user_id, body.role)
    except ValueError as exc:
        status = 404 if "not found" in str(exc) else 400
        raise HTTPException(status_code=status, detail=str(exc))

    return {
        "id": user.id,
        "role": user.role.value if user.role else None,
    }


@router.get("/users/{user_id}/activity")
async def get_user_activity(
    user_id: str,
    auth: dict = Depends(require_clerk_user_with_db),
    db: AsyncSession = Depends(get_db),
):
    """View user activity log (organizer only).

    Behavior:
    1. Verify organizer role.
    2. Fetch activity summary via AdminService.
    3. Return the activity dict.

    Raises: HTTPException(403) if not organizer.
    """
    current_user = auth["user"]
    if current_user.role != UserRole.organizer:
        raise HTTPException(status_code=403, detail="Organizer access required")

    service = AdminService()
    activity = await service.get_user_activity(db, user_id)
    return activity
