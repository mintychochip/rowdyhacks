from datetime import timedelta

import pytest

from app.auth import create_access_token, create_anonymous_token, decode_token, hash_password, verify_password


class TestPasswordHashing:
    def test_hash_and_verify_round_trip(self):
        password = "my-secure-password-123!"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("correct-password")
        assert verify_password("wrong-password", hashed) is False

    def test_hash_is_different_each_time(self):
        password = "same-password"
        h1 = hash_password(password)
        h2 = hash_password(password)
        assert h1 != h2


class TestAccessToken:
    def test_create_and_decode_round_trip(self):
        user_id = "550e8400-e29b-41d4-a716-446655440000"
        token = create_access_token(user_id=user_id, role="organizer")
        payload = decode_token(token)
        assert payload["sub"] == user_id
        assert payload["role"] == "organizer"
        assert "exp" in payload

    def test_token_expiry(self):
        user_id = "550e8400-e29b-41d4-a716-446655440000"
        token = create_access_token(user_id=user_id, role="participant", expires_delta=timedelta(seconds=-1))
        with pytest.raises(Exception, match="expired|exp|Invalid"):
            decode_token(token)

    def test_decode_invalid_token(self):
        with pytest.raises(Exception):
            decode_token("this-is-not-a-valid-jwt")


class TestAnonymousToken:
    def test_create_anonymous_token_format(self):
        token = create_anonymous_token()
        import uuid

        parsed = uuid.UUID(token)
        assert str(parsed) == token
