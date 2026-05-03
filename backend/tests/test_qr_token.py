import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.auth import create_qr_token, decode_qr_token


def test_create_and_decode_qr_token():
    reg_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    hackathon_id = str(uuid.uuid4())
    end = datetime.now(UTC) + timedelta(days=3)

    token = create_qr_token(reg_id, user_id, hackathon_id, end)
    payload = decode_qr_token(token)

    assert payload["reg_id"] == reg_id
    assert payload["user_id"] == user_id
    assert payload["hackathon_id"] == hackathon_id


def test_decode_expired_qr_token():
    reg_id = str(uuid.uuid4())
    end = datetime.now(UTC) - timedelta(days=2)

    token = create_qr_token(reg_id, str(uuid.uuid4()), str(uuid.uuid4()), end)
    with pytest.raises(ValueError):
        decode_qr_token(token)


def test_decode_tampered_qr_token():
    reg_id = str(uuid.uuid4())
    end = datetime.now(UTC) + timedelta(days=3)
    token = create_qr_token(reg_id, str(uuid.uuid4()), str(uuid.uuid4()), end)
    # Tamper by appending a character
    with pytest.raises(ValueError):
        decode_qr_token(token + "x")
