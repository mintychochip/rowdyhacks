"""Tests for Clerk JWT authentication utilities."""

import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import (
    _decode_header,
    _decode_payload,
    _fetch_clerk_jwks,
    _get_signing_key,
    _rsa_key_to_pem,
    decode_clerk_token,
    extract_clerk_user_email,
    extract_clerk_user_id,
    fetch_clerk_user_details,
    is_clerk_token,
    require_clerk_user,
    require_clerk_user_with_db,
    require_organizer,
)
from app.models import User, UserRole


@pytest.fixture(autouse=True)
def clear_jwks_cache():
    """Clear the global JWKS cache before and after each test."""
    import app.clerk_auth as ca

    ca._CLERK_JWKS_CACHE = None
    ca._CLERK_JWKS_CACHE_EXPIRY = None
    yield
    ca._CLERK_JWKS_CACHE = None
    ca._CLERK_JWKS_CACHE_EXPIRY = None


def _make_token(header: dict, payload: dict) -> str:
    """Build a fake JWT string (signature is not valid)."""
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"{header_b64}.{payload_b64}.signature"


class TestIsClerkToken:
    def test_valid_format(self):
        assert is_clerk_token(_make_token({"alg": "RS256"}, {"sub": "u"}))

    def test_empty_string(self):
        assert not is_clerk_token("")

    def test_wrong_dot_count(self):
        assert not is_clerk_token("a.b")
        assert not is_clerk_token("a.b.c.d")

    def test_empty_part(self):
        assert not is_clerk_token("a..c")


class TestDecodeHeader:
    def test_success(self):
        token = _make_token({"alg": "RS256", "kid": "key1"}, {"sub": "u"})
        result = _decode_header(token)
        assert result == {"alg": "RS256", "kid": "key1"}


class TestDecodePayload:
    def test_success(self):
        token = _make_token({"alg": "RS256"}, {"sub": "user123", "email": "a@b.com"})
        result = _decode_payload(token)
        assert result == {"sub": "user123", "email": "a@b.com"}


class TestExtractClerkUserId:
    def test_extracts_sub(self):
        assert extract_clerk_user_id({"sub": "user_123"}) == "user_123"

    def test_missing_sub(self):
        assert extract_clerk_user_id({"email": "a@b.com"}) is None


class TestExtractClerkUserEmail:
    def test_top_level_email(self):
        assert extract_clerk_user_email({"email": "a@b.com"}) == "a@b.com"

    def test_nested_user_data(self):
        payload = {"user_data": {"email_addresses": [{"email_address": "nested@example.com"}]}}
        assert extract_clerk_user_email(payload) == "nested@example.com"

    def test_fallback_keys(self):
        assert extract_clerk_user_email({"email_address": "fallback@example.com"}) == "fallback@example.com"

    def test_no_email(self):
        assert extract_clerk_user_email({"sub": "user"}) is None


class TestGetSigningKey:
    def test_found(self):
        jwks = {"keys": [{"kid": "k1", "kty": "RSA", "n": "abc", "e": "AQAB"}]}
        assert _get_signing_key(jwks, "k1") == {
            "kid": "k1",
            "kty": "RSA",
            "n": "abc",
            "e": "AQAB",
        }

    def test_not_found(self):
        jwks = {"keys": [{"kid": "k1", "kty": "RSA"}]}
        assert _get_signing_key(jwks, "k2") is None

    def test_wrong_kty(self):
        jwks = {"keys": [{"kid": "k1", "kty": "EC"}]}
        assert _get_signing_key(jwks, "k1") is None


class TestRsaKeyToPem:
    def test_converts_key(self):
        with patch("jwt.algorithms.RSAAlgorithm") as MockRSA:
            MockRSA.from_public_numbers.return_value = "key_obj"
            MockRSA.to_pem.return_value = b"pem_string"
            key_data = {"n": "abc123", "e": "AQAB"}
            result = _rsa_key_to_pem(key_data)
            assert result == "pem_string"
            MockRSA.from_public_numbers.assert_called_once()
            MockRSA.to_pem.assert_called_once_with("key_obj")


@pytest.mark.asyncio
async def test_fetch_clerk_jwks_no_secret():
    """When no secret is configured, JWKS is fetched without Authorization header."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"keys": [{"kid": "k1"}]}
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.clerk_auth.settings.clerk_secret_key", ""),
        patch("httpx.AsyncClient", return_value=mock_client),
    ):
        result = await _fetch_clerk_jwks()
        assert result == {"keys": [{"kid": "k1"}]}


@pytest.mark.asyncio
async def test_fetch_clerk_jwks_uses_cache():
    """Subsequent calls within the cache window should not hit the network."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"keys": [{"kid": "k1"}]}
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.clerk_auth.settings.clerk_secret_key", "sk_test_xxx"),
        patch("httpx.AsyncClient", return_value=mock_client),
    ):
        result1 = await _fetch_clerk_jwks()
        assert result1 == {"keys": [{"kid": "k1"}]}
        mock_client.get.assert_called_once()

        result2 = await _fetch_clerk_jwks()
        assert result2 == {"keys": [{"kid": "k1"}]}
        # Still only one HTTP call because of cache
        mock_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_clerk_user_details_no_secret():
    with patch("app.clerk_auth.settings.clerk_secret_key", ""):
        result = await fetch_clerk_user_details("user_123")
        assert result is None


@pytest.mark.asyncio
async def test_fetch_clerk_user_details_success():
    mock_data = {
        "email_addresses": [
            {"id": "ea1", "email_address": "primary@example.com"},
            {"id": "ea2", "email_address": "secondary@example.com"},
        ],
        "primary_email_address_id": "ea1",
        "first_name": "Alice",
        "last_name": "Smith",
    }

    mock_response = MagicMock()
    mock_response.json.return_value = mock_data
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.clerk_auth.settings.clerk_secret_key", "sk_test_xxx"),
        patch("httpx.AsyncClient", return_value=mock_client),
    ):
        result = await fetch_clerk_user_details("user_123")
        assert result == {
            "email": "primary@example.com",
            "name": "Alice Smith",
            "id": "user_123",
        }


@pytest.mark.asyncio
async def test_decode_clerk_token_invalid_format():
    with pytest.raises(ValueError, match="Invalid token format"):
        await decode_clerk_token("not-a-token")


@pytest.mark.asyncio
async def test_decode_clerk_token_no_secret_unverified():
    """In dev mode (no secret), the token payload is decoded without verification."""
    with patch("app.clerk_auth.settings.clerk_secret_key", ""):
        token = _make_token({"alg": "none"}, {"sub": "user", "email": "a@b.com"})
        result = await decode_clerk_token(token)
        assert result == {"sub": "user", "email": "a@b.com"}


@pytest.mark.asyncio
async def test_decode_clerk_token_missing_kid():
    with patch("app.clerk_auth.settings.clerk_secret_key", "sk_test_xxx"):
        token = _make_token({"alg": "RS256"}, {"sub": "user"})
        with pytest.raises(ValueError, match="missing 'kid'"):
            await decode_clerk_token(token)


@pytest.mark.asyncio
async def test_decode_clerk_token_no_signing_key():
    with (
        patch("app.clerk_auth.settings.clerk_secret_key", "sk_test_xxx"),
        patch(
            "app.clerk_auth._fetch_clerk_jwks",
            new=AsyncMock(return_value={"keys": []}),
        ),
    ):
        token = _make_token({"alg": "RS256", "kid": "k1"}, {"sub": "user"})
        with pytest.raises(ValueError, match="No matching signing key"):
            await decode_clerk_token(token)


@pytest.mark.asyncio
async def test_decode_clerk_token_expired():
    with (
        patch("app.clerk_auth.settings.clerk_secret_key", "sk_test_xxx"),
        patch(
            "app.clerk_auth._fetch_clerk_jwks",
            new=AsyncMock(return_value={"keys": [{"kid": "k1", "kty": "RSA"}]}),
        ),
        patch(
            "app.clerk_auth._get_signing_key",
            return_value={"kid": "k1", "kty": "RSA"},
        ),
        patch("app.clerk_auth._rsa_key_to_pem", return_value="fake_pem"),
        patch("jwt.decode", side_effect=jwt.ExpiredSignatureError("expired")),
    ):
        token = _make_token({"alg": "RS256", "kid": "k1"}, {"sub": "user"})
        with pytest.raises(ValueError, match="Token has expired"):
            await decode_clerk_token(token)


@pytest.mark.asyncio
async def test_decode_clerk_token_invalid_signature():
    with (
        patch("app.clerk_auth.settings.clerk_secret_key", "sk_test_xxx"),
        patch(
            "app.clerk_auth._fetch_clerk_jwks",
            new=AsyncMock(return_value={"keys": [{"kid": "k1", "kty": "RSA"}]}),
        ),
        patch(
            "app.clerk_auth._get_signing_key",
            return_value={"kid": "k1", "kty": "RSA"},
        ),
        patch("app.clerk_auth._rsa_key_to_pem", return_value="fake_pem"),
        patch("jwt.decode", side_effect=jwt.InvalidTokenError("bad sig")),
    ):
        token = _make_token({"alg": "RS256", "kid": "k1"}, {"sub": "user"})
        with pytest.raises(ValueError, match="Invalid token"):
            await decode_clerk_token(token)


@pytest.mark.asyncio
async def test_decode_clerk_token_success():
    payload = {"sub": "user123", "email": "a@b.com"}
    with (
        patch("app.clerk_auth.settings.clerk_secret_key", "sk_test_xxx"),
        patch(
            "app.clerk_auth._fetch_clerk_jwks",
            new=AsyncMock(return_value={"keys": [{"kid": "k1", "kty": "RSA"}]}),
        ),
        patch(
            "app.clerk_auth._get_signing_key",
            return_value={"kid": "k1", "kty": "RSA"},
        ),
        patch("app.clerk_auth._rsa_key_to_pem", return_value="fake_pem"),
        patch("jwt.decode", return_value=payload),
    ):
        token = _make_token({"alg": "RS256", "kid": "k1"}, payload)
        result = await decode_clerk_token(token)
        assert result == payload


@pytest.mark.asyncio
async def test_require_clerk_user_missing_header():
    with pytest.raises(HTTPException) as exc_info:
        await require_clerk_user(None)
    assert exc_info.value.status_code == 401
    assert "Missing or invalid" in exc_info.value.detail


@pytest.mark.asyncio
async def test_require_clerk_user_invalid_bearer():
    with pytest.raises(HTTPException) as exc_info:
        await require_clerk_user("Basic abc")
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_require_clerk_user_invalid_token_format():
    with pytest.raises(HTTPException) as exc_info:
        await require_clerk_user("Bearer bad-token")
    assert exc_info.value.status_code == 401
    assert "Invalid token format" in exc_info.value.detail


@pytest.mark.asyncio
async def test_require_clerk_user_decode_failure():
    with patch(
        "app.clerk_auth.decode_clerk_token",
        new=AsyncMock(side_effect=ValueError("bad token")),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await require_clerk_user("Bearer header.payload.sig")
        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail


@pytest.mark.asyncio
async def test_require_clerk_user_missing_sub():
    with patch(
        "app.clerk_auth.decode_clerk_token",
        new=AsyncMock(return_value={"email": "a@b.com"}),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await require_clerk_user("Bearer header.payload.sig")
        assert exc_info.value.status_code == 401
        assert "missing user ID" in exc_info.value.detail


@pytest.mark.asyncio
async def test_require_clerk_user_success():
    payload = {"sub": "user123", "email": "a@b.com", "extra": 1}
    with patch(
        "app.clerk_auth.decode_clerk_token",
        new=AsyncMock(return_value=payload),
    ):
        result = await require_clerk_user("Bearer header.payload.sig")
        assert result["sub"] == "user123"
        assert result["email"] == "a@b.com"
        assert result["payload"] == payload


@pytest.mark.asyncio
async def test_require_clerk_user_with_db_existing_user(db_session: AsyncSession):
    user = User(id="user-123", email="a@b.com", name="Alice", role=UserRole.participant)
    db_session.add(user)
    await db_session.commit()

    with patch(
        "app.clerk_auth.require_clerk_user",
        new=AsyncMock(return_value={"sub": "user-123", "email": "a@b.com", "payload": {}}),
    ):
        result = await require_clerk_user_with_db("Bearer token", db_session)
        assert result["user"].id == "user-123"
        assert result["sub"] == "user-123"


@pytest.mark.asyncio
async def test_require_clerk_user_with_db_auto_create(db_session: AsyncSession):
    with patch(
        "app.clerk_auth.require_clerk_user",
        new=AsyncMock(return_value={"sub": "new-user", "email": "new@b.com", "payload": {}}),
    ):
        result = await require_clerk_user_with_db("Bearer token", db_session)
        assert result["user"].id == "new-user"
        assert result["user"].email == "new@b.com"
        assert result["user"].role == UserRole.participant


@pytest.mark.asyncio
async def test_require_clerk_user_with_db_fetches_clerk_when_no_email(
    db_session: AsyncSession,
):
    with (
        patch(
            "app.clerk_auth.require_clerk_user",
            new=AsyncMock(return_value={"sub": "no-email-user", "email": None, "payload": {}}),
        ),
        patch(
            "app.clerk_auth.fetch_clerk_user_details",
            new=AsyncMock(return_value={"email": "clerk@example.com", "name": "Clerk User"}),
        ),
    ):
        result = await require_clerk_user_with_db("Bearer token", db_session)
        assert result["user"].email == "clerk@example.com"


@pytest.mark.asyncio
async def test_require_organizer_allows_organizer(db_session: AsyncSession):
    user = User(id="org-1", email="org@b.com", name="Org", role=UserRole.organizer)
    db_session.add(user)
    await db_session.commit()

    with patch(
        "app.clerk_auth.require_clerk_user",
        new=AsyncMock(return_value={"sub": "org-1", "email": "org@b.com", "payload": {}}),
    ):
        result = await require_organizer("Bearer token", db_session)
        assert result["user"].role == UserRole.organizer


@pytest.mark.asyncio
async def test_require_organizer_rejects_participant(db_session: AsyncSession):
    user = User(
        id="part-1",
        email="part@b.com",
        name="Part",
        role=UserRole.participant,
    )
    db_session.add(user)
    await db_session.commit()

    with patch(
        "app.clerk_auth.require_clerk_user",
        new=AsyncMock(
            return_value={
                "sub": "part-1",
                "email": "part@b.com",
                "payload": {},
            }
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await require_organizer("Bearer token", db_session)
        assert exc_info.value.status_code == 403
        assert "Organizer access required" in exc_info.value.detail
