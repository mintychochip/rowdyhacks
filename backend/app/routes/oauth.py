"""OAuth routes: authorize and callback for provider login flow."""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, OAuthAccount
from app.auth import create_access_token
from app.oauth import (
    VALID_PROVIDERS,
    PROVIDER_CONFIGS,
    build_authorize_url,
    create_state,
    consume_state,
    exchange_code,
    fetch_user_info,
    build_name_fallback,
)
from sqlalchemy.exc import IntegrityError

from app.config import settings

router = APIRouter()


def _frontend_redirect(token: str | None = None, error: str | None = None) -> RedirectResponse:
    """Build a redirect to the frontend callback page."""
    frontend_origin = settings.frontend_url
    if error:
        return RedirectResponse(f"{frontend_origin}/#/auth/callback?error={error}")
    return RedirectResponse(f"{frontend_origin}/#/auth/callback?token={token}")


@router.get("/{provider}/authorize")
async def oauth_authorize(provider: str):
    """Redirect to the provider's OAuth authorization page."""
    if provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    config = PROVIDER_CONFIGS[provider]
    if not config["client_id"]():
        raise HTTPException(status_code=503, detail=f"{provider} OAuth is not configured")

    redirect_uri = f"{settings.base_url}/api/auth/oauth/{provider}/callback"
    state = create_state(provider)
    url = build_authorize_url(provider, redirect_uri, state)
    return RedirectResponse(url)


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str | None = Query(None),
    state: str = Query(...),
    error: str | None = Query(None),
    user: str | None = Query(None),  # Apple: user's name (JSON) on first auth only
    db: AsyncSession = Depends(get_db),
):
    """Handle OAuth callback: exchange code, fetch user info, login or create account."""
    # Provider may redirect with error if user denied consent
    if error:
        return _frontend_redirect(error="oauth_denied")

    if provider not in VALID_PROVIDERS:
        return _frontend_redirect(error="unknown_provider")

    if not code:
        return _frontend_redirect(error="provider_error")

    state_payload = consume_state(state)
    if state_payload is None:
        return _frontend_redirect(error="invalid_state")

    link_user_id = state_payload.get("link_user_id")
    redirect_uri = f"{settings.base_url}/api/auth/oauth/{provider}/callback"

    try:
        token_response = await exchange_code(provider, code, redirect_uri)
    except ValueError:
        return _frontend_redirect(error="provider_error")

    try:
        info = await fetch_user_info(provider, token_response, apple_name=user)
    except ValueError:
        return _frontend_redirect(error="provider_error")

    provider_user_id = info.get("provider_user_id", "")
    provider_email = info.get("email", "")

    if not provider_user_id:
        return _frontend_redirect(error="provider_error")
    if not provider_email:
        return _frontend_redirect(error="no_email")

    # Step 1: Find existing OAuthAccount
    result = await db.execute(
        select(OAuthAccount).where(
            and_(
                OAuthAccount.provider == provider,
                OAuthAccount.provider_user_id == provider_user_id,
            )
        )
    )
    oauth_account = result.scalar_one_or_none()

    if oauth_account:
        result = await db.execute(select(User).where(User.id == oauth_account.user_id))
        user_obj = result.scalar_one_or_none()
        if not user_obj:
            return _frontend_redirect(error="user_not_found")
        token = create_access_token(user_id=str(user_obj.id), role=user_obj.role.value)
        return _frontend_redirect(token=token)

    # If linking to a specific user
    if link_user_id:
        result = await db.execute(select(User).where(User.id == link_user_id))
        user_obj = result.scalar_one_or_none()
        if not user_obj:
            return _frontend_redirect(error="user_not_found")
        new_link = OAuthAccount(
            provider=provider,
            provider_user_id=provider_user_id,
            provider_email=provider_email,
            user_id=user_obj.id,
        )
        db.add(new_link)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            return _frontend_redirect(error="provider_error")
        token = create_access_token(user_id=str(user_obj.id), role=user_obj.role.value)
        return _frontend_redirect(token=token)

    # Step 2: Auto-link by email
    if provider_email:
        result = await db.execute(select(User).where(User.email == provider_email))
        user_obj = result.scalar_one_or_none()
        if user_obj:
            new_link = OAuthAccount(
                provider=provider,
                provider_user_id=provider_user_id,
                provider_email=provider_email,
                user_id=user_obj.id,
            )
            db.add(new_link)
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()
                return _frontend_redirect(error="provider_error")
            token = create_access_token(user_id=str(user_obj.id), role=user_obj.role.value)
            return _frontend_redirect(token=token)

    # Step 3: Create new user (email is guaranteed non-empty from check above)
    user_obj = User(
        email=provider_email,
        name=build_name_fallback(provider, info),
        password_hash=None,
    )
    db.add(user_obj)
    await db.flush()

    new_link = OAuthAccount(
        provider=provider,
        provider_user_id=provider_user_id,
        provider_email=provider_email,
        user_id=user_obj.id,
    )
    db.add(new_link)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return _frontend_redirect(error="provider_error")

    token = create_access_token(user_id=str(user_obj.id), role=user_obj.role.value)
    return _frontend_redirect(token=token)
