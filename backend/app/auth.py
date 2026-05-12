"""Auth utilities for self-hosted hackathon platform.
Handles JWT tokens, password hashing, refresh tokens, OAuth state, and Fernet encryption.
"""

import base64
import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import RefreshToken, User

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


# --- Fernet key derivation ---


def _get_fernet() -> Fernet:
    """Derive a Fernet key from HACKVERIFY_SECRET_KEY via HKDF-SHA256."""
    key = hashlib.sha256(settings.secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_secret(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    return _get_fernet().decrypt(ciphertext.encode()).decode()


# --- Password hashing ---


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


# --- JWT tokens ---


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.now(UTC)})
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def verify_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError as e:
        raise ValueError(f"Invalid or expired token: {e}") from e


# --- Refresh tokens ---


def create_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def store_refresh_token(
    db: AsyncSession, user_id: str, token: str, expires_days: int = REFRESH_TOKEN_EXPIRE_DAYS
) -> RefreshToken:
    rt = RefreshToken(
        user_id=user_id,
        token_hash=hash_refresh_token(token),
        expires_at=datetime.now(UTC) + timedelta(days=expires_days),
    )
    db.add(rt)
    await db.commit()
    await db.refresh(rt)
    return rt


async def verify_refresh_token(db: AsyncSession, token: str) -> RefreshToken | None:
    token_hash = hash_refresh_token(token)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(UTC),
        )
    )
    return result.scalar_one_or_none()


async def revoke_refresh_token(db: AsyncSession, token: str) -> None:
    token_hash = hash_refresh_token(token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    rt = result.scalar_one_or_none()
    if rt:
        rt.revoked_at = datetime.now(UTC)
        await db.commit()


# --- Current user dependencies ---


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = verify_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("No user ID in token")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_current_user_ws(token: str | None) -> dict | None:
    """Validate JWT token for WebSocket connections."""
    if not token:
        return None
    try:
        payload = verify_access_token(token)
        return {
            "id": payload.get("sub"),
            "role": payload.get("role"),
            "email": payload.get("email"),
        }
    except ValueError:
        return None


# --- Role requirements ---


def require_organizer(user: User = Depends(get_current_user)) -> User:
    if user.role.value != "organizer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organizer access required")
    return user


def require_participant(user: User = Depends(get_current_user)) -> User:
    if user.role.value not in ("participant", "organizer", "judge"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Participant access required")
    return user


def require_judge(user: User = Depends(get_current_user)) -> User:
    if user.role.value not in ("judge", "organizer"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Judge access required")
    return user


# --- Password reset ---


def generate_reset_token() -> str:
    return secrets.token_urlsafe(32)


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# --- OAuth state ---


def generate_oauth_state() -> str:
    return secrets.token_urlsafe(32)


# --- Validation ---


def validate_password(password: str) -> bool:
    """Password must be at least 8 chars with uppercase, lowercase, and digit."""
    if len(password) < 8:
        return False
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    return has_upper and has_lower and has_digit


# --- Legacy internal JWTs (QR codes and anonymous tokens) ---


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
