# Auth0 Migration Design

**Date**: 2026-05-04
**Scope**: Migrate from custom JWT/OAuth to Auth0 for authentication

## Current State

### Backend
- Custom JWT tokens (HS256, 24h expiry) signed with `secret_key`
- bcrypt password hashing for email/password users
- OAuth integrations for Google, GitHub, Discord (custom code)
- `User` model: id, email, name, role, password_hash, created_at
- `OAuthAccount` model: id, provider, provider_user_id, provider_email, user_id

### Frontend
- `AuthContext` manages token in localStorage
- Custom login/register forms with email/password
- OAuth buttons redirect through backend
- Token sent as `Authorization: Bearer <token>` header

## Target State

### Auth0 Configuration
- **Tenant**: Single Auth0 tenant for the application
- **Applications**: One Auth0 Application (SPA + API)
- **Connections**:
  - Database (email/password)
  - Google (social)
  - GitHub (social)
  - Discord (social, if Auth0 supports - otherwise we add as custom)
- **User Migration**: Import existing users via Auth0 Management API

### Data Model Changes

#### User Table (Modified)
```sql
-- Keep locally for relationships and app-specific data
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth0_id VARCHAR(255) UNIQUE NOT NULL,  -- NEW: Auth0 sub claim
    email VARCHAR(320) NOT NULL,
    name VARCHAR(200) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'participant',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- REMOVED: password_hash (now in Auth0)
);

-- DROP TABLE oauth_accounts; -- REMOVED: Auth0 handles this
```

#### Migration Strategy
1. Export existing users to Auth0 via Management API
2. Export existing OAuthAccount links as Auth0 identities
3. Run database migration to add `auth0_id` column
4. Populate `auth0_id` by matching email
5. Remove `password_hash` and `oauth_accounts` table

### API Changes

#### Authentication Middleware (New)
```python
# Validate Auth0 JWT instead of custom JWT
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    # Validate with Auth0 JWKS
    # Extract 'sub' claim (Auth0 user ID)
    # Lookup user in local DB by auth0_id
    # Return user with role
```

#### Removed Routes
- `POST /auth/login` (email/password)
- `POST /auth/register` (email/password)
- `GET /auth/oauth/{provider}/authorize`
- `GET /auth/oauth/{provider}/callback`
- `DELETE /auth/me/oauth/{provider}` (unlinking)
- `GET /auth/me/oauth` (list linked providers)
- `GET /auth/me/oauth/link/{provider}`

#### Modified Routes
- `GET /auth/me` - Now validates Auth0 token, returns local user data

### Frontend Changes

#### New Dependencies
```bash
npm install @auth0/auth0-react
```

#### Auth0 Configuration
```typescript
// auth0-config.ts
export const auth0Config = {
  domain: 'hackthevalley.us.auth0.com',  // or your domain
  clientId: 'your-client-id',
  authorizationParams: {
    redirect_uri: window.location.origin + '/auth/callback',
    audience: 'https://api.hackthevalley.io',  // API identifier
  },
};
```

#### AuthContext Replacement
- Replace custom `AuthContext` with `Auth0Provider`
- Use `useAuth0()` hook for login/logout/user info
- Access token from `getAccessTokenSilently()` for API calls

#### UI Changes
- Remove email/password form from AuthPage
- Replace OAuth buttons with single "Login with Auth0" button
- Auth0 handles provider selection in its Universal Login page
- Or keep provider-specific buttons that use Auth0's connection param

### Backend Dependencies

```bash
pip install pyjwt[crypto]  # For RS256 JWT validation
# Remove: python-jose, bcrypt (no longer needed for auth)
```

## Implementation Phases

### Phase 1: Setup (No code changes)
1. Create Auth0 tenant and application
2. Configure Google/GitHub/Discord connections in Auth0
3. Configure API identifier and permissions
4. Document Auth0 credentials for deployment

### Phase 2: Backend Migration
1. Add `auth0_id` column to users table
2. Create Auth0 JWT validation middleware
3. Update `get_current_user` dependency
4. Remove OAuth callback routes
5. Remove password-based auth routes
6. Keep `/auth/me` but use Auth0 token
7. Test with Auth0 test users

### Phase 3: Frontend Migration
1. Install `@auth0/auth0-react`
2. Add Auth0Provider to App.tsx
3. Replace AuthContext with Auth0 hooks
4. Update AuthPage to use Auth0 login
5. Update API service to get Auth0 access token
6. Update all API calls to include Auth0 token

### Phase 4: User Migration
1. Write script to export users to Auth0
2. Migrate passwords: trigger password reset emails for existing users
3. Run migration on production database
4. Backfill `auth0_id` for all users

### Phase 5: Cleanup
1. Remove `password_hash` column
2. Drop `oauth_accounts` table
3. Remove custom JWT code (auth.py)
4. Remove OAuth code (oauth.py)
5. Update documentation

## Configuration

### Environment Variables
```bash
# Auth0 (new)
AUTH0_DOMAIN=hackthevalley.us.auth0.com
AUTH0_CLIENT_ID=xxx
AUTH0_CLIENT_SECRET=xxx
AUTH0_API_AUDIENCE=https://api.hackthevalley.io

# Remove (old)
# HACKVERIFY_SECRET_KEY=xxx  # No longer needed for auth
# HACKVERIFY_GOOGLE_CLIENT_ID=xxx  # Now in Auth0
# etc.
```

## Rollback Plan

1. Keep old JWT middleware commented out, not deleted
2. Keep `password_hash` column until migration is verified
3. Test Auth0 in staging environment first
4. If issues occur: revert frontend to previous commit, disable Auth0 routes

## Security Considerations

1. **Token Validation**: Always validate Auth0 JWT signature using JWKS endpoint
2. **Role Enforcement**: Double-check role from local DB, don't trust token alone
3. **User Creation**: Only create local user records after Auth0 validation
4. **Migration**: Password reset emails ensure users control their migrated accounts

## Testing Checklist

- [ ] New user can sign up via Auth0
- [ ] Existing user can log in after migration
- [ ] OAuth login (Google, GitHub, Discord) works
- [ ] Token refresh works silently
- [ ] Logout clears session
- [ ] Protected routes require valid token
- [ ] Role-based access control still works
- [ ] User data syncs correctly from Auth0
