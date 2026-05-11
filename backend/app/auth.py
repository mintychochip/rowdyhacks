"""Auth utilities - internal JWTs for QR codes and anonymous tokens only.
Clerk handles all user authentication.
"""

import uuid
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

from app.config import settings

ALGORITHM = "HS256"


def create_anonymous_token() -> str:
    """Create an anonymous access token (UUID) for self-check result retrieval."""
    return str(uuid.uuid4())


def create_qr_token(registration_id: str, user_id: str, hackathon_id: str, hackathon_end: datetime) -> str:
    """Create a signed JWT for embedding in a QR code."""
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
    """Decode and validate an internal JWT token (QR tokens only)."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}") from e


def decode_qr_token(token: str) -> dict:
    """Decode and validate a QR token JWT. Raises ValueError if invalid/expired."""
    return decode_token(token)


async def get_current_user_ws(token: str | None) -> dict | None:
    """Validate JWT token for WebSocket connections.

    Tries Clerk tokens first, then falls back to internal JWTs (QR tokens).
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
