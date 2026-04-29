import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(
    user_id: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token with user_id (sub) and role."""
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token, returning the payload."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}") from e


def create_anonymous_token() -> str:
    """Create an anonymous access token (UUID) for self-check result retrieval."""
    return str(uuid.uuid4())


def create_qr_token(registration_id: str, user_id: str, hackathon_id: str, hackathon_end: datetime) -> str:
    """Create a signed JWT for embedding in a QR code."""
    now = datetime.now(timezone.utc)
    payload = {
        "reg_id": registration_id,
        "user_id": user_id,
        "hackathon_id": hackathon_id,
        "iat": now,
        "exp": hackathon_end + timedelta(hours=24),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_qr_token(token: str) -> dict:
    """Decode and validate a QR token JWT. Raises ValueError if invalid/expired."""
    return decode_token(token)
