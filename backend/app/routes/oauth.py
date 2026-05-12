import logging
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    create_access_token,
    create_refresh_token,
    decrypt_secret,
    encrypt_secret,
    store_refresh_token,
)
from app.config import settings
from app.database import get_db
from app.models import OAuthAccount, OAuthProvider, User, UserRole

router = APIRouter(prefix="/api/auth/oauth", tags=["oauth"])
logger = logging.getLogger(__name__)

OAUTH_PRESETS = {
    "github": {
        "display_name": "GitHub",
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "scope": "read:user user:email",
    },
    "google": {
        "display_name": "Google",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://openidconnect.googleapis.com/v1/userinfo",
        "scope": "openid email profile",
    },
}


@router.get("/{provider}/login")
async def oauth_login(provider: str, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(OAuthProvider).where(OAuthProvider.name == provider, OAuthProvider.is_active.is_(True))
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="OAuth provider not found or inactive")

    redirect_uri = f"{settings.base_url}/api/auth/oauth/{provider}/callback"
    url = f"{p.authorize_url}?client_id={p.client_id}&redirect_uri={redirect_uri}&response_type=code&scope={p.scope}"
    return {"authorization_url": url}


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OAuthProvider).where(OAuthProvider.name == provider, OAuthProvider.is_active.is_(True))
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Provider not found or inactive")

    client_secret = decrypt_secret(p.client_secret_encrypted)
    redirect_uri = f"{settings.base_url}/api/auth/oauth/{provider}/callback"

    # Exchange code for token
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            p.token_url,
            data={
                "grant_type": "authorization_code",
                "client_id": p.client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
        )
    if token_res.status_code != 200:
        logger.error(f"OAuth token exchange failed: {token_res.text}")
        raise HTTPException(status_code=400, detail="OAuth token exchange failed")

    token_data = token_res.json()
    access_token = token_data.get("access_token")

    # Fetch user info
    async with httpx.AsyncClient() as client:
        user_res = await client.get(
            p.userinfo_url,
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if user_res.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch user info")

    userinfo = user_res.json()
    email = userinfo.get("email")
    provider_user_id_raw = userinfo.get("id") or userinfo.get("sub")
    if not provider_user_id_raw:
        raise HTTPException(status_code=400, detail="OAuth provider did not return user ID")
    provider_user_id = str(provider_user_id_raw)

    if not email:
        raise HTTPException(status_code=400, detail="OAuth provider did not return email")

    # Find or create user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            email=email,
            name=userinfo.get("name") or email.split("@")[0],
            role=UserRole.participant,
            email_verified=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # Link OAuth account
    existing_oauth = await db.execute(
        select(OAuthAccount).where(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_user_id == provider_user_id,
        )
    )
    if not existing_oauth.scalar_one_or_none():
        oauth_acc = OAuthAccount(
            provider=provider,
            provider_user_id=provider_user_id,
            provider_email=email,
            user_id=user.id,
            access_token_encrypted=encrypt_secret(access_token),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        db.add(oauth_acc)
        await db.commit()

    # Issue JWT
    jwt_token = create_access_token(
        {
            "sub": user.id,
            "email": user.email,
            "role": user.role.value,
        }
    )
    refresh_token = create_refresh_token()
    await store_refresh_token(db, user.id, refresh_token)

    # Redirect to frontend with token
    redirect_url = f"{settings.frontend_url}/auth/callback?token={jwt_token}&refresh={refresh_token}"
    return {"redirect_url": redirect_url, "access_token": jwt_token}
