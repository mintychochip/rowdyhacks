"""Self-hosted auth routes: local password login, registration, OAuth, token refresh, and password reset."""

import logging
from datetime import UTC, datetime, timedelta
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    create_access_token,
    create_refresh_token,
    generate_reset_token,
    get_current_user,
    hash_password,
    hash_reset_token,
    revoke_refresh_token,
    store_refresh_token,
    validate_password,
    verify_password,
    verify_refresh_token,
)
from app.config import settings
from app.database import get_db
from app.email_service import send_email
from app.models import OAuthProvider, User, UserRole
from app.schemas import UserResponse

router = APIRouter()
logger = logging.getLogger(__name__)


# --- Request models ---


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


# --- Helpers ---


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=False,  # True in production
        samesite="strict",
        max_age=7 * 24 * 60 * 60,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.set_cookie(
        key="refresh_token",
        value="",
        httponly=True,
        secure=False,
        samesite="strict",
        max_age=0,
    )


async def _require_organizer_exists(db: AsyncSession) -> None:
    """Block registration if no organizer exists in the DB."""
    result = await db.execute(select(User).where(User.role == UserRole.organizer).limit(1))
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration is blocked until an organizer account exists",
        )


# --- Routes ---


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Register a new participant account."""
    await _require_organizer_exists(db)

    if not validate_password(body.password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters with uppercase, lowercase, and digit",
        )

    # Check duplicate email
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=body.email,
        name=body.name,
        password_hash=hash_password(body.password),
        role=UserRole.participant,
        email_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info("Registered new user: %s", user.email)
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role.value,
    )


@router.post("/login")
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate with email and password."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    access_token = create_access_token({"sub": user.id, "email": user.email, "role": user.role.value})
    refresh_token = create_refresh_token()
    await store_refresh_token(db, user.id, refresh_token)

    _set_refresh_cookie(response, refresh_token)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post("/refresh")
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Rotate refresh token and issue a new access token."""
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token provided",
        )

    rt = await verify_refresh_token(db, refresh_token)
    if not rt:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Load user
    result = await db.execute(select(User).where(User.id == rt.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Revoke old refresh token
    await revoke_refresh_token(db, refresh_token)

    # Issue new tokens
    access_token = create_access_token({"sub": user.id, "email": user.email, "role": user.role.value})
    new_refresh_token = create_refresh_token()
    await store_refresh_token(db, user.id, new_refresh_token)

    _set_refresh_cookie(response, new_refresh_token)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post("/logout")
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Revoke refresh token and clear cookie."""
    if refresh_token:
        await revoke_refresh_token(db, refresh_token)

    _clear_refresh_cookie(response)
    return {"detail": "Logged out"}


@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Request a password reset link. Always returns 200 to prevent enumeration."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user:
        raw_token = generate_reset_token()
        user.password_reset_token_hash = hash_reset_token(raw_token)
        user.password_reset_expires = datetime.now(UTC) + timedelta(hours=1)
        await db.commit()

        reset_url = f"{settings.frontend_url}/reset-password?token={raw_token}"
        try:
            await send_email(body.email, "password_reset", {"reset_url": reset_url})
        except Exception:
            logger.exception("Failed to send password reset email to %s", body.email)

    return {"detail": "If an account with that email exists, a reset link has been sent"}


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Reset password using a valid reset token."""
    if not validate_password(body.new_password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters with uppercase, lowercase, and digit",
        )

    token_hash = hash_reset_token(body.token)
    result = await db.execute(
        select(User).where(
            User.password_reset_token_hash == token_hash,
            User.password_reset_expires > datetime.now(UTC),
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user.password_hash = hash_password(body.new_password)
    user.password_reset_token_hash = None
    user.password_reset_expires = None
    await db.commit()

    return {"detail": "Password has been reset"}


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    """Return the current authenticated user."""
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role.value,
    )


@router.get("/providers")
async def list_providers(db: AsyncSession = Depends(get_db)):
    """List active OAuth providers."""
    result = await db.execute(select(OAuthProvider).where(OAuthProvider.is_active.is_(True)))
    providers = result.scalars().all()
    return [{"name": p.name, "display_name": p.display_name} for p in providers]
