"""Auth routes - simplified to Clerk-only authentication."""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import (
    decode_clerk_token,
    extract_clerk_user_id,
    extract_clerk_user_email,
    fetch_clerk_user_details,
    is_clerk_token,
)
from app.database import get_db
from app.models import User
from app.schemas import UserResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/me", response_model=UserResponse)
async def get_me(
    authorization: str | None = Header(alias="Authorization", default=None),
    db: AsyncSession = Depends(get_db),
):
    """Return the current authenticated user. Clerk-only with auto-create fallback."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = authorization.removeprefix("Bearer ")

    user_id = None
    user_email = None
    user_name = None

    # Try Clerk token first
    if is_clerk_token(token):
        try:
            payload = await decode_clerk_token(token)
            user_id = extract_clerk_user_id(payload)
            user_email = extract_clerk_user_email(payload)
        except ValueError as e:
            raise HTTPException(status_code=401, detail=f"Invalid Clerk token: {e}")
    else:
        raise HTTPException(status_code=401, detail="Clerk token required")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token: no user ID")

    # Look up user by ID
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    # Auto-create user if not exists (webhook race condition mitigation)
    if not user:
        if not user_email and user_id:
            clerk_user = await fetch_clerk_user_details(user_id)
            if clerk_user:
                user_email = clerk_user.get("email")
                user_name = clerk_user.get("name") or user_name

        if user_email:
            user = User(
                id=user_id,
                email=user_email,
                name=user_name or user_email.split("@")[0],
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role.value,
        created_at=user.created_at,
    )
