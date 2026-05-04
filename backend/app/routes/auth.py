import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token, decode_token, hash_password, verify_password
from app.config import settings
from app.database import get_db
from app.models import OAuthAccount, PasswordResetToken, User
from app.oauth import PROVIDER_CONFIGS, VALID_PROVIDERS, build_authorize_url, create_state
from app.rate_limit import login_limiter, password_reset_limiter, register_limiter
from app.schemas import TokenResponse, UserLogin, UserRegister, UserResponse

router = APIRouter()


def _get_current_user_id(authorization: str = Header(alias="Authorization")) -> str:
    """Extract user_id from JWT in Authorization header. Raises 401 on failure."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = authorization.removeprefix("Bearer ")
    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: UserRegister, request: Request, db: AsyncSession = Depends(get_db)):
    """Register a new user account."""
    client_ip = request.client.host if request.client else "unknown"
    if not register_limiter.is_allowed(client_ip):
        retry = register_limiter.retry_after(client_ip)
        raise HTTPException(status_code=429, detail=f"Too many registration attempts. Try again in {retry}s.")
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=body.email,
        name=body.name,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    await db.commit()

    token = create_access_token(user_id=str(user.id), role=user.role.value)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    """Authenticate and return a JWT."""
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{client_ip}:{body.email}"
    if not login_limiter.is_allowed(rate_key):
        retry = login_limiter.retry_after(rate_key)
        raise HTTPException(status_code=429, detail=f"Too many login attempts. Try again in {retry}s.")
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(user_id=str(user.id), role=user.role.value)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def get_me(authorization: str = Header(alias="Authorization"), db: AsyncSession = Depends(get_db)):
    """Return the current authenticated user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = authorization.removeprefix("Bearer ")
    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")
    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return UserResponse(id=user.id, email=user.email, name=user.name, role=user.role.value, created_at=user.created_at)


@router.get("/me/oauth/link/{provider}")
async def oauth_link(provider: str, authorization: str = Header(alias="Authorization")):
    """Initiate linking: redirect to provider for authorization."""
    if provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
    user_id = _get_current_user_id(authorization)

    config = PROVIDER_CONFIGS[provider]
    if not config["client_id"]():
        raise HTTPException(status_code=503, detail=f"{provider} OAuth is not configured")

    redirect_uri = f"{settings.base_url}/api/auth/oauth/{provider}/callback"
    state = create_state(provider, link_user_id=user_id)
    url = build_authorize_url(provider, redirect_uri, state)
    return RedirectResponse(url)


@router.delete("/me/oauth/{provider}")
async def oauth_unlink(
    provider: str,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Remove a linked OAuth provider from the current user."""
    if provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
    user_id = _get_current_user_id(authorization)

    result = await db.execute(
        select(OAuthAccount).where(and_(OAuthAccount.provider == provider, OAuthAccount.user_id == user_id))
    )
    oauth_account = result.scalar_one_or_none()
    if not oauth_account:
        raise HTTPException(status_code=404, detail="Provider not linked to your account")

    # Check if unlinking would strand the user
    result = await db.execute(select(User).where(User.id == user_id))
    user_obj = result.scalar_one_or_none()
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")
    result = await db.execute(select(OAuthAccount).where(OAuthAccount.user_id == user_id))
    oauth_count = len(result.scalars().all())
    has_password = user_obj.password_hash is not None

    if oauth_count <= 1 and not has_password:
        raise HTTPException(
            status_code=400,
            detail="Cannot disconnect your only login method. Set a password first.",
        )

    await db.delete(oauth_account)
    await db.commit()
    return {"ok": True}


@router.get("/me/oauth")
async def list_linked_providers(
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """List OAuth providers linked to the current user."""
    user_id = _get_current_user_id(authorization)

    result = await db.execute(select(OAuthAccount).where(OAuthAccount.user_id == user_id))
    accounts = result.scalars().all()
    result = await db.execute(select(User).where(User.id == user_id))
    user_obj = result.scalar_one_or_none()

    return {
        "linked": [a.provider for a in accounts],
        "has_password": user_obj.password_hash is not None if user_obj else False,
    }


# --- Password Reset ---


@router.post("/forgot-password")
async def forgot_password(body: dict, request: Request, db: AsyncSession = Depends(get_db)):
    """Request a password reset link. Always returns 200 to prevent email enumeration."""
    email = body.get("email", "")
    client_ip = request.client.host if request.client else "unknown"
    if not password_reset_limiter.is_allowed(client_ip):
        return {"ok": True, "message": "If that email exists, a reset link has been sent."}

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        return {"ok": True, "message": "If that email exists, a reset link has been sent."}

    token = secrets.token_urlsafe(48)
    reset = PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    db.add(reset)
    await db.commit()

    reset_url = f"{settings.frontend_url}/auth?reset_token={token}"
    try:
        from app.email_service import send_email

        await send_email(
            to=user.email,
            subject="Password Reset - Hack the Valley",
            body=f"Hi {user.name},\n\nClick the link below to reset your password:\n{reset_url}\n\nThis link expires in 1 hour.\n\nHack the Valley Team",
            db=db,
        )
    except Exception:
        pass

    return {"ok": True, "message": "If that email exists, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(body: dict, db: AsyncSession = Depends(get_db)):
    """Reset password using a valid token."""
    token = body.get("token", "")
    new_password = body.get("password", "")
    if len(new_password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")

    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token == token,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > datetime.now(UTC),
        )
    )
    reset_token = result.scalar_one_or_none()
    if not reset_token:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    result = await db.execute(select(User).where(User.id == reset_token.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    user.password_hash = hash_password(new_password)
    reset_token.used_at = datetime.now(UTC)
    await db.commit()

    return {"ok": True, "message": "Password has been reset successfully"}
