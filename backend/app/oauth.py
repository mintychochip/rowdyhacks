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
        params["response_mode"] = "query"
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


async def fetch_user_info(provider: str, token_response: dict[str, Any], apple_name: str | None = None) -> dict[str, Any]:
    """Fetch user info from the provider using the access token.
    apple_name: for Apple only — the user's name from the authorization response query param
                (Apple only sends the name on first auth, and only in the callback, not token exchange)
    """
    config = PROVIDER_CONFIGS[provider]

    if provider == "apple":
        from jose import jwt as jose_jwt
        id_token = token_response.get("id_token")
        if not id_token:
            raise ValueError("Apple did not return an id_token")
        decoded = jose_jwt.decode(id_token, options={"verify_signature": False})
        email = decoded.get("email", "")
        # Apple sends the user's name as a JSON string in the `user` query param on first auth only
        name = ""
        if apple_name:
            import json
            try:
                name_obj = json.loads(apple_name)
                first = name_obj.get("name", {}).get("firstName", "")
                last = name_obj.get("name", {}).get("lastName", "")
                name = f"{first} {last}".strip()
            except (json.JSONDecodeError, TypeError):
                pass
        return {"provider_user_id": decoded.get("sub", ""), "email": email, "name": name}

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
