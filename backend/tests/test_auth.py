import uuid

import pytest
from app.auth import create_anonymous_token, decode_token


class TestDecodeToken:
    def test_decode_invalid_token(self):
        with pytest.raises(Exception):
            decode_token("this-is-not-a-valid-jwt")


class TestAnonymousToken:
    def test_create_anonymous_token_format(self):
        token = create_anonymous_token()
        parsed = uuid.UUID(token)
        assert str(parsed) == token
