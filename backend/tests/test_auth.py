import uuid
from datetime import timedelta

import pytest
from app.auth import (
    create_access_token,
    create_anonymous_token,
    decode_token,
    hash_password,
    verify_access_token,
    verify_password,
)


class TestDecodeToken:
    def test_decode_invalid_token(self):
        with pytest.raises(Exception):
            decode_token("this-is-not-a-valid-jwt")


class TestAnonymousToken:
    def test_create_anonymous_token_format(self):
        token = create_anonymous_token()
        parsed = uuid.UUID(token)
        assert str(parsed) == token


def test_hash_and_verify_password():
    hashed = hash_password("MyPassword123")
    assert verify_password("MyPassword123", hashed)
    assert not verify_password("WrongPassword", hashed)


def test_create_and_verify_access_token():
    token = create_access_token({"sub": "user-123", "email": "test@example.com", "role": "participant"})
    payload = verify_access_token(token)
    assert payload["sub"] == "user-123"
    assert payload["email"] == "test@example.com"


def test_verify_expired_token():
    token = create_access_token({"sub": "user-123"}, expires_delta=timedelta(seconds=-1))
    with pytest.raises(ValueError, match="expired"):
        verify_access_token(token)
