from fastapi import APIRouter, Depends, HTTPException, Header, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, OAuthAccount
from app.schemas import UserRegister, UserLogin, TokenResponse, UserResponse
from app.auth import hash_password, verify_password, create_access_token, decode_token
from app.oauth import VALID_PROVIDERS, PROVIDER_CONFIGS, build_authorize_url, create_state
from app.config import settings

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
    return payload["sub"]


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: UserRegister, db: AsyncSession = Depends(get_db)):
    """Register a new user account."""
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
async def login(body: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authenticate and return a JWT."""
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
        select(OAuthAccount).where(
            and_(OAuthAccount.provider == provider, OAuthAccount.user_id == user_id)
        )
    )
    oauth_account = result.scalar_one_or_none()
    if not oauth_account:
        raise HTTPException(status_code=404, detail="Provider not linked to your account")

    # Check if unlinking would strand the user
    result = await db.execute(select(User).where(User.id == user_id))
    user_obj = result.scalar_one()
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
    user_obj = result.scalar_one()

    return {"linked": [a.provider for a in accounts], "has_password": user_obj.password_hash is not None}
