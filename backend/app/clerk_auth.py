"""Clerk JWT authentication utilities.

Minimal Clerk auth implementation using PyJWT + JWKS.
Falls back to unverified decode in development when CLERK_SECRET_KEY is unset.
"""

import base64
import json
import logging
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import User, UserRole

logger = logging.getLogger(__name__)
_CLERK_JWKS_CACHE: dict | None = None
_CLERK_JWKS_CACHE_EXPIRY: datetime | None = None


def is_clerk_token(token: str) -> bool:
    """Heuristic check for Clerk JWT format.

    Behavior:
    1. Reject empty strings or tokens without exactly two dot separators.
    2. Split the token into three parts.
    3. Return True only if all parts are non-empty.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: None.
    Consumers: app.auth.get_current_user_ws, app.clerk_auth.decode_clerk_token, app.clerk_auth.require_clerk_user.
    """
    if not token or token.count(".") != 2:
        return False
    parts = token.split(".")
    return all(len(p) > 0 for p in parts)


def _decode_header(token: str) -> dict:
    """Decode the JWT header without cryptographic verification.

    Behavior:
    1. Split the token and isolate the Base64-encoded header segment.
    2. Apply URL-safe Base64 padding if needed.
    3. Decode the segment and parse it as JSON.

    Raises: ValueError if the header segment is malformed or not valid Base64/JSON.
    Side Effects: None (read-only).
    Dependencies: base64.urlsafe_b64decode, json.loads.
    Consumers: app.clerk_auth.decode_clerk_token.
    """
    header_b64 = token.split(".")[0]
    # Add padding if needed
    padding_needed = 4 - len(header_b64) % 4
    if padding_needed != 4:
        header_b64 += "=" * padding_needed
    header_json = base64.urlsafe_b64decode(header_b64)
    return json.loads(header_json)


def _decode_payload(token: str) -> dict:
    """Decode the JWT payload without cryptographic verification.

    Behavior:
    1. Split the token and isolate the Base64-encoded payload segment.
    2. Apply URL-safe Base64 padding if needed.
    3. Decode the segment and parse it as JSON.

    Raises: ValueError if the payload segment is malformed or not valid Base64/JSON.
    Side Effects: None (read-only).
    Dependencies: base64.urlsafe_b64decode, json.loads.
    Consumers: app.clerk_auth.decode_clerk_token.
    """
    payload_b64 = token.split(".")[1]
    padding_needed = 4 - len(payload_b64) % 4
    if padding_needed != 4:
        payload_b64 += "=" * padding_needed
    payload_json = base64.urlsafe_b64decode(payload_b64)
    return json.loads(payload_json)


async def _fetch_clerk_jwks() -> dict:
    """Fetch Clerk JWKS from the Clerk API with one-hour caching.

    Behavior:
    1. Check the in-memory JWKS cache; return it if still valid.
    2. Build the Clerk JWKS URL and Authorization header.
    3. Perform an async HTTP GET to fetch the JWKS document.
    4. Parse the JSON response and store it in the global cache with a 1-hour expiry.
    5. Return the JWKS dict; on failure return an empty keys list.

    Raises: None (exceptions are caught and logged).
    Side Effects: Mutates the global ``_CLERK_JWKS_CACHE`` and ``_CLERK_JWKS_CACHE_EXPIRY`` variables.
    Dependencies: httpx.AsyncClient, app.config.settings.clerk_secret_key.
    Consumers: app.clerk_auth.decode_clerk_token.
    """
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
            _CLERK_JWKS_CACHE_EXPIRY = datetime.now(UTC) + timedelta(seconds=3600)  # 1 hour cache
            return jwks
    except Exception as e:
        logger.warning(f"Failed to fetch Clerk JWKS: {e}")
        return {"keys": []}


def _get_signing_key(jwks: dict, kid: str) -> dict | None:
    """Find the RSA public key with matching kid from a JWKS document.

    Behavior:
    1. Iterate over the ``keys`` list in the JWKS dict.
    2. Return the first key whose ``kid`` and ``kty`` match the requested kid and ``RSA``.
    3. Return None if no match is found.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: None.
    Consumers: app.clerk_auth.decode_clerk_token.
    """
    for key in jwks.get("keys", []):
        if key.get("kid") == kid and key.get("kty") == "RSA":
            return key
    return None


def _rsa_key_to_pem(key_data: dict) -> str:
    """Convert JWK RSA key data to PEM format.

    Behavior:
    1. Decode the Base64url-encoded RSA modulus (n) and exponent (e).
    2. Reconstruct the RSA public key using PyJWT's RSAAlgorithm.
    3. Export the key as a PEM string and return it.

    Raises: ValueError if the JWK data is malformed or decoding fails.
    Side Effects: None (read-only).
    Dependencies: jwt.algorithms.RSAAlgorithm, base64.urlsafe_b64decode.
    Consumers: app.clerk_auth.decode_clerk_token.
    """
    from jwt.algorithms import RSAAlgorithm

    n = int.from_bytes(base64.urlsafe_b64decode(key_data["n"] + "=="[: (4 - len(key_data["n"]) % 4) % 4]), "big")
    e = int.from_bytes(base64.urlsafe_b64decode(key_data["e"] + "=="[: (4 - len(key_data["e"]) % 4) % 4]), "big")
    return RSAAlgorithm.to_pem(RSAAlgorithm.from_public_numbers(jwt.algorithms.RSAPublicNumbers(n, e))).decode()


async def decode_clerk_token(token: str) -> dict:
    """Decode and cryptographically verify a Clerk JWT.

    Behavior:
    1. Validate the token format using is_clerk_token.
    2. If no Clerk secret is configured, fall back to an unverified payload decode (dev mode).
    3. Decode the JWT header to extract the key ID (kid).
    4. Fetch the Clerk JWKS and locate the matching RSA signing key.
    5. Convert the JWK to PEM format.
    6. Verify the token signature with PyJWT using RS256.
    7. Return the decoded payload dict.

    Raises: ValueError if the token format is invalid, the kid is missing, the signing key cannot be found, the token is expired, or the signature is invalid.
    Side Effects: None (read-only, but may cache JWKS globally).
    Dependencies: app.clerk_auth.is_clerk_token, app.clerk_auth._decode_header, app.clerk_auth._decode_payload, app.clerk_auth._fetch_clerk_jwks, app.clerk_auth._get_signing_key, app.clerk_auth._rsa_key_to_pem, jwt.decode.
    Consumers: app.clerk_auth.require_clerk_user, app.auth.get_current_user_ws.
    """
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
    """Extract the user ID from a Clerk JWT payload.

    Behavior:
    1. Read the ``sub`` claim from the decoded payload dict.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: None.
    Consumers: app.clerk_auth.require_clerk_user, app.clerk_auth.require_clerk_user_with_db.
    """
    return payload.get("sub")


def extract_clerk_user_email(payload: dict) -> str | None:
    """Extract the primary email address from a Clerk JWT payload.

    Behavior:
    1. Check the top-level ``email`` claim.
    2. If absent, inspect nested ``user_data.email_addresses``.
    3. Fall back to scanning common email keys in the payload.
    4. Return the first valid email string found, or None.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: None.
    Consumers: app.clerk_auth.require_clerk_user, app.clerk_auth.require_clerk_user_with_db.
    """
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
    """Fetch user details from the Clerk REST API.

    Behavior:
    1. Return None immediately if no Clerk secret key is configured.
    2. Build the Clerk users endpoint URL and Authorization header.
    3. Perform an async HTTP GET and parse the JSON response.
    4. Extract the primary email address (or the first available email).
    5. Derive the user's display name from first_name + last_name, falling back to email.
    6. Return a normalized dict with email, name, and id.

    Raises: None (exceptions are caught and logged).
    Side Effects: None (read-only HTTP request).
    Dependencies: httpx.AsyncClient, app.config.settings.clerk_secret_key.
    Consumers: app.clerk_auth.require_clerk_user_with_db.
    """
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
    """FastAPI dependency: validate Clerk token and return a user payload dict.

    Behavior:
    1. Validate that the Authorization header is present and starts with ``Bearer``.
    2. Check the token format with is_clerk_token.
    3. Decode and verify the JWT with decode_clerk_token.
    4. Extract the user ID (sub) and email from the payload.
    5. Return a dict with ``sub``, ``email``, and the full ``payload``.

    Raises: HTTPException(401) if the header is missing, the token format is invalid, verification fails, or the user ID is absent.
    Side Effects: None (read-only, but may trigger JWKS fetch).
    Dependencies: app.clerk_auth.is_clerk_token, app.clerk_auth.decode_clerk_token, app.clerk_auth.extract_clerk_user_id, app.clerk_auth.extract_clerk_user_email.
    Consumers: FastAPI Depends() across all protected routes; also used by require_clerk_user_with_db.
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
    """FastAPI dependency: validate Clerk token and ensure a matching local DB user exists.

    Behavior:
    1. Delegate to require_clerk_user to extract the Clerk payload.
    2. Query the local User table by the Clerk subject ID.
    3. If the user exists, return the existing record.
    4. If the user does not exist, fetch details from the Clerk API (if needed) to obtain an email.
    5. Auto-create a new User row with a derived name and participant role.
    6. Commit the transaction and refresh the ORM instance.
    7. Return a dict with the User object, sub, email, and payload.

    Raises: HTTPException(401) if the token is invalid; propagates DB errors.
    Side Effects: Inserts a new User row when auto-creating.
    Dependencies: app.clerk_auth.require_clerk_user, app.clerk_auth.fetch_clerk_user_details, app.database.get_db, app.models.User, app.models.UserRole.
    Consumers: FastAPI Depends() across routes that need the full User ORM object.
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
    """FastAPI dependency: validate Clerk token and enforce organizer role.

    Behavior:
    1. Delegate to require_clerk_user_with_db to validate the token and load the User row.
    2. Inspect the user's role.
    3. Raise 403 if the role is not organizer.
    4. Return the auth dict unchanged.

    Raises: HTTPException(401) if the token is invalid; HTTPException(403) if the user is not an organizer.
    Side Effects: None (read-only, but may auto-create the user via require_clerk_user_with_db).
    Dependencies: app.clerk_auth.require_clerk_user_with_db, app.models.UserRole.
    Consumers: FastAPI Depends() on organizer-only routes (e.g., judging config, admin panels).
    """
    auth = await require_clerk_user_with_db(authorization, db)
    user = auth["user"]
    if user.role != UserRole.organizer:
        raise HTTPException(status_code=403, detail="Organizer access required")
    return auth


async def require_hackathon_organizer(
    hackathon_id: uuid.UUID,
    authorization: str | None = Header(alias="Authorization", default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """FastAPI dependency: validate Clerk token and require organizer role for a specific hackathon.

    Behavior:
    1. Delegate to require_clerk_user_with_db to validate the token and load the User row.
    2. Check if the user is the primary organizer of the hackathon.
    3. Check if the user is a co-organizer of the hackathon.
    4. Raise 403 if neither condition is met.
    5. Return the auth dict unchanged.

    Raises: HTTPException(401) if the token is invalid; HTTPException(403) if the user is not an organizer for this hackathon.
    Side Effects: None (read-only, but may auto-create the user via require_clerk_user_with_db).
    Dependencies: app.clerk_auth.require_clerk_user_with_db, app.models.Hackathon, app.models.HackathonOrganizer.
    Consumers: FastAPI Depends() on hackathon-scoped organizer routes.
    """
    auth = await require_clerk_user_with_db(authorization, db)
    user = auth["user"]

    from app.models import Hackathon, HackathonOrganizer

    # Primary organizer check
    result = await db.execute(
        select(Hackathon).where(and_(Hackathon.id == hackathon_id, Hackathon.organizer_id == user.id))
    )
    if result.scalar_one_or_none():
        return auth

    # Co-organizer check
    co_result = await db.execute(
        select(HackathonOrganizer).where(
            and_(
                HackathonOrganizer.hackathon_id == hackathon_id,
                HackathonOrganizer.user_id == user.id,
            )
        )
    )
    if co_result.scalar_one_or_none():
        return auth

    raise HTTPException(status_code=403, detail="Only the hackathon organizer can perform this action")
