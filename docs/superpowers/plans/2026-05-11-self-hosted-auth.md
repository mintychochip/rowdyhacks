# Self-Hosted Auth System Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Clerk with a fully self-contained auth system supporting local password auth, OAuth2 (GitHub/Google), invite-only hackathon registration, and first-run bootstrap via env vars.

**Architecture:** Built-in JWT auth with bcrypt password hashing, pluggable OAuth2 providers in DB, refresh tokens with DB revocation, and Fernet-encrypted OAuth secrets. All Clerk dependencies removed.

**Tech Stack:** FastAPI, SQLAlchemy, bcrypt, python-jose, cryptography (Fernet), httpx.

---

## File Structure

| File | Responsibility |
|---|---|
| `backend/app/models.py` | Add `email_verified`, `password_reset_token_hash`, `password_reset_expires` to `User`; augment `OAuthAccount`; add `OAuthProvider`, `RefreshToken`, `HackathonInvite`; add `registration_mode` to `Hackathon` |
| `backend/alembic/versions/...` | Migration for all schema changes |
| `backend/app/auth.py` | Core auth: JWT create/verify, refresh token create/verify, password hashing, Fernet encryption, OAuth state management |
| `backend/app/routes/auth.py` | Auth endpoints: register, login, refresh, logout, forgot-password, reset-password, me, OAuth login/callback, list providers |
| `backend/app/routes/admin_oauth.py` | Admin OAuth provider CRUD endpoints |
| `backend/app/routes/invites.py` | Invite code generation, listing, revocation endpoints |
| `backend/app/config.py` | Add `admin_email`, `admin_password` settings; remove Clerk settings |
| `backend/app/main.py` | Remove Clerk imports; add `admin_email`/`admin_password` bootstrap on startup; wire new routers |
| `backend/app/email_service.py` | Add password reset email template |
| `frontend/src/services/api.ts` | Replace Clerk token getter with in-memory JWT + refresh-on-401 logic |
| `frontend/src/hooks/useAuth.ts` | New custom auth hook: login, logout, register, user, refresh |
| `frontend/src/pages/AuthPage.tsx` | Replace Clerk SignIn with custom LoginForm + RegisterForm |
| `frontend/src/components/LoginForm.tsx` | Email/password form + OAuth buttons |
| `frontend/src/components/RegisterForm.tsx` | Email/password/name form |
| `frontend/src/components/ForgotPasswordForm.tsx` | Email input for reset request |
| `frontend/src/components/ResetPasswordForm.tsx` | Token + new password form |
| `frontend/src/components/OAuthAdminPanel.tsx` | Provider management table + add form |
| `frontend/src/components/InviteCodeManager.tsx` | Generate/list/revoke invites |
| `frontend/src/pages/HackathonSettings.tsx` | Add `registration_mode` toggle + invite manager |
| `backend/tests/test_auth.py` | Unit tests for JWT, bcrypt, refresh tokens, Fernet |
| `backend/tests/test_auth_routes.py` | Integration tests for register/login/logout/refresh/OAuth |
| `backend/tests/test_invites.py` | Integration tests for invite codes |

---

## Chunk 1: Database Migrations and Models

### Task 1: Add User fields and new models

**Files:**
- Modify: `backend/app/models.py:158-203` (User, OAuthAccount)
- Create: Migration file via `alembic revision`
- Test: `backend/tests/test_models.py` (verify schema loads)

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_models.py
def test_user_has_email_verified():
    from app.models import User
    u = User(email="test@example.com", name="Test", password_hash="hash")
    assert u.email_verified is False

def test_refresh_token_model():
    from app.models import RefreshToken
    rt = RefreshToken(user_id="uuid", token_hash="sha256hash", expires_at=datetime.now(UTC))
    assert rt.revoked_at is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_models.py::test_user_has_email_verified -v`
Expected: FAIL with "AttributeError: 'User' object has no attribute 'email_verified'"

- [ ] **Step 3: Modify models.py**

Add to `User` model after `password_hash`:
```python
email_verified = Column(Boolean, default=False)
password_reset_token_hash = Column(String(255), nullable=True)
password_reset_expires = Column(DateTime(timezone=True), nullable=True)
```

Add to `OAuthAccount` model after `provider_email`:
```python
access_token_encrypted = Column(Text, nullable=True)
refresh_token_encrypted = Column(Text, nullable=True)
expires_at = Column(DateTime(timezone=True), nullable=True)
```

Add new models at end of models.py:
```python
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    user = relationship("User", back_populates="refresh_tokens")


class OAuthProvider(Base):
    __tablename__ = "oauth_providers"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    client_id = Column(String(255), nullable=False)
    client_secret_encrypted = Column(Text, nullable=False)
    authorize_url = Column(Text, nullable=False)
    token_url = Column(Text, nullable=False)
    userinfo_url = Column(Text, nullable=False)
    scope = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class HackathonInvite(Base):
    __tablename__ = "hackathon_invites"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(32), unique=True, nullable=False)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.participant)
    uses_remaining = Column(Integer, nullable=False, default=1)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(String(64), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
```

Add to `User` model relationships:
```python
refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
```

Add to `Hackathon` model:
```python
registration_mode = Column(String(20), default="open", nullable=False)
```

- [ ] **Step 4: Generate Alembic migration**

Run: `cd backend && alembic revision --autogenerate -m "add self-hosted auth tables"`
Then verify the generated migration file covers all new tables and columns.

- [ ] **Step 5: Run tests**

Run: `pytest backend/tests/test_models.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/models.py backend/alembic/versions/...
git commit -m "feat(auth): add self-hosted auth models and migrations"
```

---

## Chunk 2: Backend Auth Core

### Task 2: Rewrite backend/app/auth.py

**Files:**
- Rewrite: `backend/app/auth.py`
- Test: `backend/tests/test_auth.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_auth.py
import pytest
from datetime import UTC, datetime, timedelta

from app.auth import hash_password, verify_password, create_access_token, verify_access_token


def test_hash_and_verify_password():
    hashed = hash_password("MyPassword123")
    assert verify_password("MyPassword123", hashed)
    assert not verify_password("WrongPassword", hashed)


def test_create_and_verify_access_token():
    token = create_access_token({"sub": "user-123", "email": "test@example.com", "role": "participant"})
    payload = verify_access_token(token)
    assert payload["sub"] == "user-123"
    assert payload["email"] == "test@example.com"


def test_verify_expired_token():
    token = create_access_token({"sub": "user-123"}, expires_delta=timedelta(seconds=-1))
    with pytest.raises(ValueError, match="expired"):
        verify_access_token(token)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_auth.py -v`
Expected: FAIL with import errors (functions don't exist yet)

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/auth.py
"""Auth utilities for self-hosted hackathon platform.
Handles JWT tokens, password hashing, refresh tokens, OAuth state, and Fernet encryption.
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import RefreshToken, User

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


# --- Fernet key derivation ---

def _get_fernet() -> Fernet:
    """Derive a Fernet key from HACKVERIFY_SECRET_KEY via HKDF-SHA256."""
    import base64
    import hashlib
    key = hashlib.sha256(settings.secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_secret(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    return _get_fernet().decrypt(ciphertext.encode()).decode()


# --- Password hashing ---

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


# --- JWT tokens ---

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.now(UTC)})
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def verify_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError as e:
        raise ValueError(f"Invalid or expired token: {e}") from e


# --- Refresh tokens ---

def create_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def store_refresh_token(db: AsyncSession, user_id: str, token: str, expires_days: int = REFRESH_TOKEN_EXPIRE_DAYS) -> RefreshToken:
    rt = RefreshToken(
        user_id=user_id,
        token_hash=hash_refresh_token(token),
        expires_at=datetime.now(UTC) + timedelta(days=expires_days),
    )
    db.add(rt)
    await db.commit()
    await db.refresh(rt)
    return rt


async def verify_refresh_token(db: AsyncSession, token: str) -> RefreshToken | None:
    token_hash = hash_refresh_token(token)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(UTC),
        )
    )
    return result.scalar_one_or_none()


async def revoke_refresh_token(db: AsyncSession, token: str) -> None:
    token_hash = hash_refresh_token(token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    rt = result.scalar_one_or_none()
    if rt:
        rt.revoked_at = datetime.now(UTC)
        await db.commit()


# --- Current user dependencies ---

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = verify_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("No user ID in token")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_current_user_ws(token: str | None) -> dict | None:
    """Validate JWT token for WebSocket connections."""
    if not token:
        return None
    try:
        payload = verify_access_token(token)
        return {
            "id": payload.get("sub"),
            "role": payload.get("role"),
            "email": payload.get("email"),
        }
    except ValueError:
        return None


# --- Role requirements ---

def require_organizer(user: User = Depends(get_current_user)) -> User:
    if user.role.value != "organizer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organizer access required")
    return user


def require_participant(user: User = Depends(get_current_user)) -> User:
    if user.role.value not in ("participant", "organizer", "judge"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Participant access required")
    return user


def require_judge(user: User = Depends(get_current_user)) -> User:
    if user.role.value not in ("judge", "organizer"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Judge access required")
    return user


# --- Password reset ---

def generate_reset_token() -> str:
    return secrets.token_urlsafe(32)


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# --- OAuth state ---

def generate_oauth_state() -> str:
    return secrets.token_urlsafe(32)


# --- Validation ---

def validate_password(password: str) -> bool:
    """Password must be at least 8 chars with uppercase, lowercase, and digit."""
    if len(password) < 8:
        return False
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    return has_upper and has_lower and has_digit
```

- [ ] **Step 4: Run tests**

Run: `pytest backend/tests/test_auth.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/auth.py backend/tests/test_auth.py
git commit -m "feat(auth): implement local JWT, bcrypt, refresh tokens, Fernet encryption"
```

---

## Chunk 3: Backend Auth Routes

### Task 3: Rewrite backend/app/routes/auth.py

**Files:**
- Rewrite: `backend/app/routes/auth.py`
- Modify: `backend/app/main.py` (ensure router is wired)
- Test: `backend/tests/test_auth_routes.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_auth_routes.py
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_register_new_user():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        res = await ac.post("/api/auth/register", json={
            "email": "newuser@example.com",
            "password": "Password123",
            "name": "New User",
        })
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "newuser@example.com"
    assert data["role"] == "participant"


@pytest.mark.asyncio
async def test_register_blocked_until_organizer_exists():
    # This test assumes DB is empty at start — will need conftest setup
    async with AsyncClient(app=app, base_url="http://test") as ac:
        res = await ac.post("/api/auth/register", json={
            "email": "first@example.com",
            "password": "Password123",
            "name": "First",
        })
    assert res.status_code == 403
    assert "organizer" in res.json()["detail"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_auth_routes.py -v`
Expected: FAIL (endpoint doesn't exist or returns Clerk-based response)

- [ ] **Step 3: Write the auth routes**

```python
# backend/app/routes/auth.py
import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    create_access_token,
    create_refresh_token,
    generate_reset_token,
    get_current_user,
    hash_password,
    hash_reset_token,
    require_organizer,
    store_refresh_token,
    validate_password,
    verify_access_token,
    verify_password,
    verify_refresh_token,
    revoke_refresh_token,
)
from app.config import settings
from app.database import get_db
from app.email_service import send_email
from app.models import OAuthAccount, OAuthProvider, User, UserRole
from app.schemas import UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger(__name__)


def _set_refresh_cookie(response: Response, token: str) -> None:
    max_age = 7 * 24 * 60 * 60  # 7 days
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=False,  # Set to True in production
        samesite="strict",
        max_age=max_age,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key="refresh_token")


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
async def register(
    email: str,
    password: str,
    name: str,
    db: AsyncSession = Depends(get_db),
):
    # Block registration until an organizer exists
    organizer_result = await db.execute(select(User).where(User.role == UserRole.organizer).limit(1))
    if not organizer_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform setup required. The first account must be created by the server administrator.",
        )

    # Validate password
    if not validate_password(password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters with uppercase, lowercase, and a number.",
        )

    # Check duplicate email
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=email,
        name=name,
        password_hash=hash_password(password),
        role=UserRole.participant,
        email_verified=True,  # MVP: skip email verification
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role.value,
        created_at=user.created_at,
    )


@router.post("/login")
async def login(
    response: Response,
    email: str,
    password: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not user.password_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    access_token = create_access_token({
        "sub": user.id,
        "email": user.email,
        "role": user.role.value,
    })
    refresh_token = create_refresh_token()
    await store_refresh_token(db, user.id, refresh_token)
    _set_refresh_cookie(response, refresh_token)

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/refresh")
async def refresh(
    response: Response,
    refresh_token: str = Cookie(None),
    db: AsyncSession = Depends(get_db),
):
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")

    rt = await verify_refresh_token(db, refresh_token)
    if not rt:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    result = await db.execute(select(User).where(User.id == rt.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    access_token = create_access_token({
        "sub": user.id,
        "email": user.email,
        "role": user.role.value,
    })

    # Rotate refresh token
    new_refresh_token = create_refresh_token()
    await revoke_refresh_token(db, refresh_token)
    await store_refresh_token(db, user.id, new_refresh_token)
    _set_refresh_cookie(response, new_refresh_token)

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(
    response: Response,
    refresh_token: str = Cookie(None),
    db: AsyncSession = Depends(get_db),
):
    if refresh_token:
        await revoke_refresh_token(db, refresh_token)
    _clear_refresh_cookie(response)
    return {"message": "Logged out successfully"}


@router.post("/forgot-password")
async def forgot_password(email: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        # Return success even if email not found (prevents enumeration)
        return {"message": "If an account exists, a reset email has been sent."}

    token = generate_reset_token()
    user.password_reset_token_hash = hash_reset_token(token)
    user.password_reset_expires = datetime.now(UTC) + timedelta(hours=1)
    await db.commit()

    reset_url = f"{settings.frontend_url}/reset-password?token={token}"
    body = f"Click this link to reset your password: {reset_url}\nThis link expires in 1 hour."
    await send_email(email, "Password Reset Request", body)

    return {"message": "If an account exists, a reset email has been sent."}


@router.post("/reset-password")
async def reset_password(token: str, new_password: str, db: AsyncSession = Depends(get_db)):
    if not validate_password(new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters with uppercase, lowercase, and a number.",
        )

    token_hash = hash_reset_token(token)
    result = await db.execute(
        select(User).where(
            User.password_reset_token_hash == token_hash,
            User.password_reset_expires > datetime.now(UTC),
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    user.password_hash = hash_password(new_password)
    user.password_reset_token_hash = None
    user.password_reset_expires = None
    await db.commit()

    return {"message": "Password reset successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role.value,
        created_at=user.created_at,
    )


@router.get("/providers")
async def list_providers(db: AsyncSession = Depends(get_db)):
    """List active OAuth providers for login page buttons."""
    result = await db.execute(select(OAuthProvider).where(OAuthProvider.is_active == True))
    providers = result.scalars().all()
    return [
        {"name": p.name, "display_name": p.display_name}
        for p in providers
    ]
```

- [ ] **Step 4: Wire router in main.py**

In `backend/app/main.py`, ensure:
```python
from app.routes.auth import router as auth_router
# ...
app.include_router(auth_router)
```

- [ ] **Step 5: Run tests**

Run: `pytest backend/tests/test_auth_routes.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/routes/auth.py backend/app/main.py backend/tests/test_auth_routes.py
git commit -m "feat(auth): implement local auth endpoints (register, login, refresh, logout, reset)"
```

---

## Chunk 4: Backend OAuth Routes

### Task 4: Implement OAuth login and admin management

**Files:**
- Create: `backend/app/routes/oauth.py`
- Create: `backend/app/routes/admin_oauth.py`
- Modify: `backend/app/main.py` (wire routers)
- Test: `backend/tests/test_oauth.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_oauth.py
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_list_providers_empty():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        res = await ac.get("/api/auth/providers")
    assert res.status_code == 200
    assert res.json() == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_oauth.py::test_list_providers_empty -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement OAuth routes**

```python
# backend/app/routes/oauth.py
import logging
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    create_access_token,
    create_refresh_token,
    decrypt_secret,
    encrypt_secret,
    generate_oauth_state,
    get_current_user,
    store_refresh_token,
    require_organizer,
)
from app.config import settings
from app.database import get_db
from app.models import OAuthAccount, OAuthProvider, User, UserRole
from app.schemas import UserResponse

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
    result = await db.execute(select(OAuthProvider).where(OAuthProvider.name == provider, OAuthProvider.is_active == True))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="OAuth provider not found or inactive")

    # In production: store state in Redis with 5-min TTL
    # MVP: skip state validation for simplicity (add later)
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
    result = await db.execute(select(OAuthProvider).where(OAuthProvider.name == provider))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Provider not found")

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
    provider_user_id = str(userinfo.get("id") or userinfo.get("sub"))

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
    jwt_token = create_access_token({
        "sub": user.id,
        "email": user.email,
        "role": user.role.value,
    })
    refresh_token = create_refresh_token()
    await store_refresh_token(db, user.id, refresh_token)

    # Redirect to frontend with token
    redirect_url = f"{settings.frontend_url}/auth/callback?token={jwt_token}&refresh={refresh_token}"
    return {"redirect_url": redirect_url, "access_token": jwt_token}
```

```python
# backend/app/routes/admin_oauth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import encrypt_secret, require_organizer
from app.database import get_db
from app.models import OAuthProvider
from app.routes.oauth import OAUTH_PRESETS

router = APIRouter(prefix="/api/admin/oauth", tags=["admin-oauth"])


@router.get("/providers")
async def list_providers(
    db: AsyncSession = Depends(get_db),
    user=Depends(require_organizer),
):
    result = await db.execute(select(OAuthProvider))
    providers = result.scalars().all()
    return [
        {
            "name": p.name,
            "display_name": p.display_name,
            "client_id": p.client_id,
            "client_secret": "***",
            "is_active": p.is_active,
        }
        for p in providers
    ]


@router.post("/providers")
async def add_provider(
    name: str,
    client_id: str,
    client_secret: str,
    preset: str | None = None,
    authorize_url: str | None = None,
    token_url: str | None = None,
    userinfo_url: str | None = None,
    scope: str | None = None,
    display_name: str | None = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_organizer),
):
    # Check for duplicate
    existing = await db.execute(select(OAuthProvider).where(OAuthProvider.name == name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Provider already exists")

    # Apply preset if specified
    if preset and preset in OAUTH_PRESETS:
        preset_data = OAUTH_PRESETS[preset]
        authorize_url = authorize_url or preset_data["authorize_url"]
        token_url = token_url or preset_data["token_url"]
        userinfo_url = userinfo_url or preset_data["userinfo_url"]
        scope = scope or preset_data["scope"]
        display_name = display_name or preset_data["display_name"]

    if not all([authorize_url, token_url, userinfo_url, scope]):
        raise HTTPException(status_code=400, detail="Missing required OAuth endpoint URLs")

    provider = OAuthProvider(
        name=name,
        display_name=display_name or name.capitalize(),
        client_id=client_id,
        client_secret_encrypted=encrypt_secret(client_secret),
        authorize_url=authorize_url,
        token_url=token_url,
        userinfo_url=userinfo_url,
        scope=scope,
    )
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    return {"name": provider.name, "display_name": provider.display_name}


@router.delete("/providers/{name}")
async def remove_provider(
    name: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_organizer),
):
    result = await db.execute(select(OAuthProvider).where(OAuthProvider.name == name))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    provider.is_active = False
    await db.commit()
    return {"message": f"Provider {name} deactivated"}
```

- [ ] **Step 4: Wire routers in main.py**

```python
from app.routes.oauth import router as oauth_router
from app.routes.admin_oauth import router as admin_oauth_router
# ...
app.include_router(oauth_router)
app.include_router(admin_oauth_router)
```

- [ ] **Step 5: Run tests**

Run: `pytest backend/tests/test_oauth.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/routes/oauth.py backend/app/routes/admin_oauth.py backend/app/main.py backend/tests/test_oauth.py
git commit -m "feat(auth): add OAuth2 login flow and admin provider management"
```

---

## Chunk 5: Backend Invite System

### Task 5: Implement hackathon invite codes

**Files:**
- Create: `backend/app/routes/invites.py`
- Modify: `backend/app/main.py` (wire router)
- Modify: `backend/app/routes/registrations.py` (add invite validation)
- Test: `backend/tests/test_invites.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_invites.py
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_generate_invite_codes(admin_user, auth_headers):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        res = await ac.post("/api/hackathons/123/invites", json={"count": 5, "role": "participant"}, headers=auth_headers)
    assert res.status_code == 201
    data = res.json()
    assert len(data["codes"]) == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_invites.py -v`
Expected: FAIL (endpoint not found)

- [ ] **Step 3: Implement invite routes**

```python
# backend/app/routes/invites.py
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_organizer
from app.database import get_db
from app.models import Hackathon, HackathonInvite, UserRole

router = APIRouter(prefix="/api/hackathons", tags=["invites"])


def _generate_invite_code(hackathon_slug: str) -> str:
    suffix = secrets.token_urlsafe(12).replace("-", "").replace("_", "")[:16].upper()
    return f"{hackathon_slug.upper()}-{suffix}"


@router.post("/{hackathon_id}/invites")
async def generate_invites(
    hackathon_id: str,
    count: int = 10,
    role: UserRole = UserRole.participant,
    expires_days: int | None = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_organizer),
):
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    expires_at = None
    if expires_days:
        expires_at = datetime.now(UTC) + timedelta(days=expires_days)

    codes = []
    slug = hackathon.name.replace(" ", "-").lower()[:10]
    for _ in range(count):
        code = _generate_invite_code(slug)
        # Ensure uniqueness (retry if collision)
        while True:
            existing = await db.execute(select(HackathonInvite).where(HackathonInvite.code == code))
            if not existing.scalar_one_or_none():
                break
            code = _generate_invite_code(slug)

        invite = HackathonInvite(
            hackathon_id=hackathon_id,
            code=code,
            role=role,
            expires_at=expires_at,
            created_by=user.id,
        )
        db.add(invite)
        codes.append(code)

    await db.commit()
    return {"codes": codes, "count": len(codes)}


@router.get("/{hackathon_id}/invites")
async def list_invites(
    hackathon_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_organizer),
):
    result = await db.execute(
        select(HackathonInvite).where(HackathonInvite.hackathon_id == hackathon_id)
    )
    invites = result.scalars().all()
    return [
        {
            "code": i.code,
            "role": i.role.value,
            "uses_remaining": i.uses_remaining,
            "expires_at": i.expires_at.isoformat() if i.expires_at else None,
            "created_at": i.created_at.isoformat(),
        }
        for i in invites
    ]


@router.delete("/invites/{code}")
async def revoke_invite(
    code: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_organizer),
):
    result = await db.execute(select(HackathonInvite).where(HackathonInvite.code == code))
    invite = result.scalar_one_or_none()
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    invite.uses_remaining = 0
    await db.commit()
    return {"message": f"Invite {code} revoked"}
```

- [ ] **Step 4: Modify registration endpoint for invite validation**

In the existing registration endpoint (`backend/app/routes/registrations.py` or similar), when a hackathon has `registration_mode == "invite_only"`, require `invite_code` in the request body and validate it:

```python
# Pseudocode — adapt to existing registration endpoint structure:
if hackathon.registration_mode == "invite_only":
    if not invite_code:
        raise HTTPException(400, "Invite code required")
    invite_result = await db.execute(
        select(HackathonInvite).where(
            HackathonInvite.code == invite_code,
            HackathonInvite.hackathon_id == hackathon_id,
            HackathonInvite.uses_remaining > 0,
            (HackathonInvite.expires_at.is_(None)) | (HackathonInvite.expires_at > datetime.now(UTC)),
        )
    )
    invite = invite_result.scalar_one_or_none()
    if not invite:
        raise HTTPException(400, "Invalid or expired invite code")
    invite.uses_remaining -= 1
```

- [ ] **Step 5: Run tests**

Run: `pytest backend/tests/test_invites.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/routes/invites.py backend/app/routes/registrations.py backend/tests/test_invites.py
git commit -m "feat(auth): add hackathon invite code system"
```

---

## Chunk 6: Frontend Auth State and API

### Task 6: Replace Clerk with custom auth hook and API wrapper

**Files:**
- Create: `frontend/src/hooks/useAuth.ts`
- Modify: `frontend/src/services/api.ts`
- Delete: Clerk references in frontend
- Test: Manual verification (no new test file needed — existing E2E covers)

- [ ] **Step 1: Write the auth hook**

```typescript
// frontend/src/hooks/useAuth.ts
import { useState, useEffect, useCallback } from "react";

interface User {
  id: string;
  email: string;
  name: string;
  role: string;
}

let accessToken: string | null = null;

function setAccessToken(token: string | null) {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async (): Promise<boolean> => {
    try {
      const res = await fetch("/api/auth/refresh", {
        method: "POST",
        credentials: "include",
      });
      if (!res.ok) return false;
      const data = await res.json();
      setAccessToken(data.access_token);
      return true;
    } catch {
      return false;
    }
  }, []);

  const fetchMe = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }
    try {
      const res = await fetch("/api/auth/me", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setUser(data);
      } else if (res.status === 401) {
        // Try refresh once
        const refreshed = await refresh();
        if (refreshed) {
          const retryRes = await fetch("/api/auth/me", {
            headers: { Authorization: `Bearer ${getAccessToken()}` },
          });
          if (retryRes.ok) {
            const data = await retryRes.json();
            setUser(data);
          } else {
            setUser(null);
          }
        } else {
          setUser(null);
        }
      }
    } catch {
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, [refresh]);

  useEffect(() => {
    // On mount: try refresh, then fetch me
    const init = async () => {
      const refreshed = await refresh();
      if (refreshed) {
        await fetchMe();
      } else {
        setIsLoading(false);
        setUser(null);
      }
    };
    init();
  }, [refresh, fetchMe]);

  const login = useCallback(async (email: string, password: string): Promise<boolean> => {
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) return false;
      const data = await res.json();
      setAccessToken(data.access_token);
      await fetchMe();
      return true;
    } catch {
      return false;
    }
  }, [fetchMe]);

  const register = useCallback(async (email: string, password: string, name: string): Promise<boolean> => {
    try {
      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, name }),
      });
      return res.ok;
    } catch {
      return false;
    }
  }, []);

  const logout = useCallback(async () => {
    await fetch("/api/auth/logout", {
      method: "POST",
      credentials: "include",
    });
    setAccessToken(null);
    setUser(null);
  }, []);

  return {
    user,
    isLoading,
    isAuthenticated: !!user,
    login,
    register,
    logout,
  };
}
```

- [ ] **Step 2: Modify api.ts**

Replace the Clerk token getter with the in-memory access token:

```typescript
// frontend/src/services/api.ts
import { getAccessToken } from "../hooks/useAuth";

// Remove the old setTokenGetter / getTokenFunc code entirely

async function getAuthToken(): Promise<string | null> {
  return getAccessToken();
}

// The rest of api.ts stays the same — request(), getMe(), etc.
// But add refresh-on-401 logic to request():

export async function request(path: string, options: RequestInit = {}) {
  const token = await getAuthToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10000);

  try {
    const res = await fetch(`${BASE}${path}`, {
      ...options,
      headers,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (res.status === 401 && token) {
      // Try refresh once
      const refreshRes = await fetch("/api/auth/refresh", {
        method: "POST",
        credentials: "include",
      });
      if (refreshRes.ok) {
        const data = await refreshRes.json();
        // Update token globally
        const newToken = data.access_token;
        // Retry original request
        const retryHeaders = { ...headers, Authorization: `Bearer ${newToken}` };
        const retryRes = await fetch(`${BASE}${path}`, {
          ...options,
          headers: retryHeaders,
        });
        if (!retryRes.ok) {
          const err = await retryRes.json().catch(() => ({ detail: retryRes.statusText }));
          throw new Error(err.detail || "Request failed");
        }
        return retryRes.json();
      }
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      if (Array.isArray(err)) {
        const messages = err.map((e: any) => e.msg || String(e)).join(", ");
        throw new Error(messages || "Validation failed");
      }
      throw new Error(err.detail || err.message || JSON.stringify(err) || "Request failed");
    }
    return res.json();
  } catch (e) {
    clearTimeout(timeoutId);
    throw e;
  }
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/useAuth.ts frontend/src/services/api.ts
git commit -m "feat(auth): replace Clerk with custom auth hook and in-memory JWT"
```

---

## Chunk 7: Frontend Auth Pages

### Task 7: Replace AuthPage with custom login/register forms

**Files:**
- Modify: `frontend/src/pages/AuthPage.tsx`
- Create: `frontend/src/components/LoginForm.tsx`
- Create: `frontend/src/components/RegisterForm.tsx`
- Create: `frontend/src/components/ForgotPasswordForm.tsx`
- Create: `frontend/src/components/ResetPasswordForm.tsx`

- [ ] **Step 1: Create LoginForm component**

```tsx
// frontend/src/components/LoginForm.tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

interface LoginFormProps {
  onToggle: () => void;
}

export default function LoginForm({ onToggle }: LoginFormProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    const ok = await login(email, password);
    setLoading(false);
    if (ok) {
      navigate("/");
    } else {
      setError("Invalid email or password");
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <h2>Sign In</h2>
      {error && <div style={{ color: "red" }}>{error}</div>}
      <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
      <input type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required />
      <button type="submit" disabled={loading}>{loading ? "Signing in..." : "Sign In"}</button>
      <p>
        <a href="/forgot-password">Forgot password?</a>
        <button type="button" onClick={onToggle}>Create account</button>
      </p>
    </form>
  );
}
```

- [ ] **Step 2: Create RegisterForm component**

```tsx
// frontend/src/components/RegisterForm.tsx
import { useState } from "react";
import { useAuth } from "../hooks/useAuth";

interface RegisterFormProps {
  onToggle: () => void;
}

export default function RegisterForm({ onToggle }: RegisterFormProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    setLoading(true);
    const ok = await register(email, password, name);
    setLoading(false);
    if (ok) {
      onToggle(); // Switch to login
    } else {
      setError("Registration failed. Email may already be in use.");
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <h2>Create Account</h2>
      {error && <div style={{ color: "red" }}>{error}</div>}
      <input type="text" placeholder="Full Name" value={name} onChange={(e) => setName(e.target.value)} required />
      <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
      <input type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required />
      <button type="submit" disabled={loading}>{loading ? "Creating..." : "Create Account"}</button>
      <p>Already have an account? <button type="button" onClick={onToggle}>Sign in</button></p>
    </form>
  );
}
```

- [ ] **Step 3: Rewrite AuthPage**

```tsx
// frontend/src/pages/AuthPage.tsx
import { useState } from "react";
import LoginForm from "../components/LoginForm";
import RegisterForm from "../components/RegisterForm";

export default function AuthPage() {
  const [showRegister, setShowRegister] = useState(false);

  return (
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "80vh" }}>
      {showRegister ? (
        <RegisterForm onToggle={() => setShowRegister(false)} />
      ) : (
        <LoginForm onToggle={() => setShowRegister(true)} />
      )}
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/AuthPage.tsx frontend/src/components/LoginForm.tsx frontend/src/components/RegisterForm.tsx frontend/src/components/ForgotPasswordForm.tsx frontend/src/components/ResetPasswordForm.tsx
git commit -m "feat(auth): replace Clerk SignIn with custom login/register forms"
```

---

## Chunk 8: Frontend Admin and Invite Components

### Task 8: Add OAuth admin panel and invite manager

**Files:**
- Create: `frontend/src/components/OAuthAdminPanel.tsx`
- Create: `frontend/src/components/InviteCodeManager.tsx`
- Modify: `frontend/src/pages/HackathonSettings.tsx`

- [ ] **Step 1: Create OAuthAdminPanel**

```tsx
// frontend/src/components/OAuthAdminPanel.tsx
import { useState, useEffect } from "react";
import * as api from "../services/api";

export default function OAuthAdminPanel() {
  const [providers, setProviders] = useState<any[]>([]);
  const [name, setName] = useState("");
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [preset, setPreset] = useState("github");

  useEffect(() => {
    api.request("/admin/oauth/providers").then(setProviders);
  }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    await api.request("/admin/oauth/providers", {
      method: "POST",
      body: JSON.stringify({ name, client_id: clientId, client_secret: clientSecret, preset }),
    });
    setName("");
    setClientId("");
    setClientSecret("");
    api.request("/admin/oauth/providers").then(setProviders);
  };

  return (
    <div>
      <h2>OAuth Providers</h2>
      <ul>
        {providers.map((p) => (
          <li key={p.name}>{p.display_name} ({p.is_active ? "Active" : "Inactive"})</li>
        ))}
      </ul>
      <form onSubmit={handleAdd}>
        <h3>Add Provider</h3>
        <select value={preset} onChange={(e) => setPreset(e.target.value)}>
          <option value="github">GitHub</option>
          <option value="google">Google</option>
          <option value="custom">Custom</option>
        </select>
        <input placeholder="Name (e.g. github)" value={name} onChange={(e) => setName(e.target.value)} required />
        <input placeholder="Client ID" value={clientId} onChange={(e) => setClientId(e.target.value)} required />
        <input type="password" placeholder="Client Secret" value={clientSecret} onChange={(e) => setClientSecret(e.target.value)} required />
        <button type="submit">Add Provider</button>
      </form>
    </div>
  );
}
```

- [ ] **Step 2: Create InviteCodeManager**

```tsx
// frontend/src/components/InviteCodeManager.tsx
import { useState, useEffect } from "react";
import * as api from "../services/api";

interface Props {
  hackathonId: string;
}

export default function InviteCodeManager({ hackathonId }: Props) {
  const [invites, setInvites] = useState<any[]>([]);
  const [count, setCount] = useState(10);
  const [role, setRole] = useState("participant");

  const load = () => {
    api.request(`/hackathons/${hackathonId}/invites`).then(setInvites);
  };

  useEffect(() => { load(); }, [hackathonId]);

  const generate = async () => {
    await api.request(`/hackathons/${hackathonId}/invites`, {
      method: "POST",
      body: JSON.stringify({ count, role }),
    });
    load();
  };

  return (
    <div>
      <h3>Invite Codes</h3>
      <div>
        <input type="number" value={count} onChange={(e) => setCount(Number(e.target.value))} min={1} max={100} />
        <select value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="participant">Participant</option>
          <option value="judge">Judge</option>
        </select>
        <button onClick={generate}>Generate</button>
      </div>
      <table>
        <thead><tr><th>Code</th><th>Role</th><th>Uses Left</th><th>Expires</th></tr></thead>
        <tbody>
          {invites.map((i) => (
            <tr key={i.code}>
              <td>{i.code}</td>
              <td>{i.role}</td>
              <td>{i.uses_remaining}</td>
              <td>{i.expires_at || "Never"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 3: Modify HackathonSettings**

Add `registration_mode` toggle and `InviteCodeManager` to the existing HackathonSettings page. The exact insertion point depends on the current page structure — add after the general settings section.

```tsx
// In HackathonSettings.tsx, add:
import InviteCodeManager from "../components/InviteCodeManager";

// In the settings form, add:
<div>
  <label>Registration Mode</label>
  <select
    value={hackathon.registration_mode || "open"}
    onChange={(e) => updateHackathon({ ...hackathon, registration_mode: e.target.value })}
  >
    <option value="open">Open (anyone can register)</option>
    <option value="invite_only">Invite Only (requires code)</option>
  </select>
</div>

// Add at bottom:
<InviteCodeManager hackathonId={hackathon.id} />
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/OAuthAdminPanel.tsx frontend/src/components/InviteCodeManager.tsx frontend/src/pages/HackathonSettings.tsx
git commit -m "feat(auth): add OAuth admin panel and invite code manager"
```

---

## Chunk 9: Cleanup and First-Run Bootstrap

### Task 9: Remove Clerk and add first-run bootstrap

**Files:**
- Delete: `backend/app/clerk_auth.py`
- Modify: `backend/app/config.py` (remove Clerk settings, add admin settings)
- Modify: `backend/app/main.py` (add bootstrap, remove Clerk)
- Modify: `frontend/package.json` (remove `@clerk/clerk-react`)
- Modify: `docker-compose.dev.yml` (remove `VITE_CLERK_PUBLISHABLE_KEY`)
- Modify: `docker-compose.yml` (same)

- [ ] **Step 1: Remove Clerk from backend**

Delete `backend/app/clerk_auth.py`.

Remove from `backend/app/config.py`:
```python
clerk_secret_key: str = Field(default="", description="Clerk secret key for JWT verification")
clerk_webhook_secret: str = Field(default="", description="Clerk webhook signing secret (Svix)")
```

Add to `backend/app/config.py`:
```python
admin_email: str = Field(default="", description="First organizer email (bootstrap)")
admin_password: str = Field(default="", description="First organizer password (bootstrap)")
```

- [ ] **Step 2: Add first-run bootstrap in main.py**

In the `lifespan` context manager in `main.py`, after DB initialization:

```python
from app.models import User, UserRole
from app.auth import hash_password

async def _bootstrap_admin(db):
    result = await db.execute(select(User).limit(1))
    if result.scalar_one_or_none():
        return  # Users exist, no bootstrap needed
    if not settings.admin_email or not settings.admin_password:
        logger.warning("No users found and HACKVERIFY_ADMIN_EMAIL not set. Set HACKVERIFY_ADMIN_EMAIL and HACKVERIFY_ADMIN_PASSWORD to create the first organizer.")
        return
    admin = User(
        email=settings.admin_email,
        name="Admin",
        password_hash=hash_password(settings.admin_password),
        role=UserRole.organizer,
        email_verified=True,
    )
    db.add(admin)
    await db.commit()
    logger.info(f"Bootstrap: Created organizer account for {settings.admin_email}")
```

- [ ] **Step 3: Remove Clerk from frontend**

```bash
cd frontend
npm uninstall @clerk/clerk-react
```

Remove from `frontend/package.json` if npm doesn't clean it up automatically.

Remove `VITE_CLERK_PUBLISHABLE_KEY` from all docker-compose files and `.env.example`.

- [ ] **Step 4: Update any remaining Clerk imports**

Search for remaining Clerk imports across the frontend:
```bash
grep -r "clerk" frontend/src/ --include="*.tsx" --include="*.ts"
```
Replace any remaining `useAuth` from Clerk with the custom hook, `useUser` with `useAuth().user`, etc.

- [ ] **Step 5: Run full test suite**

Run: `pytest backend/tests/ -v --ignore=backend/tests/crawler`
Expected: All auth-related tests PASS. Some tests may need updates if they relied on Clerk auth patterns.

- [ ] **Step 6: Commit**

```bash
git add backend/app/config.py backend/app/main.py backend/app/clerk_auth.py docker-compose.dev.yml docker-compose.yml frontend/package.json
git commit -m "feat(auth): remove Clerk, add first-run admin bootstrap"
```

---

## Summary

| Chunk | Tasks | Files Touched |
|---|---|---|
| 1 | DB migrations, models | `models.py`, Alembic migration |
| 2 | Auth core (JWT, bcrypt, Fernet) | `auth.py`, `test_auth.py` |
| 3 | Auth routes (register/login/refresh/logout) | `routes/auth.py`, `main.py`, `test_auth_routes.py` |
| 4 | OAuth routes and admin | `routes/oauth.py`, `routes/admin_oauth.py`, `test_oauth.py` |
| 5 | Invite system | `routes/invites.py`, `routes/registrations.py`, `test_invites.py` |
| 6 | Frontend auth state | `hooks/useAuth.ts`, `services/api.ts` |
| 7 | Frontend auth pages | `pages/AuthPage.tsx`, `components/LoginForm.tsx`, `RegisterForm.tsx`, `ForgotPasswordForm.tsx`, `ResetPasswordForm.tsx` |
| 8 | Frontend admin/invite | `components/OAuthAdminPanel.tsx`, `InviteCodeManager.tsx`, `pages/HackathonSettings.tsx` |
| 9 | Cleanup Clerk, bootstrap | `clerk_auth.py`, `config.py`, `main.py`, `package.json`, docker-compose files |
