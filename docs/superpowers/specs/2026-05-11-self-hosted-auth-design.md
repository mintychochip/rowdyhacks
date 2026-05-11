# Self-Hosted Auth System Design

> **Goal:** Replace Clerk with a fully self-contained auth system that supports local password auth, OAuth2 (GitHub/Google), and invite-only registration — so an organizer can clone, configure, and run a complete hackathon platform with zero external SaaS dependencies.

**Architecture:** Built-in JWT auth with bcrypt password hashing, pluggable OAuth2 providers stored in the database, and a first-run bootstrap via environment variables. All Clerk dependencies are removed.

**Tech Stack:** FastAPI, SQLAlchemy, bcrypt, PyJWT, python-jose (for JWT verification), Fernet (for OAuth secret encryption), httpx (for OAuth token exchange).

---

## 1. Core Auth Architecture

### 1.1 Password Auth

- **Registration**: Email + password + name. Password hashed with bcrypt (cost factor 12). Auto-assign `participant` role.
- **Login**: Email + password → issue JWT access token (15 min expiry) + refresh token (7 day expiry, stored in httpOnly cookie).
- **Token refresh**: `/api/auth/refresh` endpoint reads refresh token cookie, validates, issues new access token.
- **Logout**: Clear refresh token cookie + invalidate token in DB (or just let it expire for MVP).
- **Password reset**: Generate reset token (1 hour expiry), send email with reset link via the existing Mailpit/SendGrid email service.
- **Change password**: Authenticated endpoint requiring current password + new password.

### 1.2 OAuth2 Framework

- **Generic OAuth provider model**: `OAuthProvider` table with `name`, `client_id`, `client_secret_encrypted`, `authorize_url`, `token_url`, `userinfo_url`, `scope`, `is_active`.
- **OAuth login flow**: `/api/auth/oauth/{provider}/login` → redirect to provider authorize URL → `/api/auth/oauth/{provider}/callback` → exchange code for token → fetch userinfo → find or create local user → issue JWT.
- **OAuth account linking**: `OAuthAccount` table maps `(provider_name, provider_user_id)` → `user_id`. If a user with matching email already exists, link the OAuth account instead of creating a duplicate.
- **Encrypted secrets**: OAuth client secrets encrypted at rest using Fernet with `HACKVERIFY_SECRET_KEY` as the key.

### 1.3 First-Run Bootstrap

- On app startup, if the `users` table is empty, check for `HACKVERIFY_ADMIN_EMAIL` and `HACKVERIFY_ADMIN_PASSWORD` in environment variables.
- If both are present, create a user with that email, hashed password, name = "Admin", and role = `organizer`.
- If env vars are missing and DB is empty, log a warning: "No users found and HACKVERIFY_ADMIN_EMAIL not set. Create the first user via the API or set env vars."
- This eliminates the need for a setup wizard while still allowing fully automated deployments.

### 1.4 Role-Based Access Control

- Keep the existing three roles: `organizer`, `participant`, `judge`.
- JWT payload contains: `sub` (user id), `email`, `role`, `exp`, `iat`.
- Keep existing `require_user`, `require_organizer`, `require_participant`, `require_judge` dependency injection patterns — just swap the Clerk-based JWT validation for local JWT validation.

---

## 2. OAuth Provider Management

### 2.1 Database Schema

```sql
CREATE TABLE oauth_providers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,  -- 'github', 'google', 'custom_1'
    display_name VARCHAR(100) NOT NULL,
    client_id VARCHAR(255) NOT NULL,
    client_secret_encrypted TEXT NOT NULL,
    authorize_url TEXT NOT NULL,
    token_url TEXT NOT NULL,
    userinfo_url TEXT NOT NULL,
    scope TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE oauth_accounts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    provider_name VARCHAR(50) NOT NULL,
    provider_user_id VARCHAR(255) NOT NULL,
    access_token_encrypted TEXT,
    refresh_token_encrypted TEXT,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(provider_name, provider_user_id)
);
```

### 2.2 Admin Panel API

- `GET /api/admin/oauth/providers` — List all providers (with `client_secret` masked as `***`). Organizer only.
- `POST /api/admin/oauth/providers` — Add/connect a provider. Body: `name`, `client_id`, `client_secret`, `authorize_url`, `token_url`, `userinfo_url`, `scope`.
- `DELETE /api/admin/oauth/providers/{name}` — Disconnect a provider. Does NOT delete OAuth-linked users.
- `POST /api/admin/oauth/providers/{name}/connect` — Initiates the "admin connect" OAuth flow. This is a separate flow from user login — the admin grants permission so the app can act on behalf of users. The callback stores the app's client credentials (same as manual config, but via OAuth instead of copy-paste).

### 2.3 One-Click Connect Flow (MVP v2)

For the initial implementation, the manual config form is sufficient. The one-click connect flow is documented here as a future enhancement:

1. Admin clicks "Connect GitHub" in admin panel.
2. Backend generates state param and redirects to `https://github.com/login/oauth/authorize?client_id=GITHUB_APP_CLIENT_ID&scope=...`.
3. Admin grants permission on GitHub.
4. GitHub redirects to `/api/admin/oauth/github/callback`.
5. Backend exchanges code for token, then uses that token to fetch the OAuth app's credentials (if GitHub API supports this — some providers don't expose client_secret via API, so manual entry may always be needed for some).
6. Stores `client_id` and `client_secret` in DB.

**Revised MVP approach**: Admin enters `client_id` and `client_secret` manually via a form. This is what every self-hosted app does (GitLab, Mattermost, etc.) and is reliable across all OAuth providers. One-click connect can be added later as a convenience layer.

### 2.4 Built-in Provider Presets

When adding a provider, the admin can select from presets:

- **GitHub**: Pre-fills `authorize_url=https://github.com/login/oauth/authorize`, `token_url=https://github.com/login/oauth/access_token`, `userinfo_url=https://api.github.com/user`, `scope=read:user user:email`.
- **Google**: Pre-fills Google OAuth2 endpoints and `scope=openid email profile`.
- **Custom**: Admin fills all fields manually. Supports any OAuth2 provider.

---

## 3. Login & Registration UX

### 3.1 Pages

- `/login` — Email + password form. Social login buttons appear dynamically based on active OAuth providers (fetched from `/api/auth/providers`).
- `/register` — Email + password + name form. Checkbox for "I agree to the code of conduct" (links to content page). If hackathon is invite-only, additional field for invite code.
- `/forgot-password` — Email input. Sends reset link.
- `/reset-password` — Token from email + new password form.
- `/admin/oauth` — OAuth provider management (organizer only).

### 3.2 Frontend Auth State

- Replace `useAuth()` Clerk hook with a custom hook that:
  - Stores JWT access token in memory (never localStorage for security).
  - Reads user info from `/api/auth/me` on page load.
  - Automatically refreshes token via `/api/auth/refresh` when access token expires.
  - Exposes `login(email, password)`, `logout()`, `register(email, password, name)`, `user`, `isLoading`, `isAuthenticated`.
- Use Axios interceptors to attach `Authorization: Bearer <token>` header to all API requests and handle 401 by attempting refresh.

### 3.3 Backend Changes

- Delete `backend/app/clerk_auth.py` entirely.
- Modify `backend/app/auth.py` to implement local JWT validation:
  - `create_access_token(data: dict)` — Issue JWT.
  - `create_refresh_token(user_id: int)` — Issue refresh token, store hash in DB `refresh_tokens` table.
  - `verify_token(token: str)` — Decode and validate JWT.
  - `get_current_user(token: str = Depends(oauth2_scheme))` — FastAPI dependency.
- Keep existing `require_organizer`, `require_participant`, `require_judge` but base them on `get_current_user` instead of Clerk.

---

## 4. Invite-Only Registration

### 4.1 Per-Hackathon Toggle

- Add `registration_mode` enum column to `hackathons` table: `"open"` (default) or `"invite_only"`.
- Organizer sets this in Hackathon Settings.
- When `invite_only`:
  - Public registration endpoint requires `invite_code` field.
  - `POST /api/auth/register` checks code against `HackathonInvite` table.
  - `POST /api/registrations` also validates invite code (for existing users registering for a specific hackathon).

### 4.2 Invite Codes

```sql
CREATE TABLE hackathon_invites (
    id SERIAL PRIMARY KEY,
    hackathon_id INTEGER REFERENCES hackathons(id) ON DELETE CASCADE,
    code VARCHAR(32) UNIQUE NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'participant',  -- 'participant' or 'judge'
    uses_remaining INTEGER NOT NULL DEFAULT 1,
    expires_at TIMESTAMP,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);
```

- Organizer generates codes in bulk: `POST /api/hackathons/{id}/invites` with `count`, `role`, `expires_days`.
- Codes are random alphanumeric (16 chars), e.g., `OPENHACK-2026-ABC123`.
- Frontend displays codes in a table with copy button, uses remaining, expiry.

---

## 5. Data Migration Strategy

### 5.1 For Existing Deployments (if any)

- `backend/app/clerk_auth.py` is deleted.
- `users.clerk_id` column is deprecated but kept initially for reference. Log warning on startup if any users have `clerk_id` set: "Clerk auth is no longer supported. These users must set a password via forgot-password flow."
- `OAuthAccount` table schema changes: rename `provider` to `provider_name`, add `provider_user_id`, remove `clerk_id` foreign key. Write Alembic migration.
- Frontend: Replace all `useAuth()` Clerk calls with custom hook. Remove `@clerk/clerk-react` dependency from `package.json`.

### 5.2 New Fields on Users Table

```sql
ALTER TABLE users ADD COLUMN password_hash VARCHAR(255);
ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT false;
ALTER TABLE users ADD COLUMN password_reset_token VARCHAR(255);
ALTER TABLE users ADD COLUMN password_reset_expires TIMESTAMP;
```

- `password_hash` is nullable (OAuth-only users don't have one initially).
- On first password login attempt, if `password_hash` is null, return "Please set a password via forgot-password flow."

---

## 6. API Endpoints

### 6.1 Auth Endpoints

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/api/auth/register` | Register new account | Public |
| POST | `/api/auth/login` | Login with password | Public |
| POST | `/api/auth/refresh` | Refresh access token | Refresh cookie |
| POST | `/api/auth/logout` | Logout | Refresh cookie |
| POST | `/api/auth/forgot-password` | Request reset link | Public |
| POST | `/api/auth/reset-password` | Reset password with token | Public |
| GET | `/api/auth/me` | Current user info | Bearer JWT |
| GET | `/api/auth/providers` | List active OAuth providers | Public |
| GET | `/api/auth/oauth/{provider}/login` | Initiate OAuth login | Public |
| GET | `/api/auth/oauth/{provider}/callback` | OAuth callback | Public |

### 6.2 Admin OAuth Endpoints

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/api/admin/oauth/providers` | List provider configs | Organizer |
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

- `LoginForm.tsx` — Email/password + social buttons
- `RegisterForm.tsx` — Email/password/name + invite code (conditional)
- `ForgotPasswordForm.tsx`
- `ResetPasswordForm.tsx`
- `OAuthButton.tsx` — Dynamic social button based on provider
- `OAuthAdminPanel.tsx` — Provider management table + add form
- `InviteCodeManager.tsx` — Generate/list/revoke invites

### 7.2 Modified Pages

- `AuthPage.tsx` — Replace Clerk with custom forms
- `HackathonSettings.tsx` — Add `registration_mode` toggle + invite code manager
- `Dashboard.tsx` — No functional change, just auth hook swap

### 7.3 Deleted

- All Clerk imports (`@clerk/clerk-react`, `clerkAuth`)
- `backend/app/clerk_auth.py`
- `VITE_CLERK_PUBLISHABLE_KEY` env var

---

## 8. Security Considerations

- **Password policy**: Minimum 8 chars, at least one uppercase, one lowercase, one number. Enforced at registration and password change.
- **Rate limiting**: Login attempts limited to 5 per minute per IP. Uses existing `fastapi-limiter` with Redis.
- **Token security**: Access tokens in `Authorization` header. Refresh tokens in httpOnly, SameSite=strict, Secure (in production) cookies.
- **OAuth state param**: Random state stored in short-lived Redis key (5 min TTL) to prevent CSRF.
- **Secret encryption**: OAuth client secrets encrypted with Fernet using `HACKVERIFY_SECRET_KEY`.
- **SQL injection prevention**: All queries via SQLAlchemy ORM (parameterized).
- **XSS prevention**: No user input rendered as raw HTML without sanitization.

---

## 9. Testing Plan

### 9.1 Unit Tests

- Password hashing (bcrypt verify)
- JWT creation and verification (expired, invalid signature, valid)
- OAuth state generation and validation
- Invite code generation (format, uniqueness)
- Rate limiting enforcement

### 9.2 Integration Tests

- Full register → login → access protected endpoint → logout flow
- Password reset flow (token generation, expiry, usage)
- OAuth login simulation (mock GitHub/Google token exchange)
- Invite-only registration (valid code, invalid code, expired code, exhausted uses)
- Admin OAuth provider CRUD

### 9.3 E2E Tests

- Playwright test: register account, login, view dashboard, logout
- Playwright test: login via GitHub OAuth (using a test OAuth app)
- Playwright test: organizer generates invite code, participant uses it to register

---

## 10. Rollout & Backwards Compatibility

- This is a **breaking change** for any existing Clerk-based deployment.
- Recommended approach: create a feature branch, complete all work, then merge with a major version bump and migration guide.
- For new self-hosted users: this is the default and only auth system.

---

## Open Questions

1. Should we keep the Clerk code behind a feature flag for a transition period, or delete it entirely?
2. Should the first-run bootstrap also create a default hackathon, or should that remain a separate manual step?
3. Do we need to support "magic link" (passwordless email login) as an alternative to passwords?
