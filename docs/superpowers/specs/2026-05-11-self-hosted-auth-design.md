# Self-Hosted Auth System Design

> **Goal:** Replace Clerk with a fully self-contained auth system that supports local password auth, OAuth2 (GitHub/Google), and invite-only registration — so an organizer can clone, configure, and run a complete hackathon platform with zero external SaaS dependencies.

**Architecture:** Built-in JWT auth with bcrypt password hashing, pluggable OAuth2 providers stored in the database, and a first-run bootstrap via environment variables. All Clerk dependencies are removed.

**Tech Stack:** FastAPI, SQLAlchemy, bcrypt, python-jose (JWT), Fernet (OAuth secret encryption), httpx (OAuth token exchange).

---

## 1. Core Auth Architecture

### 1.1 Password Auth

- **Registration**: Email + password + name. Password hashed with bcrypt (cost factor 12). Auto-assign `participant` role.
- **First-run protection**: Public registration is **blocked** until at least one `organizer` user exists. This prevents a race condition where a random visitor creates the first account before the admin sets up the platform.
- **Login**: Email + password → issue JWT access token (15 min expiry) + refresh token (7 day expiry, stored in httpOnly cookie).
- **Token refresh**: `/api/auth/refresh` endpoint reads refresh token cookie, validates against DB `refresh_tokens` table, issues new access token.
- **Logout**: Clear refresh token cookie **and** mark the token as revoked in DB (`revoked_at` timestamp). Do not rely on expiry alone.
- **Password reset**: Generate reset token (1 hour expiry), send email with reset link via the existing Mailpit/SendGrid email service.
- **Change password**: Authenticated endpoint requiring current password + new password.

### 1.2 OAuth2 Framework

- **Generic OAuth provider model**: `OAuthProvider` table with `name`, `client_id`, `client_secret_encrypted`, `authorize_url`, `token_url`, `userinfo_url`, `scope`, `is_active`.
- **OAuth login flow**: `/api/auth/oauth/{provider}/login` → redirect to provider authorize URL → `/api/auth/oauth/{provider}/callback` → exchange code for token → fetch userinfo → find or create local user → issue JWT.
- **OAuth account linking**: `OAuthAccount` table (already exists) maps `(provider, provider_user_id)` → `user_id`. If a user with matching email already exists **and the OAuth provider returns `email_verified=true`**, link the OAuth account. Otherwise require password login first, then manual linking.
- **Encrypted secrets**: OAuth client secrets encrypted at rest using Fernet. The Fernet key is derived from `HACKVERIFY_SECRET_KEY` via HKDF-SHA256 to produce a 32-byte key, then base64-encoded for Fernet.

### 1.3 First-Run Bootstrap

- On app startup, if the `users` table is empty, check for `HACKVERIFY_ADMIN_EMAIL` and `HACKVERIFY_ADMIN_PASSWORD` in environment variables.
- If both are present, create a user with that email, hashed password, name = "Admin", and role = `organizer`.
- If env vars are missing and DB is empty, log a warning: "No users found and HACKVERIFY_ADMIN_EMAIL not set. Set HACKVERIFY_ADMIN_EMAIL and HACKVERIFY_ADMIN_PASSWORD to create the first organizer, then restart the app."
- The admin should remove `HACKVERIFY_ADMIN_PASSWORD` from `.env` after first run.

### 1.4 Role-Based Access Control

- Keep the existing three global roles: `organizer`, `participant`, `judge`.
- JWT payload contains: `sub` (user id), `email`, `role`, `exp`, `iat`.
- Keep existing `require_user`, `require_organizer`, `require_participant`, `require_judge` dependency injection patterns — swap Clerk-based JWT validation for local JWT validation using `python-jose`.
- **Judge role note**: A user with global role `judge` can judge any hackathon they are assigned to. Judge invites (Section 4.2) create accounts with `judge` role directly. There is no per-hackathon judge role; the global role suffices.

---

## 2. OAuth Provider Management

### 2.1 Database Schema

Use existing `Guid` and `String(64)` key patterns from `app/models.py`:

```python
class OAuthProvider(Base):
    __tablename__ = "oauth_providers"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False)  # 'github', 'google'
    display_name = Column(String(100), nullable=False)
    client_id = Column(String(255), nullable=False)
    client_secret_encrypted = Column(Text, nullable=False)
    authorize_url = Column(Text, nullable=False)
    token_url = Column(Text, nullable=False)
    userinfo_url = Column(Text, nullable=False)
    scope = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
```

The existing `OAuthAccount` table is augmented:

```python
# Add to existing OAuthAccount in models.py:
access_token_encrypted = Column(Text, nullable=True)
refresh_token_encrypted = Column(Text, nullable=True)
expires_at = Column(DateTime(timezone=True), nullable=True)
```

New table for refresh tokens:

```python
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(255), nullable=False)  # SHA-256 hash of the token
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
```

### 2.2 Admin Panel API

- `GET /api/admin/oauth/providers` — List all providers (with `client_secret` masked as `***`). Organizer only.
- `POST /api/admin/oauth/providers` — Add a provider. Body: `name`, `client_id`, `client_secret`, `authorize_url`, `token_url`, `userinfo_url`, `scope`, `display_name`. Built-in presets (GitHub/Google) pre-fill endpoint URLs.
- `DELETE /api/admin/oauth/providers/{name}` — Disconnect a provider. Does NOT delete OAuth-linked users. Organizer only.

### 2.3 Built-in Provider Presets

When adding a provider via the admin panel, the admin selects a preset which pre-fills endpoint URLs:

- **GitHub**: `authorize_url=https://github.com/login/oauth/authorize`, `token_url=https://github.com/login/oauth/access_token`, `userinfo_url=https://api.github.com/user`, `scope=read:user user:email`.
- **Google**: `authorize_url=https://accounts.google.com/o/oauth2/v2/auth`, `token_url=https://oauth2.googleapis.com/token`, `userinfo_url=https://openidconnect.googleapis.com/v1/userinfo`, `scope=openid email profile`.
- **Custom**: Admin fills all fields manually. Supports any standard OAuth2 provider.

---

## 3. Login & Registration UX

### 3.1 Pages

- `/login` — Email + password form. Social login buttons appear dynamically based on active OAuth providers (fetched from `/api/auth/providers`).
- `/register` — Email + password + name form. If platform has no organizer yet, registration is blocked with a message: "Platform setup required. The first account must be created by the server administrator."
- `/forgot-password` — Email input. Sends reset link.
- `/reset-password` — Token from email + new password form.
- `/admin/oauth` — OAuth provider management (organizer only).

### 3.2 Frontend Auth State

Replace `useAuth()` Clerk hook with a custom hook:

- **Token storage**: JWT access token stored in a module-level variable (memory only, never `localStorage`). Refresh token stored in httpOnly cookie by the backend.
- **Initialization sequence on page load**:
  1. Call `POST /api/auth/refresh` with credentials (sends httpOnly cookie). If valid, receive new access token.
  2. Call `GET /api/auth/me` with the access token to get user info.
  3. If refresh fails (expired/revoked), redirect to `/login`.
- **API wrapper**: Adapt the existing `frontend/src/services/api.ts` fetch wrapper to attach `Authorization: Bearer <token>` to all requests. On 401, attempt refresh once, then retry. If refresh fails, redirect to `/login`.
- **Exposed API**: `login(email, password)`, `logout()`, `register(email, password, name)`, `user`, `isLoading`, `isAuthenticated`.

### 3.3 Backend Changes

- Delete `backend/app/clerk_auth.py` entirely.
- Rewrite `backend/app/auth.py` to implement local JWT validation:
  - `create_access_token(data: dict, expires_delta: timedelta)` — Issue JWT with `python-jose`.
  - `create_refresh_token(user_id: str)` — Issue random token (32 bytes, urlsafe base64), store SHA-256 hash in `RefreshToken` table.
  - `verify_access_token(token: str)` — Decode and validate JWT with `python-jose`.
  - `verify_refresh_token(token: str)` — Look up hash in `RefreshToken` table, check not revoked and not expired.
  - `get_current_user(token: str = Depends(oauth2_scheme))` — FastAPI dependency for HTTP routes.
  - `get_current_user_ws(token: str)` — For WebSocket routes (called from `backend/app/routes/websocket.py`).
- Update `require_organizer`, `require_participant`, `require_judge` to use `get_current_user`.

---

## 4. Invite-Only Registration

### 4.1 Two-Layer Model

- **Platform-level**: Anyone can create a global account once an organizer exists. No invite needed for signup.
- **Hackathon-level**: Each hackathon has `registration_mode`: `"open"` (default) or `"invite_only"`. When `"invite_only"`, registering for that specific hackathon requires an invite code.

This distinction is critical: users need accounts to browse the platform, but only invited users can register for a restricted hackathon.

### 4.2 Per-Hackathon Toggle

- Add `registration_mode` enum column to `hackathons` table: `"open"` or `"invite_only"`, default `"open"`.
- Organizer sets this in Hackathon Settings.
- When `invite_only`:
  - `POST /api/hackathons/{id}/register` (or existing registration endpoint) requires `invite_code` field.
  - Endpoint validates code against `HackathonInvite` table.

### 4.3 Invite Codes

```python
class HackathonInvite(Base):
    __tablename__ = "hackathon_invites"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    hackathon_id = Column(Guid, ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(32), unique=True, nullable=False)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.participant)
    uses_remaining = Column(Integer, nullable=False, default=1)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(String(64), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
```

- Organizer generates codes in bulk: `POST /api/hackathons/{id}/invites` with `count`, `role`, `expires_days`.
- Codes are random alphanumeric (16 chars), prefixed with hackathon slug, e.g., `OPENHACK-ABC123DEF`.
- Frontend displays codes in a table with copy button, uses remaining, expiry.
- When a code is used: decrement `uses_remaining`. If reaches 0, code is effectively expired.

---

## 5. Data Migration Strategy

### 5.1 Clerk Removal

- `backend/app/clerk_auth.py` is deleted.
- `backend/app/routes/auth.py` currently imports from `clerk_auth` and must be rewritten entirely.
- `backend/app/routes/websocket.py` uses `get_current_user_ws` from `auth.py` — update to use local JWT.
- Frontend: Remove `@clerk/clerk-react` from `package.json`. Replace all `useAuth()` Clerk calls with custom hook.
- Remove `VITE_CLERK_PUBLISHABLE_KEY` from all env files and docker-compose.

### 5.2 Existing Schema Augmentations

The `User` model already has `password_hash` (`String(128)`, nullable). Add new fields:

```python
# Add to User model:
email_verified = Column(Boolean, default=False)
password_reset_token_hash = Column(String(255), nullable=True)  # SHA-256 hash of the plaintext token
password_reset_expires = Column(DateTime(timezone=True), nullable=True)
```

- The plaintext reset token (32 bytes, urlsafe base64) is sent in the email only. Its SHA-256 hash is stored in `password_reset_token_hash`. When the user submits the reset form, hash the submitted token and compare against the stored hash.

The `OAuthAccount` model already exists with `provider`, `provider_user_id`, `provider_email`, `user_id`. Augment it:

```python
# Add to OAuthAccount model:
access_token_encrypted = Column(Text, nullable=True)
refresh_token_encrypted = Column(Text, nullable=True)
expires_at = Column(DateTime(timezone=True), nullable=True)
```

New model: `RefreshToken` (see Section 2.1).
New model: `OAuthProvider` (see Section 2.1).
New model: `HackathonInvite` (see Section 4.3).
New column on `Hackathon`: `registration_mode`.

### 5.3 Email Verification (MVP Deferred)

For the initial implementation, `email_verified` is set to `True` on registration. This is acceptable for a self-hosted hackathon where the organizer controls the participant list. A full email verification flow can be added later.

---

## 6. API Endpoints

### 6.1 Auth Endpoints

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/api/auth/register` | Register new account (blocked until organizer exists) | Public |
| POST | `/api/auth/login` | Login with password | Public |
| POST | `/api/auth/refresh` | Refresh access token | Refresh cookie |
| POST | `/api/auth/logout` | Logout (revokes refresh token) | Refresh cookie |
| POST | `/api/auth/forgot-password` | Request reset link | Public |
| POST | `/api/auth/reset-password` | Reset password with token | Public |
| GET | `/api/auth/me` | Current user info | Bearer JWT |
| GET | `/api/auth/providers` | List active OAuth providers | Public |
| GET | `/api/auth/oauth/{provider}/login` | Initiate OAuth login | Public |
| GET | `/api/auth/oauth/{provider}/callback` | OAuth callback | Public |

### 6.2 Admin OAuth Endpoints

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/api/admin/oauth/providers` | List provider configs (secrets masked) | Organizer |
| POST | `/api/admin/oauth/providers` | Add provider config | Organizer |
| DELETE | `/api/admin/oauth/providers/{name}` | Remove provider | Organizer |

### 6.3 Invite Endpoints

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/api/hackathons/{id}/invites` | Generate invite codes | Organizer |
| GET | `/api/hackathons/{id}/invites` | List invite codes | Organizer |
| DELETE | `/api/invites/{code}` | Revoke invite code | Organizer |

---

## 7. Frontend Changes

### 7.1 New Components

- `LoginForm.tsx` — Email/password + social buttons (dynamically rendered from `/api/auth/providers`)
- `RegisterForm.tsx` — Email/password/name
- `ForgotPasswordForm.tsx`
- `ResetPasswordForm.tsx`
- `OAuthAdminPanel.tsx` — Provider management table + add form with preset selector
- `InviteCodeManager.tsx` — Generate/list/revoke invites for a hackathon

### 7.2 Modified Pages

- `AuthPage.tsx` — Replace Clerk components with custom forms
- `HackathonSettings.tsx` — Add `registration_mode` toggle (`"open"` / `"invite_only"`) + invite code manager
- `Dashboard.tsx`, `HackerDashboard.tsx`, `JudgePortal.tsx`, `OrganizerRegistrationsPage.tsx` — Swap `useAuth()` for custom hook (no functional change)
- `frontend/src/services/api.ts` — Add token attachment and 401 refresh logic

### 7.3 Deleted Dependencies

- `@clerk/clerk-react`
- `@clerk/types`
- `backend/app/clerk_auth.py`

---

## 8. Security Considerations

- **Password policy**: Minimum 8 chars, at least one uppercase, one lowercase, one number. Enforced at registration and password change.
- **Rate limiting**: Login attempts limited to 5 per minute per IP using existing `fastapi-limiter` + Redis.
- **Token security**: Access tokens in `Authorization` header. Refresh tokens in httpOnly, SameSite=strict, Secure (in production) cookies.
- **OAuth state param**: Random state stored in Redis with 5-minute TTL to prevent CSRF.
- **Secret encryption**: OAuth client secrets encrypted with Fernet using a key derived from `HACKVERIFY_SECRET_KEY` via HKDF-SHA256.
- **Refresh token invalidation**: Logout marks token as revoked (`revoked_at`). Do not rely solely on expiry.
- **SQL injection prevention**: All queries via SQLAlchemy ORM.
- **First-run protection**: Registration blocked until an organizer exists prevents unauthorized first-account creation.

---

## 9. Testing Plan

### 9.1 Unit Tests

- Password hashing (bcrypt verify round-trip)
- JWT creation and verification (expired, invalid signature, valid)
- Refresh token creation, hash storage, verification, revocation
- Fernet secret encryption/decryption round-trip
- OAuth state generation and validation
- Invite code generation (format, uniqueness)
- Rate limiting enforcement

### 9.2 Integration Tests

- Full register → login → access protected endpoint → logout flow
- Password reset flow (token generation, expiry, usage)
- OAuth login simulation (mock GitHub/Google token exchange with `respx`)
- Invite-only hackathon registration (valid code, invalid code, expired code, exhausted uses)
- Admin OAuth provider CRUD
- First-run bootstrap (env vars create organizer, missing env vars block registration)
- Token refresh flow (valid refresh, expired refresh, revoked refresh)

### 9.3 E2E Tests

- Playwright: register account, login, view dashboard, logout
- Playwright: login via GitHub OAuth (using a test OAuth app)
- Playwright: organizer generates invite code, participant uses it to register for hackathon

---

## 10. Rollout & Backwards Compatibility

- This is a **breaking change** for any existing Clerk-based deployment.
- Create a feature branch, complete all work, then merge with a major version bump and migration guide.
- For new self-hosted users: this is the default and only auth system.
- Existing `OAuthAccount` data remains valid but augmented with new columns.
