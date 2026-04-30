# OAuth Social Login with Account Linking

## Summary

Add Google, GitHub, Discord, and Apple OAuth to the existing email/password auth system. Users can sign in via any provider, and authenticated users can link multiple providers to a single account.

## Data Model

### OAuthAccount (new table)
| Column | Type | Notes |
|--------|------|-------|
| id | Guid (UUID) | PK |
| provider | String(20) | `google`, `github`, `discord`, `apple` |
| provider_user_id | String(255) | ID from the provider |
| provider_email | String(320) | Email from the provider (nullable) |
| user_id | Guid (FK → users.id) | Owning user |
| created_at | DateTime(tz) | |

- Unique composite index on `(provider, provider_user_id)`
- A user can have multiple OAuthAccount rows (one per provider)

### User (changes)
- `password_hash` becomes nullable — OAuth-only users won't have a password

## Backend

### New dependencies
- `httpx` or `aiohttp` for provider API calls
- No OAuth library needed — the flow is simple enough to implement directly

### Config (Settings)
Add per-provider client ID and secret fields:
- `google_client_id`, `google_client_secret`
- `github_client_id`, `github_client_secret`
- `discord_client_id`, `discord_client_secret`
- `apple_client_id`, `apple_client_secret`, `apple_team_id`, `apple_key_id`, `apple_private_key_path` (Apple uses a private key JWT flow, more complex than the others)

### Routes

`GET /api/auth/oauth/{provider}/authorize`
- Builds the provider's OAuth authorization URL with redirect_uri, client_id, scope, state
- Redirects the browser to the provider

`GET /api/auth/oauth/{provider}/callback`
- Receives `code` and `state`
- Exchanges code for access token (POST to provider's token endpoint)
- Fetches user info (email, name, provider user ID) from provider's user endpoint
- Login-or-create logic:
  1. Find OAuthAccount by `(provider, provider_user_id)` → if found, login as linked user
  2. If not found, check if User.email matches OAuth email → auto-link (add OAuthAccount row)
  3. If no match → create new User + OAuthAccount, login
- All paths issue a JWT and redirect to frontend callback URL with `?token=<jwt>`

`POST /api/auth/me/oauth/{provider}/link` (auth required)
- Same as authorize but marks the state as "linking" mode
- On callback: adds OAuthAccount to the authenticated user's account
- Errors if the OAuth account is already linked to another user

`DELETE /api/auth/me/oauth/{provider}/unlink` (auth required)
- Removes the OAuthAccount row
- Fails (400) if this would leave the user with no auth methods (no password and no other OAuth accounts)

`GET /api/auth/me/oauth` (auth required)
- Returns list of linked providers for the current user

### OAuth Provider Details

**Google**
- Token endpoint: `https://oauth2.googleapis.com/token`
- User info: `https://www.googleapis.com/oauth2/v2/userinfo`
- Scopes: `openid profile email`

**GitHub**
- Token endpoint: `https://github.com/login/oauth/access_token`
- User info: `https://api.github.com/user`
- Emails: `https://api.github.com/user/emails` (primary verified)
- Scopes: `user:email`

**Discord**
- Token endpoint: `https://discord.com/api/oauth2/token`
- User info: `https://discord.com/api/users/@me`
- Scopes: `identify email`

**Apple**
- Uses Sign in with Apple's token endpoint and a client secret signed with a private key (JWT)
- Token endpoint: `https://appleid.apple.com/auth/token`
- ID token contains user info (name only on first auth, email in claims)
- Scopes: `name email`

### Redirect URI pattern
- `{base_url}/api/auth/oauth/{provider}/callback`

## Frontend

### AuthPage changes
- Add social login buttons below the email/password form with a "or" divider
- Each button links to `/api/auth/oauth/{provider}/authorize`
- Style: full-width outlined buttons with provider icon + "Sign in with X"

### OAuth callback handling
- Backend redirects to frontend at `/#/auth/callback?token=<jwt>`
- A small AuthCallback component reads the token, stores it (same as current login flow), and navigates to `/`
- Route: `/auth/callback` renders AuthCallback

### Linked Accounts UI
- Accessible from user dropdown or settings page
- Shows each provider with a "Connected" / "Not connected" status
- "Connect" button initiates link flow
- "Disconnect" button removes link (disabled if last remaining auth method)

### API service additions
- `getOAuthAuthorizeUrl(provider)` — returns the backend authorize URL
- `getLinkedAccounts()` — `GET /api/auth/me/oauth`
- `linkProvider(provider)` — `POST /api/auth/me/oauth/{provider}/link`
- `unlinkProvider(provider)` — `DELETE /api/auth/me/oauth/{provider}/unlink`

## Error Handling

- OAuth callback failures (bad code, expired state) → redirect to frontend with `?error=<message>`, AuthPage shows toast
- Account already linked to another user (link conflict) → toast explaining the issue
- Unlink last auth method → toast explaining user must set a password first
- Email mismatch between provider and linked account → logged and accepted (provider email may change)

## Testing

- Unit tests for the login-or-create and link/unlink logic
- Mock provider HTTP responses
- Frontend: test that social buttons render and link to correct URLs
- Frontend: test callback component handles token and error params
