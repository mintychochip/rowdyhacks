"""Clerk JWT authentication utilities.

Minimal Clerk auth implementation using PyJWT + JWKS.
Falls back to unverified decode in development when CLERK_SECRET_KEY is unset.
"""

import base64
import json
import logging
from datetime import UTC, datetime

import httpx
import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import User, UserRole

logger = logging.getLogger(__name__)
_CLERK_JWKS_CACHE: dict | None = None
_CLERK_JWKS_CACHE_EXPIRY: datetime | None = None


def is_clerk_token(token: str) -> bool:
    """Heuristic: Clerk tokens are standard JWTs (three dot-separated base64 parts)."""
    if not token or token.count(".") != 2:
        return False
    parts = token.split(".")
    return all(len(p) > 0 for p in parts)


def _decode_header(token: str) -> dict:
    """Decode the JWT header without verification."""
    header_b64 = token.split(".")[0]
    # Add padding if needed
    padding_needed = 4 - len(header_b64) % 4
    if padding_needed != 4:
        header_b64 += "=" * padding_needed
    header_json = base64.urlsafe_b64decode(header_b64)
    return json.loads(header_json)


def _decode_payload(token: str) -> dict:
    """Decode the JWT payload without verification."""
    payload_b64 = token.split(".")[1]
    padding_needed = 4 - len(payload_b64) % 4
    if padding_needed != 4:
        payload_b64 += "=" * padding_needed
    payload_json = base64.urlsafe_b64decode(payload_b64)
    return json.loads(payload_json)


async def _fetch_clerk_jwks() -> dict:
    """Fetch Clerk JWKS. Caches for 1 hour."""
    global _CLERK_JWKS_CACHE, _CLERK_JWKS_CACHE_EXPIRY

    if _CLERK_JWKS_CACHE and _CLERK_JWKS_CACHE_EXPIRY and datetime.now(UTC) < _CLERK_JWKS_CACHE_EXPIRY:
        return _CLERK_JWKS_CACHE

    # Derive JWKS URL from secret key if possible, otherwise use default Clerk API
    if settings.clerk_secret_key.startswith("sk_test") or settings.clerk_secret_key:
        url = "https://api.clerk.com/v1/jwks"
    else:
        url = "https://api.clerk.com/v1/jwks"

    headers = {}
    if settings.clerk_secret_key:
        headers["Authorization"] = f"Bearer {settings.clerk_secret_key}"

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, timeout=10.0)
            resp.raise_for_status()
            jwks = resp.json()
            _CLERK_JWKS_CACHE = jwks
            _CLERK_JWKS_CACHE_EXPIRY = datetime.now(UTC) + 3600  # 1 hour cache
            return jwks
    except Exception as e:
        logger.warning(f"Failed to fetch Clerk JWKS: {e}")
        return {"keys": []}


def _get_signing_key(jwks: dict, kid: str) -> dict | None:
    """Find the RSA public key with matching kid from JWKS."""
    for key in jwks.get("keys", []):
        if key.get("kid") == kid and key.get("kty") == "RSA":
            return key
    return None


def _rsa_key_to_pem(key_data: dict) -> str:
    """Convert JWK RSA key data to PEM format."""
    from jwt.algorithms import RSAAlgorithm

    n = int.from_bytes(base64.urlsafe_b64decode(key_data["n"] + "=="[: (4 - len(key_data["n"]) % 4) % 4]), "big")
    e = int.from_bytes(base64.urlsafe_b64decode(key_data["e"] + "=="[: (4 - len(key_data["e"]) % 4) % 4]), "big")
    return RSAAlgorithm.to_pem(RSAAlgorithm.from_public_numbers(jwt.algorithms.RSAPublicNumbers(n, e))).decode()


async def decode_clerk_token(token: str) -> dict:
    """Decode and verify a Clerk JWT. Raises ValueError if invalid."""
    if not is_clerk_token(token):
        raise ValueError("Invalid token format")

    # If no Clerk secret configured, do unverified decode (dev fallback)
    if not settings.clerk_secret_key:
        logger.debug("No CLERK_SECRET_KEY set; decoding Clerk token without verification")
        try:
            return _decode_payload(token)
        except Exception as e:
            raise ValueError(f"Failed to decode token: {e}") from e

    header = _decode_header(token)
    kid = header.get("kid")
    if not kid:
        raise ValueError("Token header missing 'kid'")

    jwks = await _fetch_clerk_jwks()
    key_data = _get_signing_key(jwks, kid)
    if not key_data:
        raise ValueError(f"No matching signing key found for kid={kid}")

    try:
        pem = _rsa_key_to_pem(key_data)
        payload = jwt.decode(token, pem, algorithms=["RS256"], options={"verify_aud": False})
        return payload
    except jwt.ExpiredSignatureError as e:
        raise ValueError("Token has expired") from e
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid token: {e}") from e


def extract_clerk_user_id(payload: dict) -> str | None:
    """Extract user ID (sub) from Clerk token payload."""
    return payload.get("sub")


def extract_clerk_user_email(payload: dict) -> str | None:
    """Extract primary email from Clerk token payload."""
    # Clerk puts email in email claim or nested in user data
    email = payload.get("email")
    if email:
        return email
    # Try primary email from user_data if present
    user_data = payload.get("user_data", {})
    if isinstance(user_data, dict):
        emails = user_data.get("email_addresses", [])
        if emails:
            return emails[0].get("email_address")
    # Fallback: look in payload directly
    for key in ("email_address", "mail", "primary_email_address_id"):
        if key in payload:
            val = payload[key]
            if isinstance(val, str) and "@" in val:
                return val
    return None


async def fetch_clerk_user_details(user_id: str) -> dict | None:
    """Fetch user details from Clerk API. Returns dict with email, name, etc."""
    if not settings.clerk_secret_key:
        return None

    url = f"https://api.clerk.com/v1/users/{user_id}"
    headers = {"Authorization": f"Bearer {settings.clerk_secret_key}"}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
            email_addresses = data.get("email_addresses", [])
            primary_email_id = data.get("primary_email_address_id")
            email = None
            for ea in email_addresses:
                if ea.get("id") == primary_email_id:
                    email = ea.get("email_address")
                    break
            if not email and email_addresses:
                email = email_addresses[0].get("email_address")

            first_name = data.get("first_name", "")
            last_name = data.get("last_name", "")
            name = f"{first_name} {last_name}".strip() or email

            return {"email": email, "name": name, "id": user_id}
    except Exception as e:
        logger.warning(f"Failed to fetch Clerk user details: {e}")
        return None


async def require_clerk_user(
    authorization: str | None = Header(alias="Authorization", default=None),
) -> dict:
    """FastAPI dependency: validate Clerk token and return user payload dict.

    Returns dict with at minimum 'sub' (user id) and optionally 'email'.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.removeprefix("Bearer ")

    if not is_clerk_token(token):
        raise HTTPException(status_code=401, detail="Invalid token format")

    try:
        payload = await decode_clerk_token(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}") from e

    user_id = extract_clerk_user_id(payload)
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing user ID")

    return {
        "sub": user_id,
        "email": extract_clerk_user_email(payload),
        "payload": payload,
    }


async def require_clerk_user_with_db(
    authorization: str | None = Header(alias="Authorization", default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """FastAPI dependency: validate Clerk token, look up or auto-create DB user.

    Returns dict with 'user' (User ORM object), 'sub', 'email', 'payload'.
    """
    user_payload = await require_clerk_user(authorization)
    user_id = user_payload["sub"]
    email = user_payload.get("email")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        # Auto-create user (same logic as auth.py /me)
        if not email:
            clerk_user = await fetch_clerk_user_details(user_id)
            if clerk_user:
                email = clerk_user.get("email")
        name = email.split("@")[0] if email else "Unknown"
        user = User(id=user_id, email=email or f"{user_id}@unknown", name=name, role=UserRole.participant)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return {
        "user": user,
        "sub": user_id,
        "email": email,
        "payload": user_payload["payload"],
    }


async def require_organizer(
    authorization: str | None = Header(alias="Authorization", default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """FastAPI dependency: validate Clerk token and require organizer role.

    Returns the same dict as require_clerk_user_with_db.
    """
    auth = await require_clerk_user_with_db(authorization, db)
    user = auth["user"]
    if user.role != UserRole.organizer:
        raise HTTPException(status_code=403, detail="Organizer access required")
    return auth
