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
| provider_email | String(320) | Email from the provider (nullable — Apple may hide email via private relay) |
| user_id | Guid (FK → users.id) | Owning user |
| created_at | DateTime(tz) | |

- Unique composite index on `(provider, provider_user_id)`
- A user can have multiple OAuthAccount rows (one per provider)

### User (changes)
- `password_hash` becomes nullable — OAuth-only users won't have a password
- `User.name` default when created via OAuth: use the name from the provider response. For Apple on subsequent auths where name is absent, fall back to the email local part (e.g., `justin` from `justin@example.com`) or "Hacker" as a last-resort placeholder.

## Backend

### New dependencies
- `httpx` — async HTTP client for provider API calls
- Optional: `authlib` to simplify Apple's private key JWT client assertion. The spec does not require it, but implementers should evaluate it for the Apple provider specifically.

### Config (Settings)
Add per-provider client ID and secret fields:
- `google_client_id`, `google_client_secret`
- `github_client_id`, `github_client_secret`
- `discord_client_id`, `discord_client_secret`
- `apple_client_id`, `apple_client_secret`, `apple_team_id`, `apple_key_id`, `apple_private_key_path`

### OAuth State Management (CSRF Protection)

The `state` parameter prevents CSRF attacks on the OAuth flow.

- On `authorize`: generate a cryptographically random nonce (32 bytes, hex-encoded). Store it server-side keyed by the nonce, with a payload containing the provider name and an optional `link_user_id` (set when the user is linking a provider to an existing account). TTL: 10 minutes.
- Storage: in-memory cache (e.g., a dict with expiration) or the database. In-memory is acceptable for a single-instance deploy; use the database if multi-instance is expected.
- On `callback`: look up the received `state` in the store. If missing or expired, redirect to frontend with `error=invalid_state`. If valid, consume it (delete from store) and proceed.
- The state nonce is NOT embedded in the JWT or sent to the client beyond the OAuth redirect URL.

### Routes

`GET /api/auth/oauth/{provider}/authorize`
- Generates state nonce, stores it with TTL, builds the provider's OAuth authorization URL
- Redirects the browser to the provider

`GET /api/auth/oauth/{provider}/callback`
- Receives `code` and `state`
- Validates state (missing/expired → redirect with `error=invalid_state`)
- Exchanges code for access token via httpx POST to provider's token endpoint
- Fetches user info (email, name, provider user ID) from provider's user endpoint
- Login-or-create logic:
  1. Find OAuthAccount by `(provider, provider_user_id)` → if found, login as linked user
  2. If not found and the OAuth response includes a verified email, check if any `User.email` matches it → if so, auto-link (add OAuthAccount row) and log in as that user. Email auto-link is intentional: if someone controls a verified OAuth email, they effectively own that identity. No additional confirmation prompt is needed.
  3. If no match → create new User (with the email from the provider, name from the provider with fallback as described above, null password_hash) + OAuthAccount, login
- All paths issue a JWT and redirect to the frontend callback URL:
  - Success: `{frontend_origin}/#/auth/callback?token={jwt}` (the `?token=` lives inside the hash fragment since the app uses hash routing)
  - Error: `{frontend_origin}/#/auth/callback?error={message}`

`POST /api/auth/me/oauth/{provider}/link` (auth required)
- Redirects to provider's OAuth authorize URL with state nonce carrying `link_user_id=<current user's id>`
- On callback: adds OAuthAccount to the authenticated user's account
- Errors (409) if the OAuth account is already linked to another user

`DELETE /api/auth/me/oauth/{provider}/unlink` (auth required)
- Removes the OAuthAccount row
- Fails (400) if this would leave the user with no auth methods (no password and no other OAuth accounts)

`GET /api/auth/me/oauth` (auth required)
- Returns list of linked providers for the current user, e.g. `{"linked": ["google", "github"], "has_password": true}`

### OAuth Provider Details

**Google**
- Token endpoint: `https://oauth2.googleapis.com/token`
- User info: `https://www.googleapis.com/oauth2/v2/userinfo`
- Scopes: `openid profile email`

**GitHub**
- Token endpoint: `https://github.com/login/oauth/access_token`
- User info: `https://api.github.com/user`
- Emails: `https://api.github.com/user/emails` (use the primary verified email)
- Scopes: `user:email`

**Discord**
- Token endpoint: `https://discord.com/api/oauth2/token`
- User info: `https://discord.com/api/users/@me`
- Scopes: `identify email`

**Apple**
- Token endpoint: `https://appleid.apple.com/auth/token`
- ID token contains user info. The `name` claim is only present on the **very first** authentication for a given app; on subsequent auths the name fields are absent. Use the email local part or "Hacker" as a fallback for the user name.
- Apple may return a private relay email (`@privaterelay.appleid.com`). This is still a valid, deliverable email — use it as `User.email`.
- Client assertion: a JWT signed with the Apple private key, per Apple's documentation. Use `authlib` or implement directly with `python-jose` (already a dependency).
- Scopes: `name email`

### Redirect URI pattern
- `{base_url}/api/auth/oauth/{provider}/callback`
- Each provider's developer console must be configured with these exact redirect URIs before the flow works.

### Operational Checklist
Before the feature works end-to-end, the following must be done per provider:
1. Register the application in each provider's developer console
2. Configure allowed redirect URIs
3. Obtain client ID and secret
4. Add them to `.env` / deployment config
5. For Apple: generate a private key in the Apple Developer portal and download the `.p8` file

## Frontend

### AuthPage changes
- Add social login buttons below the email/password form with an "or" divider
- Each button is an `<a>` link to `{API_BASE}/auth/oauth/{provider}/authorize` (a full page navigation, not a fetch)
- Style: full-width outlined buttons with provider icon + "Sign in with X"

### OAuth callback handling (`/auth/callback` route)
- Renders an `AuthCallback` component
- This component reads `token` and `error` from the URL hash fragment's query string (e.g., `/#/auth/callback?token=jwt123` → parse `token=jwt123` from `location.hash`)
- If `token` is present: store it in localStorage (same as current login), fetch `/api/auth/me` to populate user state, navigate to `/`
- If `error` is present: navigate to `/auth?error=<message>` so AuthPage shows a toast
- Shows a loading spinner while processing

### Linked Accounts UI
- Accessible from user dropdown or settings page
- Shows each provider with a "Connected" / "Not connected" status
- "Connect" button initiates link flow (navigates to `/api/auth/me/oauth/{provider}/link`)
- "Disconnect" button removes link, disabled with tooltip if it's the user's last auth method and they have no password

### API service additions
- `getOAuthAuthorizeUrl(provider)` — returns `{API_BASE}/auth/oauth/{provider}/authorize`
- `getLinkedAccounts()` — `GET /api/auth/me/oauth`
- `linkProvider(provider)` — `POST /api/auth/me/oauth/{provider}/link`
- `unlinkProvider(provider)` — `DELETE /api/auth/me/oauth/{provider}/unlink`

## Error Handling

- **Expired/missing state** → redirect to `/#/auth/callback?error=invalid_state`, AuthPage shows toast "Login session expired. Please try again."
- **Provider returns error** (e.g., user denied consent) → redirect to `/#/auth/callback?error=oauth_denied`
- **Account already linked** (link conflict, 409) → toast "This account is already connected to another user."
- **Unlink last auth method** (400) → toast "Set a password before disconnecting your only login method."
- **Provider unreachable** (httpx timeout/error) → redirect to `/#/auth/callback?error=provider_error`
- **Provider returns no email** → treat as error, redirect with `error=no_email`
- **Race condition on concurrent link** → unique constraint on `(provider, provider_user_id)` catches this at the DB layer; return 409

## Testing

### Backend Unit Tests
- `authorize` creates state nonce and redirects to correct provider URL
- `callback` with valid state + new user → creates User + OAuthAccount, returns JWT redirect
- `callback` with valid state + existing OAuthAccount → logs in as existing user
- `callback` with valid state + matching email → auto-links to existing user
- `callback` with expired/missing state → redirects with `error=invalid_state`
- `callback` with bad provider code → redirects with `error=provider_error`
- `callback` when provider returns no email → redirects with `error=no_email`
- `callback` for Apple subsequent auth (no name in response) → creates user with name fallback
- `link` endpoint creates OAuthAccount for authenticated user
- `link` endpoint returns 409 when OAuthAccount already linked to another user
- `unlink` endpoint removes OAuthAccount
- `unlink` endpoint returns 400 when it would strand the user (no password, no other OAuth)
- Concurrent link attempts → unique constraint prevents duplicates

### Frontend Tests
- AuthPage renders social login buttons for all four providers
- Each button links to the correct authorize URL
- AuthCallback parses token from hash fragment, stores it, navigates to `/`
- AuthCallback parses error from hash fragment, navigates to `/auth?error=...`
- Linked Accounts UI shows correct connected/disconnected state per provider
- Disconnect button is disabled with tooltip when it's the user's only auth method

## Rate Limiting

Rate limiting on OAuth callback endpoints is deferred to a separate security hardening pass. The state store's 10-minute TTL already limits replay attacks. If needed, add a simple per-IP rate limiter on the callback route.
