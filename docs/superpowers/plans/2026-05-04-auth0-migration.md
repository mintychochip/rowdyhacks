# Auth0 Migration Implementation Plan

> **For agentic workers:** REQUIRED: Use @superpowers:subagent-driven-development or @superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate authentication from custom JWT/OAuth to Auth0 while maintaining user data and roles

**Architecture:** Auth0 handles identity (email/password, social OAuth), local PostgreSQL keeps app-specific data (role, relationships). Backend validates Auth0 JWTs, frontend uses Auth0 React SDK.

**Tech Stack:** FastAPI, React + TypeScript, Auth0, PostgreSQL, SQLAlchemy, pyjwt

---

## File Structure Overview

| File | Responsibility |
|------|---------------|
| `backend/app/auth0.py` | Auth0 JWT validation, JWKS fetching, token parsing |
| `backend/app/routes/auth.py` | Modified: remove password/OAuth routes, keep `/me` endpoint |
| `backend/app/routes/oauth.py` | **DELETE** - Auth0 handles OAuth |
| `backend/app/oauth.py` | **DELETE** - no longer needed |
| `backend/app/auth.py` | **DELETE** - custom JWT replaced by Auth0 |
| `backend/alembic/versions/xxx_add_auth0_id.py` | Migration: add `auth0_id` column, drop `oauth_accounts` |
| `frontend/src/auth0-config.ts` | Auth0 configuration (domain, clientId, audience) |
| `frontend/src/contexts/AuthContext.tsx` | **REPLACE** - use Auth0 React SDK |
| `frontend/src/pages/AuthPage.tsx` | Modified: Auth0 login button, remove password forms |
| `frontend/src/services/api.ts` | Modified: get Auth0 token for API calls |
| `backend/app/config.py` | Modified: add Auth0 settings, remove OAuth client settings |
| `backend/scripts/migrate_users_to_auth0.py` | One-time script to export users to Auth0 |

---

## Chunk 1: Backend Auth0 JWT Validation

### Task 1: Add pyjwt with crypto support

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/requirements.txt` (if exists)

- [ ] **Step 1: Add dependency**

Add to `backend/pyproject.toml` dependencies:
```toml
dependencies = [
    # ... existing deps ...
    "pyjwt[crypto]>=2.8.0",
]
```

- [ ] **Step 2: Commit**

```bash
git add backend/pyproject.toml
git commit -m "deps: add pyjwt[crypto] for Auth0 JWT validation"
```

### Task 2: Create Auth0 JWT validation module

**Files:**
- Create: `backend/app/auth0.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_auth0.py`:
```python
import pytest
from unittest.mock import Mock, patch
from app.auth0 import validate_auth0_token, get_auth0_public_key, Auth0Error


def test_get_auth0_public_key_caches_jwks():
    """JWKS should be fetched and cached."""
    mock_jwks = {
        "keys": [
            {
                "kty": "RSA",
                "kid": "test-key-id",
                "use": "sig",
                "n": "xGOrOr...",  # base64url-encoded modulus
                "e": "AQAB",
            }
        ]
    }

    with patch("app.auth0.requests.get") as mock_get:
        mock_get.return_value = Mock(json=lambda: mock_jwks, status_code=200)

        # First call fetches JWKS
        key1 = get_auth0_public_key("test-key-id", "test.us.auth0.com")
        assert key1 is not None
        assert mock_get.call_count == 1

        # Second call uses cache
        key2 = get_auth0_public_key("test-key-id", "test.us.auth0.com")
        assert mock_get.call_count == 1  # No additional request


def test_validate_auth0_token_invalid_signature():
    """Invalid token signature should raise Auth0Error."""
    with pytest.raises(Auth0Error, match="Invalid token"):
        validate_auth0_token("invalid.token.here", "test.us.auth0.com", "audience")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
pytest tests/test_auth0.py -v
```
Expected: FAIL with "ModuleNotFoundError: No module named 'app.auth0'"

- [ ] **Step 3: Implement auth0.py**

Create `backend/app/auth0.py`:
```python
"""Auth0 JWT validation using JWKS."""

import requests
from datetime import datetime, timezone
from typing import Any

import jwt
from jwt import PyJWKClient


class Auth0Error(Exception):
    """Raised when Auth0 token validation fails."""
    pass


# Cache for JWKS client
_jwks_client: PyJWKClient | None = None
_jwks_domain: str | None = None


def _get_jwks_client(domain: str) -> PyJWKClient:
    """Get or create JWKS client for the domain."""
    global _jwks_client, _jwks_domain

    if _jwks_client is None or _jwks_domain != domain:
        jwks_url = f"https://{domain}/.well-known/jwks.json"
        _jwks_client = PyJWKClient(jwks_url)
        _jwks_domain = domain

    return _jwks_client


def validate_auth0_token(
    token: str,
    domain: str,
    audience: str,
    issuer_prefix: str = "https://",
) -> dict[str, Any]:
    """Validate an Auth0 access token and return the payload.

    Args:
        token: The JWT access token from Auth0
        domain: Auth0 domain (e.g., "mytenant.us.auth0.com")
        audience: API identifier configured in Auth0
        issuer_prefix: Protocol prefix for issuer URL

    Returns:
        Decoded token payload with 'sub', 'permissions', etc.

    Raises:
        Auth0Error: If token is invalid, expired, or signature verification fails
    """
    try:
        client = _get_jwks_client(domain)
        signing_key = client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=audience,
            issuer=f"{issuer_prefix}{domain}/",
        )

        return payload

    except jwt.ExpiredSignatureError as e:
        raise Auth0Error("Token has expired") from e
    except jwt.InvalidAudienceError as e:
        raise Auth0Error("Invalid token audience") from e
    except jwt.InvalidIssuerError as e:
        raise Auth0Error("Invalid token issuer") from e
    except jwt.InvalidTokenError as e:
        raise Auth0Error(f"Invalid token: {e}") from e
    except Exception as e:
        raise Auth0Error(f"Token validation failed: {e}") from e


def get_auth0_public_key(kid: str, domain: str) -> Any:
    """Get a public key from Auth0 JWKS by key ID.

    Args:
        kid: Key ID from JWT header
        domain: Auth0 domain

    Returns:
        Public key object for JWT verification
    """
    client = _get_jwks_client(domain)
    signing_key = client.get_signing_key(kid)
    return signing_key.key


def extract_user_id(payload: dict[str, Any]) -> str:
    """Extract Auth0 user ID (sub claim) from token payload."""
    user_id = payload.get("sub")
    if not user_id:
        raise Auth0Error("Token missing 'sub' claim")
    return user_id


def extract_email(payload: dict[str, Any]) -> str | None:
    """Extract email from token payload (may be in different claims)."""
    # Auth0 access tokens: check custom claims or userinfo scope
    return payload.get("email") or payload.get("https://email")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_auth0.py -v
```
Expected: PASS (or some tests may fail with mocked data - fix as needed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/auth0.py backend/tests/test_auth0.py
git commit -m "feat(auth0): add JWT validation with JWKS support"
```

---

## Chunk 2: Backend Auth Routes Refactor

### Task 3: Add Auth0 settings to config

**Files:**
- Modify: `backend/app/config.py`

- [ ] **Step 1: Add Auth0 settings**

Add to `backend/app/config.py` Settings class:
```python
    # Auth0 Configuration
    auth0_domain: str = Field(
        default="",
        description="Auth0 tenant domain (e.g., mytenant.us.auth0.com)"
    )
    auth0_api_audience: str = Field(
        default="",
        description="Auth0 API identifier"
    )
    auth0_client_id: str = Field(
        default="",
        description="Auth0 application client ID"
    )
    auth0_client_secret: str = Field(
        default="",
        description="Auth0 application client secret (for management API)"
    )

    @field_validator("auth0_domain")
    @classmethod
    def validate_auth0_domain(cls, v: str) -> str:
        if v and not v.endswith(".auth0.com") and not v.endswith(".okta.com"):
            raise ValueError("auth0_domain must be a valid Auth0/Okta domain")
        return v
```

Remove OAuth client settings (mark as deprecated, will remove later):
```python
    # OAuth provider credentials - DEPRECATED, moved to Auth0
    google_client_id: str = Field(default="", description="Deprecated: use Auth0")
    google_client_secret: str = Field(default="", description="Deprecated: use Auth0")
    github_client_id: str = Field(default="", description="Deprecated: use Auth0")
    github_client_secret: str = Field(default="", description="Deprecated: use Auth0")
    discord_client_id: str = Field(default="", description="Deprecated: use Auth0")
    discord_client_secret: str = Field(default="", description="Deprecated: use Auth0")
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/config.py
git commit -m "config: add Auth0 settings, deprecate OAuth client settings"
```

### Task 4: Create new auth dependency

**Files:**
- Create: `backend/app/dependencies/auth.py` (or modify existing)

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_dependencies_auth.py`:
```python
import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user_auth0
from app.auth0 import Auth0Error


@pytest.mark.asyncio
async def test_get_current_user_auth0_no_header():
    """Should raise 401 when no Authorization header."""
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user_auth0(None, Mock(spec=AsyncSession))
    assert exc_info.value.status_code == 401
    assert "Missing" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_user_auth0_invalid_bearer():
    """Should raise 401 when header doesn't start with Bearer."""
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user_auth0("Basic xyz", Mock(spec=AsyncSession))
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_auth0_valid_token_creates_user():
    """Should create new user if auth0_id not found."""
    from app.models import User

    mock_payload = {
        "sub": "auth0|123456",
        "email": "new@example.com",
        "name": "New User",
    }

    with patch("app.dependencies.auth.validate_auth0_token", return_value=mock_payload):
        with patch("app.dependencies.auth.settings") as mock_settings:
            mock_settings.auth0_domain = "test.us.auth0.com"
            mock_settings.auth0_api_audience = "my-api"

            mock_db = AsyncMock(spec=AsyncSession)
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = None  # User not found
            mock_db.execute.return_value = mock_result

            # Should create new user
            user = await get_current_user_auth0("Bearer valid_token", mock_db)

            assert mock_db.add.called
            assert mock_db.commit.called
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_dependencies_auth.py -v
```
Expected: ImportError for app.dependencies.auth

- [ ] **Step 3: Create auth dependency**

Create `backend/app/dependencies/__init__.py`:
```python
"""Shared FastAPI dependencies."""
```

Create `backend/app/dependencies/auth.py`:
```python
"""Auth0 authentication dependencies for FastAPI routes."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth0 import Auth0Error, extract_user_id, validate_auth0_token
from app.config import settings
from app.database import get_db
from app.models import User


async def get_current_user_auth0(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate Auth0 token and return the current user.

    Creates a new local user record if the Auth0 user hasn't logged in before.
    Syncs email/name from Auth0 token to local DB on each login.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.removeprefix("Bearer ")

    # Validate Auth0 configuration
    if not settings.auth0_domain or not settings.auth0_api_audience:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth0 is not configured",
        )

    try:
        payload = validate_auth0_token(
            token,
            domain=settings.auth0_domain,
            audience=settings.auth0_api_audience,
        )
    except Auth0Error as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    auth0_user_id = extract_user_id(payload)

    # Look up user by auth0_id
    result = await db.execute(select(User).where(User.auth0_id == auth0_user_id))
    user = result.scalar_one_or_none()

    if user:
        # Sync data from Auth0 token
        email = payload.get("email") or payload.get("https://email")
        name = payload.get("name") or payload.get("https://name") or payload.get("nickname")

        if email and user.email != email:
            user.email = email
        if name and user.name != name:
            user.name = name

        await db.commit()
        return user

    # User doesn't exist locally - create them
    # Extract profile data from token
    email = payload.get("email") or payload.get("https://email")
    name = (
        payload.get("name")
        or payload.get("https://name")
        or payload.get("nickname")
        or (email.split("@")[0] if email else "User")
    )

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token missing email claim",
        )

    # Check for email conflict with existing non-Auth0 user
    result = await db.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()
    if existing:
        # Link existing user to Auth0
        existing.auth0_id = auth0_user_id
        await db.commit()
        return existing

    # Create new user
    new_user = User(
        auth0_id=auth0_user_id,
        email=email,
        name=name,
        role="participant",  # Default role
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


# Backward compatibility alias
get_current_user = get_current_user_auth0
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_dependencies_auth.py -v
```
Expected: Tests pass (may need to adjust based on actual test results)

- [ ] **Step 5: Commit**

```bash
git add backend/app/dependencies/ backend/tests/test_dependencies_auth.py
git commit -m "feat(auth): add Auth0 token validation dependency"
```

### Task 5: Update User model with auth0_id

**Files:**
- Modify: `backend/app/models.py`

- [ ] **Step 1: Add auth0_id column to User model**

Modify `backend/app/models.py` User class:
```python
class User(Base):
    __tablename__ = "users"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    auth0_id = Column(String(255), unique=True, nullable=True, index=True)  # NEW
    email = Column(String(320), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.participant)
    password_hash = Column(String(128), nullable=True)  # Will be removed in Phase 5
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    # ... relationships unchanged ...
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/models.py
git commit -m "model: add auth0_id column to User model"
```

### Task 6: Create database migration

**Files:**
- Create: `backend/alembic/versions/` (auto-generated)

- [ ] **Step 1: Generate migration**

```bash
cd backend
alembic revision --autogenerate -m "add auth0_id_to_users"
```

- [ ] **Step 2: Review and edit migration**

Check `backend/alembic/versions/xxx_add_auth0_id_to_users.py`:
- Should add `auth0_id` column
- Should NOT drop `oauth_accounts` yet (Phase 5)
- Should NOT drop `password_hash` yet (Phase 5)

Manually edit if needed:
```python
"""add auth0_id_to_users

Revision ID: xxx
Revises: yyy
Create Date: 2026-05-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'xxx'
down_revision: Union[str, None] = 'yyy'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('auth0_id', sa.String(length=255), nullable=True))
    op.create_index('ix_users_auth0_id', 'users', ['auth0_id'], unique=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('ix_users_auth0_id', table_name='users')
    op.drop_column('users', 'auth0_id')
    # ### end Alembic commands ###
```

- [ ] **Step 3: Run migration locally**

```bash
alembic upgrade head
```

- [ ] **Step 4: Commit**

```bash
git add backend/alembic/versions/
git commit -m "migration: add auth0_id column to users table"
```

### Task 7: Refactor auth routes

**Files:**
- Modify: `backend/app/routes/auth.py`

- [ ] **Step 1: Remove password-based routes**

Edit `backend/app/routes/auth.py`, remove:
- `register` endpoint (POST /register)
- `login` endpoint (POST /login)
- `_get_current_user_id` helper (replaced by dependency)
- OAuth link/unlink endpoints (GET /me/oauth/link/{provider}, DELETE /me/oauth/{provider}, GET /me/oauth)

Keep only:
- `get_current_user` dependency import from new location
- `get_me` endpoint (GET /me) - modify to use new dependency

- [ ] **Step 2: Update imports and get_me endpoint**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies.auth import get_current_user  # NEW import
from app.models import User
from app.schemas import UserResponse

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the current authenticated user."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role.value,
        created_at=current_user.created_at,
    )
```

- [ ] **Step 3: Update all route files that use get_current_user**

Find and update all files using old `get_current_user`:
```bash
grep -r "from app.routes.auth import get_current_user" backend/app/
```

Update each to use `from app.dependencies.auth import get_current_user`

Common files to check:
- `backend/app/routes/hackathons.py`
- `backend/app/routes/submissions.py`
- `backend/app/routes/tracks.py`
- `backend/app/routes/assistant.py`
- Any other route files

- [ ] **Step 4: Test routes**

```bash
cd backend
pytest tests/test_auth.py -v -k "test_me"  # or whatever tests exist
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/routes/auth.py backend/app/routes/
git commit -m "refactor(auth): remove password/OAuth routes, use Auth0 dependency"
```

### Task 8: Remove old OAuth routes file

**Files:**
- Delete: `backend/app/routes/oauth.py`

- [ ] **Step 1: Remove OAuth routes from app**

Edit `backend/app/main.py` or wherever routers are included:
Remove:
```python
from app.routes import oauth
# ...
app.include_router(oauth.router, prefix="/api/auth/oauth", tags=["oauth"])
```

- [ ] **Step 2: Delete oauth.py routes file**

```bash
git rm backend/app/routes/oauth.py
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "refactor(auth): remove OAuth callback routes (now in Auth0)"
```

---

## Chunk 3: Frontend Auth0 Integration

### Task 9: Install Auth0 React SDK

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Install dependency**

```bash
cd frontend
npm install @auth0/auth0-react
```

- [ ] **Step 2: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "deps: install @auth0/auth0-react"
```

### Task 10: Create Auth0 config

**Files:**
- Create: `frontend/src/auth0-config.ts`

- [ ] **Step 1: Create config file**

```typescript
// frontend/src/auth0-config.ts

export const auth0Config = {
  domain: import.meta.env.VITE_AUTH0_DOMAIN || "",
  clientId: import.meta.env.VITE_AUTH0_CLIENT_ID || "",
  authorizationParams: {
    redirect_uri: `${window.location.origin}/#/auth/callback`,
    audience: import.meta.env.VITE_AUTH0_AUDIENCE || "",
  },
  cacheLocation: "localstorage" as const,
  useRefreshTokens: true,
};

// Validate config
export function validateAuth0Config(): void {
  const required = [
    "VITE_AUTH0_DOMAIN",
    "VITE_AUTH0_CLIENT_ID",
    "VITE_AUTH0_AUDIENCE",
  ];

  const missing = required.filter(
    (key) => !import.meta.env[key]
  );

  if (missing.length > 0) {
    console.warn(
      `Missing Auth0 environment variables: ${missing.join(", ")}. Auth will not work.`
    );
  }
}
```

- [ ] **Step 2: Update .env.example**

Add to `frontend/.env.example`:
```
# Auth0 Configuration
VITE_AUTH0_DOMAIN=your-tenant.us.auth0.com
VITE_AUTH0_CLIENT_ID=your-client-id
VITE_AUTH0_AUDIENCE=https://api.hackthevalley.io
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/auth0-config.ts frontend/.env.example
git commit -m "config: add Auth0 configuration file"
```

### Task 11: Replace AuthContext with Auth0

**Files:**
- Replace: `frontend/src/contexts/AuthContext.tsx`

- [ ] **Step 1: Rewrite AuthContext to wrap Auth0**

Replace `frontend/src/contexts/AuthContext.tsx`:
```typescript
import { useAuth0 } from "@auth0/auth0-react";
import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import * as api from "../services/api";

interface User {
  id: string;
  email: string;
  name: string;
  role: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: () => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const {
    isAuthenticated,
    isLoading: auth0Loading,
    user: auth0User,
    getAccessTokenSilently,
    loginWithRedirect,
    logout: auth0Logout,
  } = useAuth0();

  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Fetch user profile from backend when Auth0 auth changes
  useEffect(() => {
    if (isAuthenticated && !auth0Loading) {
      setIsLoading(true);

      getAccessTokenSilently()
        .then((accessToken) => {
          setToken(accessToken);
          // Set token for API calls
          localStorage.setItem("auth_token", accessToken);

          // Fetch user profile from our backend
          return api.getMe();
        })
        .then((userData) => {
          setUser({
            id: userData.id,
            email: userData.email,
            name: userData.name,
            role: userData.role,
          });
        })
        .catch((err) => {
          console.error("Failed to fetch user profile:", err);
          // Token invalid or other error - clear auth
          localStorage.removeItem("auth_token");
          setToken(null);
          setUser(null);
        })
        .finally(() => {
          setIsLoading(false);
        });
    } else if (!isAuthenticated && !auth0Loading) {
      // Not authenticated
      localStorage.removeItem("auth_token");
      setToken(null);
      setUser(null);
      setIsLoading(false);
    }
  }, [isAuthenticated, auth0Loading, getAccessTokenSilently]);

  const login = () => {
    loginWithRedirect();
  };

  const logout = () => {
    localStorage.removeItem("auth_token");
    auth0Logout({
      logoutParams: {
        returnTo: window.location.origin,
      },
    });
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading: isLoading || auth0Loading,
        isAuthenticated,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
```

- [ ] **Step 2: Update App.tsx to use Auth0Provider**

Edit `frontend/src/App.tsx`:
```typescript
import { Auth0Provider } from "@auth0/auth0-react";
import { AuthProvider } from "./contexts/AuthContext";
import { auth0Config, validateAuth0Config } from "./auth0-config";

// Validate config on load
validateAuth0Config();

function App() {
  return (
    <Auth0Provider {...auth0Config}>
      <AuthProvider>
        {/* ... rest of app ... */}
      </AuthProvider>
    </Auth0Provider>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/contexts/AuthContext.tsx frontend/src/App.tsx
git commit -m "feat(auth): integrate Auth0 React SDK in AuthContext"
```

### Task 12: Update AuthPage

**Files:**
- Modify: `frontend/src/pages/AuthPage.tsx`

- [ ] **Step 1: Remove password forms, add Auth0 login**

Replace `frontend/src/pages/AuthPage.tsx`:
```typescript
import { useEffect } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useMediaQuery } from "../hooks/useMediaQuery";
import {
  PRIMARY,
  ERROR_TEXT,
  ERROR_BG20,
  ERROR,
  TEXT_MUTED,
  TEXT_PRIMARY,
  PAGE_BG,
} from "../theme";

export default function AuthPage() {
  const { isAuthenticated, isLoading, loginWithRedirect } = useAuth0();
  const navigate = useNavigate();
  const { isMobile } = useMediaQuery();
  const [searchParams] = useSearchParams();

  const urlError = searchParams.get("error");

  // Redirect already-logged-in users
  useEffect(() => {
    if (isAuthenticated && !isLoading) {
      navigate("/", { replace: true });
    }
  }, [isAuthenticated, isLoading, navigate]);

  const handleLogin = () => {
    loginWithRedirect({
      authorizationParams: {
        screen_hint: "login",
      },
    });
  };

  const handleSignup = () => {
    loginWithRedirect({
      authorizationParams: {
        screen_hint: "signup",
      },
    });
  };

  if (isLoading) {
    return (
      <div
        style={{
          maxWidth: 400,
          margin: isMobile ? "30px auto" : "60px auto",
          padding: isMobile ? 14 : 24,
          textAlign: "center",
          color: TEXT_MUTED,
        }}
      >
        Loading...
      </div>
    );
  }

  return (
    <div
      style={{
        maxWidth: 400,
        margin: isMobile ? "30px auto" : "60px auto",
        padding: isMobile ? 14 : 24,
      }}
    >
      <h1 style={{ textAlign: "center", marginBottom: 24 }}>Welcome</h1>

      {urlError && (
        <div
          style={{
            background: ERROR_BG20,
            border: `1px solid ${ERROR}`,
            borderRadius: 8,
            padding: 12,
            marginBottom: 16,
            color: ERROR_TEXT,
          }}
        >
          {urlError === "oauth_denied"
            ? "Login was cancelled."
            : `Authentication error: ${urlError}`}
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <button
          onClick={handleLogin}
          style={{
            width: "100%",
            padding: "14px",
            background: PRIMARY,
            border: "none",
            borderRadius: 8,
            color: "#fff",
            fontSize: 16,
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Sign In
        </button>

        <button
          onClick={handleSignup}
          style={{
            width: "100%",
            padding: "14px",
            background: "transparent",
            border: `1px solid ${PRIMARY}`,
            borderRadius: 8,
            color: PRIMARY,
            fontSize: 16,
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Create Account
        </button>
      </div>

      <p
        style={{
          textAlign: "center",
          marginTop: 24,
          fontSize: 14,
          color: TEXT_MUTED,
        }}
      >
        You can sign in with email/password or social accounts via Auth0.
      </p>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/AuthPage.tsx
git commit -m "feat(auth): update AuthPage to use Auth0 Universal Login"
```

### Task 13: Create Auth0 callback handler

**Files:**
- Create: `frontend/src/pages/AuthCallbackPage.tsx`

- [ ] **Step 1: Create callback page**

```typescript
// frontend/src/pages/AuthCallbackPage.tsx
import { useAuth0 } from "@auth0/auth0-react";
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { PAGE_BG, TEXT_MUTED } from "../theme";

export default function AuthCallbackPage() {
  const { isLoading, isAuthenticated, error } = useAuth0();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isLoading) {
      if (isAuthenticated) {
        navigate("/", { replace: true });
      } else if (error) {
        navigate(`/auth?error=${encodeURIComponent(error.message)}`, {
          replace: true,
        });
      }
    }
  }, [isLoading, isAuthenticated, error, navigate]);

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: PAGE_BG,
        color: TEXT_MUTED,
      }}
    >
      Completing authentication...
    </div>
  );
}
```

- [ ] **Step 2: Add route to App.tsx**

Add to routes:
```typescript
import AuthCallbackPage from "./pages/AuthCallbackPage";

// In routes array:
{ path: "/auth/callback", element: <AuthCallbackPage /> }
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/AuthCallbackPage.tsx frontend/src/App.tsx
git commit -m "feat(auth): add Auth0 callback handler page"
```

### Task 14: Update API service for Auth0 tokens

**Files:**
- Modify: `frontend/src/services/api.ts`

- [ ] **Step 1: Update API to use Auth0 token from localStorage**

Edit `frontend/src/services/api.ts`:

The API service likely already reads from localStorage. Verify it works:
```typescript
// Should already exist - verify token is read from localStorage
const getToken = () => localStorage.getItem("auth_token");

// In request headers:
headers: {
  "Authorization": `Bearer ${getToken()}`,
  // ...
}
```

No changes needed if already using localStorage pattern.

- [ ] **Step 2: Commit (if changes made)**

```bash
git add frontend/src/services/api.ts
git commit -m "refactor(api): verify Auth0 token integration"
```

---

## Chunk 4: User Migration Script

### Task 15: Create user migration script

**Files:**
- Create: `backend/scripts/migrate_users_to_auth0.py`

- [ ] **Step 1: Create migration script**

```python
#!/usr/bin/env python3
"""
Migrate existing users to Auth0.

This script:
1. Reads users from local database
2. Creates users in Auth0 via Management API
3. Links existing OAuth accounts as identities
4. Outputs mapping of local user_id -> auth0_id

Usage:
    export AUTH0_DOMAIN=your-tenant.us.auth0.com
    export AUTH0_CLIENT_ID=management-api-client-id
    export AUTH0_CLIENT_SECRET=management-api-client-secret
    export DATABASE_URL=postgresql+asyncpg://...
    python migrate_users_to_auth0.py
"""

import asyncio
import json
import os
import sys
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models import User, OAuthAccount


# Auth0 Management API
AUTH0_DOMAIN = os.environ.get("AUTH0_DOMAIN", "")
AUTH0_CLIENT_ID = os.environ.get("AUTH0_CLIENT_ID", "")
AUTH0_CLIENT_SECRET = os.environ.get("AUTH0_CLIENT_SECRET", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")


async def get_auth0_token() -> str:
    """Get Auth0 Management API access token."""
    url = f"https://{AUTH0_DOMAIN}/oauth/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": AUTH0_CLIENT_ID,
        "client_secret": AUTH0_CLIENT_SECRET,
        "audience": f"https://{AUTH0_DOMAIN}/api/v2/",
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()["access_token"]


async def create_auth0_user(
    token: str,
    email: str,
    name: str,
    email_verified: bool = True,
) -> str | None:
    """Create a user in Auth0. Returns auth0_id or None on conflict."""
    url = f"https://{AUTH0_DOMAIN}/api/v2/users"

    # Generate a secure random password (users will use password reset)
    import secrets
    temp_password = secrets.token_urlsafe(32)

    payload = {
        "email": email,
        "name": name,
        "password": temp_password,
        "connection": "Username-Password-Authentication",
        "email_verified": email_verified,
        "verify_email": False,  # Don't send verification for migrated users
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )

        if resp.status_code == 409:
            # User already exists - find them
            search_url = f"https://{AUTH0_DOMAIN}/api/v2/users"
            search_resp = await client.get(
                search_url,
                params={"q": f'email:"{email}"', "search_engine": "v3"},
                headers={"Authorization": f"Bearer {token}"},
            )
            search_resp.raise_for_status()
            users = search_resp.json()
            if users:
                return users[0]["user_id"]
            return None

        resp.raise_for_status()
        return resp.json()["user_id"]


async def trigger_password_reset(token: str, email: str) -> bool:
    """Trigger a password reset email for a migrated user."""
    url = f"https://{AUTH0_DOMAIN}/api/v2/tickets/password-change"

    payload = {
        "user_id": None,  # Will be looked up by email
        "email": email,
        "connection_id": None,  # Will use default connection
        "email_verified": True,
        "ttl_sec": 0,  # Use default TTL
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )

        if resp.status_code == 201:
            return True
        return False


async def migrate_users():
    """Main migration function."""
    if not all([AUTH0_DOMAIN, AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET, DATABASE_URL]):
        print("Missing required environment variables")
        print("Need: AUTH0_DOMAIN, AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET, DATABASE_URL")
        sys.exit(1)

    print(f"Starting migration to Auth0 domain: {AUTH0_DOMAIN}")

    # Get Auth0 token
    print("Getting Auth0 Management API token...")
    token = await get_auth0_token()
    print("Got token.")

    # Connect to database
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Get all users
        result = await session.execute(select(User))
        users = result.scalars().all()

        print(f"Found {len(users)} users to migrate")

        # Migration results
        results = []
        errors = []

        for user in users:
            try:
                print(f"Migrating user: {user.email} ({user.id})")

                # Create user in Auth0
                auth0_id = await create_auth0_user(
                    token,
                    user.email,
                    user.name,
                    email_verified=True,
                )

                if auth0_id:
                    print(f"  -> Auth0 ID: {auth0_id}")

                    # Update local user record
                    user.auth0_id = auth0_id
                    await session.commit()

                    # Trigger password reset for users with passwords
                    if user.password_hash:
                        await trigger_password_reset(token, user.email)
                        print(f"  -> Password reset email sent")

                    results.append({
                        "local_id": str(user.id),
                        "auth0_id": auth0_id,
                        "email": user.email,
                        "status": "migrated",
                    })
                else:
                    errors.append({
                        "local_id": str(user.id),
                        "email": user.email,
                        "error": "Failed to create or find Auth0 user",
                    })

            except Exception as e:
                print(f"  -> ERROR: {e}")
                errors.append({
                    "local_id": str(user.id),
                    "email": user.email,
                    "error": str(e),
                })

    # Print summary
    print("\n" + "=" * 50)
    print("MIGRATION SUMMARY")
    print("=" * 50)
    print(f"Total users: {len(users)}")
    print(f"Successful: {len(results)}")
    print(f"Errors: {len(errors)}")

    if errors:
        print("\nErrors:")
        for e in errors:
            print(f"  - {e['email']}: {e['error']}")

    # Save results
    with open("migration_results.json", "w") as f:
        json.dump({"migrated": results, "errors": errors}, f, indent=2)
    print("\nResults saved to migration_results.json")


if __name__ == "__main__":
    asyncio.run(migrate_users())
```

- [ ] **Step 2: Commit**

```bash
git add backend/scripts/migrate_users_to_auth0.py
git commit -m "feat(auth): add user migration script for Auth0"
```

---

## Chunk 5: Cleanup and Finalization

### Task 16: Create final cleanup migration

**Files:**
- Create: `backend/alembic/versions/xxx_cleanup_auth_tables.py`

- [ ] **Step 1: Generate cleanup migration**

After user migration is complete and verified:

```bash
cd backend
alembic revision -m "cleanup auth tables post auth0 migration"
```

- [ ] **Step 2: Write cleanup migration**

Edit generated file:
```python
"""cleanup auth tables post auth0 migration

Revision ID: xxx
Revises: yyy
Create Date: 2026-05-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'xxx'
down_revision: Union[str, None] = 'yyy'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop oauth_accounts table
    op.drop_table('oauth_accounts')

    # Remove password_hash column from users
    op.drop_column('users', 'password_hash')

    # Make auth0_id non-nullable after migration is complete
    op.alter_column('users', 'auth0_id', nullable=False)


def downgrade() -> None:
    # Restore password_hash
    op.add_column('users', sa.Column('password_hash', sa.String(128), nullable=True))

    # Make auth0_id nullable again
    op.alter_column('users', 'auth0_id', nullable=True)

    # Recreate oauth_accounts table
    op.create_table(
        'oauth_accounts',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('provider', sa.String(20), nullable=False),
        sa.Column('provider_user_id', sa.String(255), nullable=False),
        sa.Column('provider_email', sa.String(320), nullable=True),
        sa.Column('user_id', postgresql.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider', 'provider_user_id', name='ix_oauth_accounts_provider_user')
    )
```

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/
git commit -m "migration: cleanup legacy auth tables after Auth0 migration"
```

### Task 17: Remove legacy auth files

**Files:**
- Delete: `backend/app/auth.py`
- Delete: `backend/app/oauth.py`
- Modify: `backend/pyproject.toml` (remove bcrypt, python-jose)

- [ ] **Step 1: Delete legacy files**

```bash
git rm backend/app/auth.py
git rm backend/app/oauth.py
```

- [ ] **Step 2: Remove unused dependencies**

Edit `backend/pyproject.toml`:
Remove:
```toml
    # "bcrypt>=4.0.0",  # Removed: Auth0 handles passwords
    # "python-jose[cryptography]>=3.3.0",  # Removed: using pyjwt instead
```

- [ ] **Step 3: Remove unused imports from files**

Check for any remaining imports of deleted modules:
```bash
grep -r "from app.auth import" backend/app/ --include="*.py"
grep -r "from app.oauth import" backend/app/ --include="*.py"
```

Clean up any remaining references.

- [ ] **Step 4: Commit**

```bash
git add backend/app/ backend/pyproject.toml
git commit -m "refactor(auth): remove legacy JWT and OAuth modules"
```

### Task 18: Update documentation

**Files:**
- Modify: `README.md` or `docs/auth.md`

- [ ] **Step 1: Document Auth0 setup**

Create/update docs:
```markdown
# Authentication Setup

## Auth0 Configuration

1. Create Auth0 tenant at https://auth0.com
2. Create a Single Page Application
3. Create an API with identifier (e.g., `https://api.hackthevalley.io`)
4. Configure connections:
   - Database (Username-Password)
   - Google (social)
   - GitHub (social)
   - Discord (social, may need custom setup)

## Environment Variables

### Backend
```
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_API_AUDIENCE=https://api.hackthevalley.io
AUTH0_CLIENT_ID=...
AUTH0_CLIENT_SECRET=...
```

### Frontend
```
VITE_AUTH0_DOMAIN=your-tenant.us.auth0.com
VITE_AUTH0_CLIENT_ID=...
VITE_AUTH0_AUDIENCE=https://api.hackthevalley.io
```

## User Migration

See `backend/scripts/migrate_users_to_auth0.py`
```

- [ ] **Step 2: Commit**

```bash
git add docs/ README.md
git commit -m "docs: update authentication documentation for Auth0"
```

---

## Deployment Checklist

Before deploying to production:

- [ ] Auth0 tenant configured with production URLs
- [ ] User migration script tested in staging
- [ ] All tests pass
- [ ] Frontend environment variables set in Vercel
- [ ] Backend environment variables set on server
- [ ] Database migrations run successfully
- [ ] Rollback plan documented

## Rollback Plan

If issues occur after deployment:

1. **Revert code**: `git revert HEAD~N` (N commits = number of migration commits)
2. **Database**: Rollback migrations if needed
3. **Environment**: Restore old OAuth credentials temporarily
4. **Users**: Existing sessions will expire naturally (Auth0 tokens have expiry)

---

Plan complete and saved to `docs/superpowers/plans/2026-05-04-auth0-migration.md`. Ready to execute?
