"""Auth utilities for internal JWTs used by QR codes and anonymous tokens.

Clerk handles all user authentication; this module only provides
legacy/token helpers that do not depend on Clerk.
"""

import uuid
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

from app.config import settings

ALGORITHM = "HS256"


def create_anonymous_token() -> str:
    """Create an anonymous access token (UUID) for self-check result retrieval.

    Behavior:
    1. Generate a new UUID4 string.
    2. Return it as the anonymous access token.

    Raises: None
    Side Effects: None (read-only, no state mutation).
    Dependencies: uuid.uuid4.
    Consumers: Internal helper used by submission checks.
    """
    return str(uuid.uuid4())


def create_qr_token(registration_id: str, user_id: str, hackathon_id: str, hackathon_end: datetime) -> str:
    """Create a signed JWT for embedding in a QR code.

    Behavior:
    1. Build a JWT payload with registration ID, user ID, hackathon ID, and issued-at time.
    2. Set expiration to 24 hours after the hackathon end date.
    3. Encode the payload with HS256 using the configured secret key.

    Raises: None
    Side Effects: None (read-only, no state mutation).
    Dependencies: jose.jwt.encode, app.config.settings.secret_key.
    Consumers: Internal helper used by check-in and registration routes.
    """
    now = datetime.now(UTC)
    payload = {
        "reg_id": registration_id,
        "user_id": user_id,
        "hackathon_id": hackathon_id,
        "iat": now,
        "exp": hackathon_end + timedelta(hours=24),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate an internal JWT token (QR tokens only).

    Behavior:
    1. Attempt to decode the token with HS256 using the configured secret key.
    2. Return the decoded payload dict.
    3. On JWTError, re-raise as ValueError with the original error chained.

    Raises: ValueError if the token is invalid or cannot be decoded.
    Side Effects: None (read-only).
    Dependencies: jose.jwt.decode, app.config.settings.secret_key.
    Consumers: decode_qr_token, get_current_user_ws.
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}") from e


def decode_qr_token(token: str) -> dict:
    """Decode and validate a QR token JWT.

    Behavior:
    1. Delegate to decode_token to verify the JWT signature and expiry.
    2. Return the decoded payload dict.

    Raises: ValueError if the token is invalid or expired.
    Side Effects: None (read-only).
    Dependencies: decode_token.
    Consumers: WebSocket authentication routes.
    """
    return decode_token(token)


async def get_current_user_ws(token: str | None) -> dict | None:
    """Validate JWT token for WebSocket connections.

    Behavior:
    1. Return None if no token is provided.
    2. Try Clerk tokens first: decode the Clerk JWT, extract the user ID, and return a participant dict.
    3. If Clerk validation fails or the user ID is missing, return None.
    4. Fall back to internal JWT (QR tokens): decode with decode_token, extract the user ID or sub claim, and return the role dict.
    5. On any fallback exception, return None.

    Raises: None (all errors are swallowed and return None).
    Side Effects: None (read-only).
    Dependencies: app.clerk_auth.is_clerk_token, decode_clerk_token, extract_clerk_user_id, decode_token.
    Consumers: WebSocket connection manager.
    """
    if not token:
        return None

    # Try Clerk token first
    from app.clerk_auth import is_clerk_token, decode_clerk_token, extract_clerk_user_id

    if is_clerk_token(token):
        try:
            payload = await decode_clerk_token(token)
            user_id = extract_clerk_user_id(payload)
            if user_id:
                return {"id": user_id, "role": "participant"}
        except Exception:
            pass
        return None

    # Fall back to internal JWT (QR tokens)
    try:
        payload = decode_token(token)
        return {
            "id": payload.get("sub") or payload.get("user_id"),
            "role": payload.get("role"),
        }
    except Exception:
        return None
