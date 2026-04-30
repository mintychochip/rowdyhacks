# OAuth Social Login with Account Linking — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Google, GitHub, Discord, and Apple OAuth login with account linking to the existing email/password JWT auth system.

**Architecture:** A new `oauth.py` module handles provider-specific OAuth flows (authorize URL building, code exchange, user info fetching) and the login-or-create + linking logic. A new `routes/oauth.py` file exposes the authorize/callback endpoints. Account management routes (link, unlink, list) go in the existing `routes/auth.py` to keep clean `/api/auth/me/oauth` paths. A new `OAuthAccount` model tracks linked provider accounts. Frontend adds social login buttons, an OAuth callback page, and linked-accounts management in a settings page.

**Tech Stack:** FastAPI, httpx, python-jose (already used for JWT), React with React Router (hash routing), existing theme system.

---

## Chunk 1: Backend Model, Config, and OAuth Logic Module

### Task 1.1: Add OAuthAccount model and make password_hash nullable

**Files:**
- Modify: `backend/app/models.py`

- [ ] **Step 1: Add OAuthAccount model and update User.password_hash**

In `backend/app/models.py`, after the `User` class, add:

```python
class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    provider = Column(String(20), nullable=False)
    provider_user_id = Column(String(255), nullable=False)
    provider_email = Column(String(320), nullable=True)
    user_id = Column(Guid, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_oauth_accounts_provider_user", "provider", "provider_user_id", unique=True),
    )

    user = relationship("User", back_populates="oauth_accounts")
```

In the `User` class, change:
```python
password_hash = Column(String(128), nullable=False)  # OLD
password_hash = Column(String(128), nullable=True)   # NEW
```

And add the relationship to User:
```python
oauth_accounts = relationship("OAuthAccount", back_populates="user", cascade="all, delete-orphan")
```

- [ ] **Step 2: Verify model imports**

Run: `cd backend && python -c "from app.models import Base, OAuthAccount; print('OAuthAccount model imported OK')"`
Expected: "OAuthAccount model imported OK"

- [ ] **Step 3: Commit**

```bash
git add backend/app/models.py
git commit -m "feat: add OAuthAccount model, make User.password_hash nullable"
```

---

### Task 1.2: Add OAuth config settings

**Files:**
- Modify: `backend/app/config.py`

- [ ] **Step 1: Add provider config fields to Settings**

Add after the `secret_key` field in `Settings`:

```python
# OAuth provider credentials
google_client_id: str = Field(default="", description="Google OAuth client ID")
google_client_secret: str = Field(default="", description="Google OAuth client secret")
github_client_id: str = Field(default="", description="GitHub OAuth client ID")
github_client_secret: str = Field(default="", description="GitHub OAuth client secret")
discord_client_id: str = Field(default="", description="Discord OAuth client ID")
discord_client_secret: str = Field(default="", description="Discord OAuth client secret")
apple_client_id: str = Field(default="", description="Apple Sign In service ID")
apple_team_id: str = Field(default="", description="Apple Developer Team ID")
apple_key_id: str = Field(default="", description="Apple private key ID")
apple_private_key_path: str = Field(default="", description="Path to Apple .p8 private key file")
```

- [ ] **Step 2: Verify settings import**

Run: `cd backend && python -c "from app.config import settings; print(settings.google_client_id)"`
Expected: Prints empty string (default).

- [ ] **Step 3: Commit**

```bash
git add backend/app/config.py
git commit -m "feat: add OAuth provider config fields to Settings"
```

---

### Task 1.3: Create OAuth logic module (state store + provider configs)

**Files:**
- Create: `backend/app/oauth.py`

- [ ] **Step 1: Write the module**

```python
"""OAuth provider logic: state management, provider configs, token exchange, user info."""

import secrets
import time
from typing import Any

import httpx
from fastapi.responses import RedirectResponse

from app.config import settings

# ── State Store (CSRF protection) ──────────────────────────────

_state_store: dict[str, tuple[float, dict[str, Any]]] = {}

def _cleanup_expired() -> None:
    """Lazily remove expired state entries."""
    now = time.time()
    expired = [k for k, (exp, _) in _state_store.items() if now > exp]
    for k in expired:
        _state_store.pop(k, None)


def create_state(provider: str, link_user_id: str | None = None) -> str:
    """Generate a CSRF state nonce and store it with a 10-minute TTL."""
    _cleanup_expired()
    nonce = secrets.token_hex(32)
    _state_store[nonce] = (
        time.time() + 600,  # 10 minutes
        {"provider": provider, "link_user_id": link_user_id},
    )
    return nonce


def consume_state(nonce: str) -> dict[str, Any] | None:
    """Validate and consume a state nonce. Returns payload or None if invalid/expired."""
    _cleanup_expired()
    entry = _state_store.pop(nonce, None)
    if entry is None:
        return None
    expires_at, payload = entry
    if time.time() > expires_at:
        return None
    return payload


# ── Provider Configs ──────────────────────────────────────────

PROVIDER_CONFIGS = {
    "google": {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "scopes": "openid profile email",
        "client_id": lambda: settings.google_client_id,
        "client_secret": lambda: settings.google_client_secret,
    },
    "github": {
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "scopes": "user:email",
        "client_id": lambda: settings.github_client_id,
        "client_secret": lambda: settings.github_client_secret,
    },
    "discord": {
        "authorize_url": "https://discord.com/api/oauth2/authorize",
        "token_url": "https://discord.com/api/oauth2/token",
        "userinfo_url": "https://discord.com/api/users/@me",
        "scopes": "identify email",
        "client_id": lambda: settings.discord_client_id,
        "client_secret": lambda: settings.discord_client_secret,
    },
    "apple": {
        "authorize_url": "https://appleid.apple.com/auth/authorize",
        "token_url": "https://appleid.apple.com/auth/token",
        "scopes": "name email",
        "client_id": lambda: settings.apple_client_id,
    },
}

VALID_PROVIDERS = list(PROVIDER_CONFIGS.keys())


# ── Helpers ────────────────────────────────────────────────────

def build_authorize_url(provider: str, redirect_uri: str, state: str) -> str:
    """Build the provider's OAuth authorization URL."""
    config = PROVIDER_CONFIGS[provider]
    from urllib.parse import urlencode
    params = {
        "client_id": config["client_id"](),
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": config["scopes"],
        "response_type": "code",
    }
    if provider == "apple":
        params["response_mode"] = "form_post"
    return f"{config['authorize_url']}?{urlencode(params)}"


def _build_apple_client_secret() -> str:
    """Build a JWT client_secret for Apple's token endpoint."""
    from pathlib import Path
    from datetime import datetime, timedelta, timezone
    from jose import jwt as jose_jwt

    key_path = Path(settings.apple_private_key_path)
    if not key_path.exists():
        raise RuntimeError(f"Apple private key not found at {settings.apple_private_key_path}")

    private_key = key_path.read_text()
    now = datetime.now(timezone.utc)
    payload = {
        "iss": settings.apple_team_id,
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "aud": "https://appleid.apple.com",
        "sub": settings.apple_client_id,
    }
    headers = {"alg": "ES256", "kid": settings.apple_key_id}
    return jose_jwt.encode(payload, private_key, algorithm="ES256", headers=headers)


async def exchange_code(provider: str, code: str, redirect_uri: str) -> dict[str, Any]:
    """Exchange an OAuth authorization code for an access token."""
    config = PROVIDER_CONFIGS[provider]
    token_data: dict[str, str] = {
        "client_id": config["client_id"](),
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    headers = {"Accept": "application/json"}
    if provider == "apple":
        token_data["client_secret"] = _build_apple_client_secret()
    elif provider == "github":
        token_data["client_secret"] = config["client_secret"]()
    else:
        token_data["client_secret"] = config["client_secret"]()

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(config["token_url"], data=token_data, headers=headers)
        if resp.status_code != 200:
            raise ValueError(f"Token exchange failed ({resp.status_code}): {resp.text[:200]}")
        return resp.json()


async def fetch_user_info(provider: str, token_response: dict[str, Any]) -> dict[str, Any]:
    """Fetch user info from the provider using the access token."""
    config = PROVIDER_CONFIGS[provider]

    if provider == "apple":
        from jose import jwt as jose_jwt
        id_token = token_response.get("id_token")
        if not id_token:
            raise ValueError("Apple did not return an id_token")
        decoded = jose_jwt.decode(id_token, options={"verify_signature": False})
        email = decoded.get("email", "")
        name_obj = token_response.get("user", {})
        first_name = name_obj.get("name", {}).get("firstName", "") if isinstance(name_obj, dict) else ""
        last_name = name_obj.get("name", {}).get("lastName", "") if isinstance(name_obj, dict) else ""
        full_name = f"{first_name} {last_name}".strip()
        return {"provider_user_id": decoded.get("sub", ""), "email": email, "name": full_name}

    headers = {"Authorization": f"Bearer {token_response['access_token']}"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        if provider == "github":
            user_resp = await client.get(config["userinfo_url"], headers=headers)
            if user_resp.status_code != 200:
                raise ValueError(f"GitHub user endpoint failed ({user_resp.status_code})")
            user_data = user_resp.json()
            email_resp = await client.get("https://api.github.com/user/emails", headers=headers)
            email = ""
            if email_resp.status_code == 200:
                for e in email_resp.json():
                    if e.get("primary") and e.get("verified"):
                        email = e["email"]
                        break
            return {
                "provider_user_id": str(user_data.get("id", "")),
                "email": email,
                "name": user_data.get("login", "") or user_data.get("name", ""),
            }
        elif provider == "discord":
            resp = await client.get(config["userinfo_url"], headers=headers)
            if resp.status_code != 200:
                raise ValueError(f"Discord user endpoint failed ({resp.status_code})")
            user_data = resp.json()
            return {
                "provider_user_id": str(user_data.get("id", "")),
                "email": user_data.get("email", ""),
                "name": user_data.get("username", ""),
            }
        else:  # google
            resp = await client.get(config["userinfo_url"], headers=headers)
            if resp.status_code != 200:
                raise ValueError(f"Google user endpoint failed ({resp.status_code})")
            user_data = resp.json()
            return {
                "provider_user_id": str(user_data.get("id", "")),
                "email": user_data.get("email", ""),
                "name": user_data.get("name", ""),
            }


def build_name_fallback(provider: str, info: dict[str, Any]) -> str:
    """Return a display name, with fallbacks for missing data."""
    name = info.get("name", "").strip()
    if name:
        return name
    email = info.get("email", "")
    if email and "@" in email:
        return email.split("@")[0]
    return "Hacker"
```

- [ ] **Step 2: Verify import**

Run: `cd backend && python -c "from app.oauth import build_authorize_url, create_state, consume_state; print('oauth module OK')"`
Expected: "oauth module OK"

- [ ] **Step 3: Commit**

```bash
git add backend/app/oauth.py
git commit -m "feat: add OAuth logic module with state store and provider configs"
```

---

## Chunk 2: Backend OAuth Routes

### Task 2.1: Create OAuth routes (authorize + callback)

**Files:**
- Create: `backend/app/routes/oauth.py`

- [ ] **Step 1: Write the routes module**

```python
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
    build_authorize_url,
    create_state,
    consume_state,
    exchange_code,
    fetch_user_info,
    build_name_fallback,
)
from app.config import settings

router = APIRouter()


def _frontend_redirect(token: str | None = None, error: str | None = None) -> RedirectResponse:
    """Build a redirect to the frontend callback page."""
    frontend_origin = settings.base_url
    if error:
        return RedirectResponse(f"{frontend_origin}/#/auth/callback?error={error}")
    return RedirectResponse(f"{frontend_origin}/#/auth/callback?token={token}")


@router.get("/{provider}/authorize")
async def oauth_authorize(provider: str):
    """Redirect to the provider's OAuth authorization page."""
    if provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    from app.oauth import PROVIDER_CONFIGS
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
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Handle OAuth callback: exchange code, fetch user info, login or create account."""
    if provider not in VALID_PROVIDERS:
        return _frontend_redirect(error="unknown_provider")

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
        info = await fetch_user_info(provider, token_response)
    except ValueError:
        return _frontend_redirect(error="provider_error")

    provider_user_id = info.get("provider_user_id", "")
    provider_email = info.get("email", "")

    if not provider_user_id:
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
        user = result.scalar_one()
        token = create_access_token(user_id=str(user.id), role=user.role.value)
        return _frontend_redirect(token=token)

    # If linking to a specific user
    if link_user_id:
        result = await db.execute(select(User).where(User.id == link_user_id))
        user = result.scalar_one_or_none()
        if not user:
            return _frontend_redirect(error="user_not_found")
        new_link = OAuthAccount(
            provider=provider,
            provider_user_id=provider_user_id,
            provider_email=provider_email or None,
            user_id=user.id,
        )
        db.add(new_link)
        await db.commit()
        token = create_access_token(user_id=str(user.id), role=user.role.value)
        return _frontend_redirect(token=token)

    # Step 2: Auto-link by email
    if provider_email:
        result = await db.execute(select(User).where(User.email == provider_email))
        user = result.scalar_one_or_none()
        if user:
            new_link = OAuthAccount(
                provider=provider,
                provider_user_id=provider_user_id,
                provider_email=provider_email,
                user_id=user.id,
            )
            db.add(new_link)
            await db.commit()
            token = create_access_token(user_id=str(user.id), role=user.role.value)
            return _frontend_redirect(token=token)

    # Step 3: Create new user
    user = User(
        email=provider_email or f"{provider}_{provider_user_id}@placeholder.local",
        name=build_name_fallback(provider, info),
        password_hash=None,
    )
    db.add(user)
    await db.flush()

    new_link = OAuthAccount(
        provider=provider,
        provider_user_id=provider_user_id,
        provider_email=provider_email or None,
        user_id=user.id,
    )
    db.add(new_link)
    await db.commit()

    token = create_access_token(user_id=str(user.id), role=user.role.value)
    return _frontend_redirect(token=token)
```

- [ ] **Step 2: Verify route imports**

Run: `cd backend && python -c "from app.routes.oauth import router; print('routes OK')"`
Expected: "routes OK"

- [ ] **Step 3: Commit**

```bash
git add backend/app/routes/oauth.py
git commit -m "feat: add OAuth authorize and callback routes"
```

---

### Task 2.2: Add account management OAuth routes to auth.py

**Files:**
- Modify: `backend/app/routes/auth.py`

These routes belong under `/api/auth` (the existing auth router prefix), producing clean paths like `/api/auth/me/oauth`.

- [ ] **Step 1: Add link, unlink, and list routes**

Add at the end of `backend/app/routes/auth.py`:

```python
from app.models import OAuthAccount
from app.oauth import VALID_PROVIDERS, PROVIDER_CONFIGS, build_authorize_url, create_state, consume_state


@router.get("/me/oauth/link/{provider}")
async def oauth_link(provider: str, authorization: str = Header(alias="Authorization")):
    """Initiate linking: redirect to provider for authorization."""
    if provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = authorization.removeprefix("Bearer ")
    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")

    config = PROVIDER_CONFIGS[provider]
    if not config["client_id"]():
        raise HTTPException(status_code=503, detail=f"{provider} OAuth is not configured")

    redirect_uri = f"{settings.base_url}/api/auth/oauth/{provider}/callback"
    state = create_state(provider, link_user_id=payload["sub"])
    url = build_authorize_url(provider, redirect_uri, state)
    from fastapi.responses import RedirectResponse
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

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = authorization.removeprefix("Bearer ")
    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = payload["sub"]

    result = await db.execute(
        select(OAuthAccount).where(
            and_(
                OAuthAccount.provider == provider,
                OAuthAccount.user_id == user_id,
            )
        )
    )
    # Note: and_ is imported from sqlalchemy
    from sqlalchemy import and_
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
    user = result.scalar_one()
    result = await db.execute(select(OAuthAccount).where(OAuthAccount.user_id == user_id))
    oauth_count = len(result.scalars().all())
    has_password = user.password_hash is not None

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
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = authorization.removeprefix("Bearer ")
    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = payload["sub"]

    result = await db.execute(select(OAuthAccount).where(OAuthAccount.user_id == user_id))
    accounts = result.scalars().all()
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()

    return {"linked": [a.provider for a in accounts], "has_password": user.password_hash is not None}
```

Also update the imports at the top of `auth.py` to add:
```python
from sqlalchemy import and_
from app.models import OAuthAccount
from app.oauth import VALID_PROVIDERS, PROVIDER_CONFIGS, build_authorize_url, create_state, consume_state
from app.config import settings
```

And add the `RedirectResponse` import:
```python
from fastapi.responses import RedirectResponse
```

Note: The existing route `get_me` manually parses the Authorization header. Extract that into a small helper to avoid repetition:

```python
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
```

Then simplify `get_me` and the new routes to use `_get_current_user_id`.

- [ ] **Step 2: Verify routes import**

Run: `cd backend && python -c "from app.routes.auth import router; print('auth routes OK')"`
Expected: "auth routes OK"

- [ ] **Step 3: Commit**

```bash
git add backend/app/routes/auth.py
git commit -m "feat: add OAuth account management routes (link, unlink, list) to auth router"
```

---

### Task 2.3: Wire OAuth routes into main.py

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Add the oauth router**

Add import:
```python
from app.routes.oauth import router as oauth_router
```

Add to app:
```python
app.include_router(oauth_router, prefix="/api/auth/oauth", tags=["oauth"])
```

Resulting routes:
- `GET /api/auth/oauth/{provider}/authorize`
- `GET /api/auth/oauth/{provider}/callback`
- `GET /api/auth/me/oauth/link/{provider}` (from auth router, prefix `/api/auth`)
- `DELETE /api/auth/me/oauth/{provider}` (from auth router)
- `GET /api/auth/me/oauth` (from auth router)

- [ ] **Step 2: Verify app imports**

Run: `cd backend && python -c "from app.main import app; print('app imports OK')"`
Expected: "app imports OK"

- [ ] **Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: wire OAuth routes into main app"
```

---

## Chunk 3: Backend Tests

### Task 3.1: Write unit tests for state store and name fallbacks

**Files:**
- Create: `backend/tests/test_oauth.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for OAuth state store, name fallbacks, and routes."""
import uuid
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy import select

from app.models import User, OAuthAccount, UserRole
from app.auth import hash_password, create_access_token, decode_token
from app.oauth import create_state, consume_state, build_name_fallback


# ── State Store ──────────────────────────────────────────────

def test_create_and_consume_state():
    state = create_state("google")
    payload = consume_state(state)
    assert payload == {"provider": "google", "link_user_id": None}


def test_create_and_consume_state_with_link_user():
    state = create_state("github", link_user_id="user-123")
    payload = consume_state(state)
    assert payload == {"provider": "github", "link_user_id": "user-123"}


def test_consume_nonexistent_state():
    assert consume_state("nonexistent") is None


def test_consume_state_twice_fails():
    state = create_state("discord")
    assert consume_state(state) is not None
    assert consume_state(state) is None


# ── Name Fallbacks ──────────────────────────────────────────

def test_build_name_fallback_uses_name():
    assert build_name_fallback("google", {"name": "Alice"}) == "Alice"


def test_build_name_fallback_uses_email_local_part():
    assert build_name_fallback("google", {"name": "", "email": "alice@example.com"}) == "alice"


def test_build_name_fallback_returns_hacker():
    assert build_name_fallback("google", {"name": "", "email": ""}) == "Hacker"
```

- [ ] **Step 2: Run state and name fallback tests**

Run: `cd backend && python -m pytest tests/test_oauth.py -v`
Expected: All pass.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_oauth.py
git commit -m "test: add OAuth state store and name fallback unit tests"
```

---

### Task 3.2: Write route tests for authorize, callback, unlink, and list

**Files:**
- Modify: `backend/tests/test_oauth.py` (append to existing file)

- [ ] **Step 1: Add route tests**

```python
# ── Route Tests ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_unknown_provider_returns_400(client):
    response = await client.get("/api/auth/oauth/unknown_provider/authorize", follow_redirects=False)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_callback_with_expired_state(client):
    response = await client.get(
        "/api/auth/oauth/google/callback?code=test&state=nonexistent",
        follow_redirects=False,
    )
    assert response.status_code == 307
    assert "error=invalid_state" in response.headers["location"]


@pytest.mark.asyncio
async def test_list_linked_providers(db_session, client):
    user = User(
        id=uuid.uuid4(), email="linktest@test.com", name="LinkTest",
        password_hash=hash_password("pw"), role=UserRole.participant,
    )
    db_session.add(user)
    await db_session.commit()

    token = create_access_token(user_id=str(user.id), role=user.role.value)
    response = await client.get(
        "/api/auth/me/oauth",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() == {"linked": [], "has_password": True}


@pytest.mark.asyncio
async def test_unlink_last_auth_method_fails(db_session, client):
    user = User(
        id=uuid.uuid4(), email="oauthonly@test.com", name="OAuthUser",
        password_hash=None, role=UserRole.participant,
    )
    db_session.add(user)
    await db_session.flush()
    oa = OAuthAccount(
        id=uuid.uuid4(), provider="google", provider_user_id="g123",
        provider_email="oauthonly@test.com", user_id=user.id,
    )
    db_session.add(oa)
    await db_session.commit()

    token = create_access_token(user_id=str(user.id), role=user.role.value)
    response = await client.delete(
        "/api/auth/me/oauth/google",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert "only login method" in response.json()["detail"]


@pytest.mark.asyncio
async def test_unlink_succeeds_when_has_password(db_session, client):
    user = User(
        id=uuid.uuid4(), email="both@test.com", name="BothAuth",
        password_hash=hash_password("pw"), role=UserRole.participant,
    )
    db_session.add(user)
    await db_session.flush()
    oa = OAuthAccount(
        id=uuid.uuid4(), provider="google", provider_user_id="g456",
        provider_email="both@test.com", user_id=user.id,
    )
    db_session.add(oa)
    await db_session.commit()

    token = create_access_token(user_id=str(user.id), role=user.role.value)
    response = await client.delete(
        "/api/auth/me/oauth/google",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}

    result = await db_session.execute(select(OAuthAccount).where(OAuthAccount.user_id == user.id))
    assert len(result.scalars().all()) == 0
```

- [ ] **Step 2: Run route tests**

Run: `cd backend && python -m pytest tests/test_oauth.py -v`
Expected: All tests pass.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_oauth.py
git commit -m "test: add OAuth route tests (authorize, callback, unlink, list)"
```

---

### Task 3.3: Write callback integration tests with mocked httpx

**Files:**
- Modify: `backend/tests/test_oauth.py` (append to existing file)

- [ ] **Step 1: Add mocked callback tests**

```python
# ── Callback integration tests (httpx mocked) ──────────────

@pytest.mark.asyncio
async def test_callback_creates_new_user(client, db_session):
    """Full callback flow: new user via Google OAuth."""
    state = create_state("google")
    token_response = {"access_token": "tok123", "token_type": "bearer"}
    user_info = {"id": "g-user-999", "email": "newuser@gmail.com", "name": "New User"}

    with patch("app.routes.oauth.exchange_code", new=AsyncMock(return_value=token_response)), \
         patch("app.routes.oauth.fetch_user_info", new=AsyncMock(return_value={
             "provider_user_id": "g-user-999",
             "email": "newuser@gmail.com",
             "name": "New User",
         })):
        response = await client.get(
            f"/api/auth/oauth/google/callback?code=test&state={state}",
            follow_redirects=False,
        )

    assert response.status_code == 307
    location = response.headers["location"]
    assert "token=" in location and "error=" not in location

    # Verify user and OAuthAccount were created
    result = await db_session.execute(select(User).where(User.email == "newuser@gmail.com"))
    user = result.scalar_one()
    assert user.name == "New User"
    assert user.password_hash is None

    result = await db_session.execute(
        select(OAuthAccount).where(OAuthAccount.provider_user_id == "g-user-999")
    )
    oa = result.scalar_one()
    assert oa.provider == "google"
    assert oa.user_id == user.id


@pytest.mark.asyncio
async def test_callback_logs_in_existing_oauth_account(client, db_session):
    """Callback with existing OAuthAccount returns JWT for that user."""
    user = User(
        id=uuid.uuid4(), email="existing@test.com", name="Existing",
        password_hash=None, role=UserRole.participant,
    )
    db_session.add(user)
    await db_session.flush()
    oa = OAuthAccount(
        id=uuid.uuid4(), provider="google", provider_user_id="g-existing",
        provider_email="existing@test.com", user_id=user.id,
    )
    db_session.add(oa)
    await db_session.commit()

    state = create_state("google")
    with patch("app.routes.oauth.exchange_code", new=AsyncMock(return_value={"access_token": "tok"})), \
         patch("app.routes.oauth.fetch_user_info", new=AsyncMock(return_value={
             "provider_user_id": "g-existing",
             "email": "existing@test.com",
             "name": "Existing",
         })):
        response = await client.get(
            f"/api/auth/oauth/google/callback?code=test&state={state}",
            follow_redirects=False,
        )

    assert response.status_code == 307
    assert "token=" in response.headers["location"]
    # No new OAuthAccount should be created
    result = await db_session.execute(select(OAuthAccount).where(OAuthAccount.user_id == user.id))
    assert len(result.scalars().all()) == 1


@pytest.mark.asyncio
async def test_callback_auto_links_by_email(client, db_session):
    """Callback auto-links when OAuth email matches existing user email."""
    user = User(
        id=uuid.uuid4(), email="alice@test.com", name="Alice",
        password_hash=hash_password("pw"), role=UserRole.participant,
    )
    db_session.add(user)
    await db_session.commit()

    state = create_state("google")
    with patch("app.routes.oauth.exchange_code", new=AsyncMock(return_value={"access_token": "tok"})), \
         patch("app.routes.oauth.fetch_user_info", new=AsyncMock(return_value={
             "provider_user_id": "g-new-link",
             "email": "alice@test.com",
             "name": "Alice",
         })):
        response = await client.get(
            f"/api/auth/oauth/google/callback?code=test&state={state}",
            follow_redirects=False,
        )

    assert response.status_code == 307
    assert "token=" in response.headers["location"]
    result = await db_session.execute(
        select(OAuthAccount).where(OAuthAccount.provider_user_id == "g-new-link")
    )
    oa = result.scalar_one()
    assert oa.user_id == user.id


@pytest.mark.asyncio
async def test_callback_apple_no_name_fallback(client, db_session):
    """Apple callback where name is absent (subsequent auth)."""
    state = create_state("apple")
    with patch("app.routes.oauth.exchange_code", new=AsyncMock(return_value={"access_token": "tok", "id_token": "x"})), \
         patch("app.routes.oauth.fetch_user_info", new=AsyncMock(return_value={
             "provider_user_id": "apple-sub-1",
             "email": "justin@example.com",
             "name": "",  # no name on subsequent auth
         })):
        response = await client.get(
            f"/api/auth/oauth/apple/callback?code=test&state={state}",
            follow_redirects=False,
        )

    assert response.status_code == 307
    assert "token=" in response.headers["location"]
    result = await db_session.execute(select(User).where(User.email == "justin@example.com"))
    user = result.scalar_one()
    assert user.name == "justin"  # fallback: email local part
    assert user.password_hash is None


@pytest.mark.asyncio
async def test_callback_provider_error_redirects_with_error(client):
    """When exchange_code raises, redirect with provider_error."""
    state = create_state("google")
    with patch("app.routes.oauth.exchange_code", new=AsyncMock(side_effect=ValueError("fail"))):
        response = await client.get(
            f"/api/auth/oauth/google/callback?code=test&state={state}",
            follow_redirects=False,
        )
    assert response.status_code == 307
    assert "error=provider_error" in response.headers["location"]


@pytest.mark.asyncio
async def test_callback_no_email_redirects_with_error(client):
    """When provider returns no provider_user_id, redirect with no_email."""
    state = create_state("github")
    with patch("app.routes.oauth.exchange_code", new=AsyncMock(return_value={"access_token": "tok"})), \
         patch("app.routes.oauth.fetch_user_info", new=AsyncMock(return_value={
             "provider_user_id": "", "email": "", "name": "",
         })):
        response = await client.get(
            f"/api/auth/oauth/github/callback?code=test&state={state}",
            follow_redirects=False,
        )
    assert response.status_code == 307
    assert "error=no_email" in response.headers["location"]


@pytest.mark.asyncio
async def test_link_endpoint_initiates_oauth_flow(client, db_session):
    """GET /me/oauth/link/{provider} redirects to provider."""
    user = User(
        id=uuid.uuid4(), email="linker@test.com", name="Linker",
        password_hash=hash_password("pw"), role=UserRole.participant,
    )
    db_session.add(user)
    await db_session.commit()

    token = create_access_token(user_id=str(user.id), role=user.role.value)
    response = await client.get(
        "/api/auth/me/oauth/link/google",
        headers={"Authorization": f"Bearer {token}"},
        follow_redirects=False,
    )
    assert response.status_code == 307
    assert "accounts.google.com" in response.headers["location"]
```

- [ ] **Step 2: Run callback tests**

Run: `cd backend && python -m pytest tests/test_oauth.py -v`
Expected: All tests pass (12 total).

- [ ] **Step 3: Run full test suite**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All existing tests still pass, new tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_oauth.py
git commit -m "test: add mocked callback integration tests for OAuth login-or-create flow"
```

---

### Task 3.4: Add httpx dependency

**Files:**
- Modify: `backend/requirements.txt` (or `pyproject.toml`)

- [ ] **Step 1: Install httpx**

Run: `cd backend && pip install httpx`

Then run `pip freeze > requirements.txt` or add `httpx` manually to the requirements file.

- [ ] **Step 2: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore: add httpx dependency for OAuth provider API calls"
```

---

## Chunk 4: Frontend API Service + AuthPage

### Task 4.1: Add OAuth API functions

**Files:**
- Modify: `frontend/src/services/api.ts`

- [ ] **Step 1: Add OAuth API functions**

Add at the end of `api.ts`:

```typescript
// OAuth
const API_BASE = '/api';

export const getOAuthAuthorizeUrl = (provider: string) =>
  `${API_BASE}/auth/oauth/${provider}/authorize`;

export const getOAuthLinkUrl = (provider: string) =>
  `${API_BASE}/auth/me/oauth/link/${provider}`;

export const getLinkedAccounts = () =>
  request('/auth/me/oauth');

export const unlinkProvider = (provider: string) =>
  request(`/auth/me/oauth/${provider}`, { method: 'DELETE' });
```

Note: remove the existing top-level `const BASE = '/api';` and use `API_BASE` consistently, or just reuse `BASE`. For this feature, use the existing `BASE` constant (line 1 of api.ts).

- [ ] **Step 2: Verify TypeScript**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/api.ts
git commit -m "feat: add OAuth API functions to frontend service"
```

---

### Task 4.2: Add social login buttons to AuthPage

**Files:**
- Modify: `frontend/src/pages/AuthPage.tsx`

- [ ] **Step 1: Add social login buttons**

Import the authorize URL helper and theme tokens as needed:

```tsx
const API_BASE = '/api';
```

Add after the `</form>` closing tag and before the toggle paragraph:

```tsx
      <div style={{ marginTop: 20, marginBottom: 20 }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16,
        }}>
          <div style={{ flex: 1, height: 1, background: INPUT_BORDER }} />
          <span style={{ color: TEXT_MUTED, fontSize: 13 }}>or continue with</span>
          <div style={{ flex: 1, height: 1, background: INPUT_BORDER }} />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {(['google', 'github', 'discord', 'apple'] as const).map(provider => (
            <a
              key={provider}
              href={`${API_BASE}/auth/oauth/${provider}/authorize`}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                width: '100%', padding: '10px 12px',
                background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`,
                borderRadius: 6, color: TEXT_PRIMARY, fontSize: 14, fontWeight: 500,
                textDecoration: 'none', cursor: 'pointer', boxSizing: 'border-box',
              }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: 20 }}>
                {provider === 'google' ? 'login' : provider === 'github' ? 'code' : provider === 'discord' ? 'chat' : 'fingerprint'}
              </span>
              Sign in with {provider.charAt(0).toUpperCase() + provider.slice(1)}
            </a>
          ))}
        </div>
      </div>
```

- [ ] **Step 2: Add error display from URL params**

The AuthPage should also display errors from the callback flow (e.g., when redirected from `/auth/callback?error=...`). Add a `useEffect` to read `?error=` from the URL:

```tsx
import { useSearchParams } from 'react-router-dom';

// Inside the component, after existing hooks:
const [searchParams] = useSearchParams();
const urlError = searchParams.get('error');

useEffect(() => {
  if (urlError) {
    setError(decodeURIComponent(urlError));
  }
}, [urlError]);
```

Need to add `useEffect` to the import:
```tsx
import { useState, useEffect } from 'react';
```

And `useSearchParams`:
```tsx
import { useNavigate, useSearchParams } from 'react-router-dom';
```

- [ ] **Step 3: Verify TypeScript**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/AuthPage.tsx
git commit -m "feat: add social login buttons and OAuth error display to AuthPage"
```

---

## Chunk 5: Frontend Callback + Linked Accounts UI

### Task 5.1: Create AuthCallback component

**Files:**
- Create: `frontend/src/pages/AuthCallback.tsx`

- [ ] **Step 1: Create the component**

```tsx
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { TEXT_MUTED, PAGE_BG, TEXT_PRIMARY } from '../theme';

export default function AuthCallback() {
  const navigate = useNavigate();

  useEffect(() => {
    const hash = location.hash;
    const queryIndex = hash.indexOf('?');
    if (queryIndex === -1) {
      navigate('/auth?error=no_oauth_data');
      return;
    }
    const query = hash.slice(queryIndex + 1);
    const params = new URLSearchParams(query);
    const token = params.get('token');
    const error = params.get('error');

    if (error) {
      const messages: Record<string, string> = {
        invalid_state: 'Login session expired. Please try again.',
        oauth_denied: 'Login was cancelled.',
        provider_error: 'Could not connect to login provider. Please try again.',
        no_email: 'Your account did not return an email address.',
      };
      const message = messages[error] || 'Login failed. Please try again.';
      navigate(`/auth?error=${encodeURIComponent(message)}`);
      return;
    }

    if (token) {
      localStorage.setItem('auth_token', token);
      window.location.href = '/';
      return;
    }

    navigate('/auth?error=no_oauth_data');
  }, [navigate]);

  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      minHeight: '60vh', background: PAGE_BG,
    }}>
      <div style={{ textAlign: 'center' }}>
        <div className="material-symbols-outlined" style={{
          fontSize: 48, color: TEXT_PRIMARY, marginBottom: 16,
          animation: 'spin 1s linear infinite',
        }}>
          progress_activity
        </div>
        <p style={{ color: TEXT_MUTED }}>Completing sign in...</p>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/AuthCallback.tsx
git commit -m "feat: add OAuth callback page component"
```

---

### Task 5.2: Add AuthCallback route to App.tsx

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Add import and route**

Add import:
```tsx
import AuthCallback from './pages/AuthCallback';
```

Add route inside the `<Route element={<Layout />}>` block:
```tsx
            <Route path="/auth/callback" element={<AuthCallback />} />
```

- [ ] **Step 2: Verify TypeScript**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: add AuthCallback route to App"
```

---

### Task 5.3: Create LinkedAccounts component

**Files:**
- Create: `frontend/src/components/LinkedAccounts.tsx`

- [ ] **Step 1: Create the component**

```tsx
import { useState, useEffect } from 'react';
import { getLinkedAccounts, unlinkProvider, getOAuthLinkUrl } from '../services/api';
import { CARD_BG, TEXT_PRIMARY, TEXT_MUTED, BORDER, INPUT_BORDER, ERROR_TEXT, SUCCESS, TYPO, RADIUS, SPACE } from '../theme';
import { useToast } from '../contexts/ToastContext';

type LinkedState = {
  linked: string[];
  has_password: boolean;
};

const PROVIDER_INFO: Record<string, { label: string; icon: string }> = {
  google: { label: 'Google', icon: 'login' },
  github: { label: 'GitHub', icon: 'code' },
  discord: { label: 'Discord', icon: 'chat' },
  apple: { label: 'Apple', icon: 'fingerprint' },
};

export default function LinkedAccounts() {
  const [state, setState] = useState<LinkedState | null>(null);
  const [loading, setLoading] = useState(true);
  const [unlinking, setUnlinking] = useState<string | null>(null);
  const { showToast } = useToast();

  const fetchState = async () => {
    try {
      const data = await getLinkedAccounts();
      setState(data);
    } catch {
      // Not authenticated or error
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchState(); }, []);

  const handleUnlink = async (provider: string) => {
    setUnlinking(provider);
    try {
      await unlinkProvider(provider);
      setState(prev => prev ? { ...prev, linked: prev.linked.filter(p => p !== provider) } : prev);
      showToast(`${PROVIDER_INFO[provider]?.label || provider} disconnected.`);
    } catch (err: any) {
      showToast(err.message || 'Failed to disconnect.');
    } finally {
      setUnlinking(null);
    }
  };

  if (loading) return <div style={{ color: TEXT_MUTED }}>Loading...</div>;
  if (!state) return null;

  const canUnlink = (provider: string) => {
    const otherLinked = state.linked.filter(p => p !== provider);
    return otherLinked.length > 0 || state.has_password;
  };

  return (
    <div style={{ marginTop: SPACE.lg }}>
      <h3 style={{ ...TYPO.h3, color: TEXT_PRIMARY, marginBottom: SPACE.md }}>Linked Accounts</h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: SPACE.sm }}>
        {Object.entries(PROVIDER_INFO).map(([provider, info]) => {
          const isLinked = state.linked.includes(provider);
          return (
            <div key={provider} style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '12px 16px', background: CARD_BG, border: `1px solid ${BORDER}`,
              borderRadius: RADIUS.md,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span className="material-symbols-outlined" style={{ fontSize: 24, color: TEXT_PRIMARY }}>
                  {info.icon}
                </span>
                <div>
                  <div style={{ fontWeight: 600, color: TEXT_PRIMARY }}>{info.label}</div>
                  <div style={{ fontSize: 13, color: isLinked ? SUCCESS : TEXT_MUTED }}>
                    {isLinked ? 'Connected' : 'Not connected'}
                  </div>
                </div>
              </div>
              {isLinked ? (
                <button
                  onClick={() => handleUnlink(provider)}
                  disabled={!canUnlink(provider) || unlinking === provider}
                  title={!canUnlink(provider) ? 'Set a password before disconnecting your only login method' : `Disconnect ${info.label}`}
                  style={{
                    background: 'none', border: `1px solid ${!canUnlink(provider) ? BORDER : '#ff4444'}`,
                    borderRadius: RADIUS.sm, padding: '4px 12px',
                    cursor: !canUnlink(provider) ? 'not-allowed' : 'pointer',
                    color: !canUnlink(provider) ? TEXT_MUTED : ERROR_TEXT,
                    fontSize: 13, opacity: !canUnlink(provider) ? 0.5 : 1,
                  }}
                >
                  {unlinking === provider ? '...' : 'Disconnect'}
                </button>
              ) : (
                <a
                  href={getOAuthLinkUrl(provider)}
                  style={{
                    background: 'none', border: `1px solid ${INPUT_BORDER}`,
                    borderRadius: RADIUS.sm, padding: '4px 12px', cursor: 'pointer',
                    color: TEXT_PRIMARY, fontSize: 13, textDecoration: 'none',
                  }}
                >
                  Connect
                </a>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/LinkedAccounts.tsx
git commit -m "feat: add LinkedAccounts component for managing OAuth connections"
```

---

### Task 5.4: Create Settings page

**Files:**
- Create: `frontend/src/pages/SettingsPage.tsx`

- [ ] **Step 1: Create the page**

```tsx
import LinkedAccounts from '../components/LinkedAccounts';
import { TEXT_PRIMARY, TYPO, SPACE } from '../theme';
import { useMediaQuery } from '../hooks/useMediaQuery';

export default function SettingsPage() {
  const { isMobile } = useMediaQuery();
  return (
    <div style={{ maxWidth: 600, margin: isMobile ? '20px auto' : '40px auto', padding: isMobile ? 14 : 24 }}>
      <h1 style={{ ...TYPO.h1, color: TEXT_PRIMARY, marginBottom: SPACE.lg }}>Account Settings</h1>
      <LinkedAccounts />
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/SettingsPage.tsx
git commit -m "feat: add Settings page for account management"
```

---

### Task 5.5: Wire Settings page into routes and add navigation link

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Layout.tsx`

- [ ] **Step 1: Add Settings route to App.tsx**

Add import:
```tsx
import SettingsPage from './pages/SettingsPage';
```

Add route:
```tsx
            <Route path="/settings" element={<SettingsPage />} />
```

- [ ] **Step 2: Add Settings link to Layout.tsx user section**

In the Layout user section (where the logout button is), add a settings link before the logout button:

```tsx
              <Link
                to="/settings"
                title="Account Settings"
                style={{
                  background: 'none', border: 'none', color: TEXT_MUTED, cursor: 'pointer',
                  padding: 4, display: 'flex', alignItems: 'center', textDecoration: 'none',
                }}
              >
                <span className="material-symbols-outlined" style={{ fontSize: 18 }}>settings</span>
              </Link>
```

- [ ] **Step 3: Verify TypeScript**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/Layout.tsx
git commit -m "feat: add Settings route and navigation link to sidebar"
```

---

## Chunk 6: Final Verification

### Task 6.1: Run all tests and verify

- [ ] **Step 1: Run backend tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All tests pass.

- [ ] **Step 2: Run frontend TypeScript check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No TypeScript errors.

- [ ] **Step 3: Manual smoke test**

Start both servers and verify:
1. Navigate to `/auth` — social login buttons render below the email/password form
2. Navigate to `/auth/callback?token=fake` — redirects to `/` with token set
3. Navigate to `/auth/callback?error=invalid_state` — redirects to `/auth` with error message
4. Sign in with demo account, navigate to `/settings` — Linked Accounts section renders with all four providers

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: final verification and polish for OAuth integration"
```
