"""Tests for WebhookService delivery and HMAC signing."""

import pytest

from app.services.webhook_service import WebhookService


class FakeEvent:
    def __init__(self, id, type, payload, created_at):
        self.id = id
        self.type = type
        self.payload = payload
        self.created_at = created_at


class FakeSubscription:
    def __init__(self, id, url, secret, events, active=True):
        self.id = id
        self.url = url
        self.secret = secret
        self.events = events
        self.active = active


def test_sign_generates_hmac():
    """_sign must produce a valid HMAC-SHA256 hex digest."""
    service = WebhookService()
    body = '{"foo":"bar"}'
    secret = "my-secret"
    sig = service._sign(body, secret)
    assert isinstance(sig, str)
    assert len(sig) == 64  # SHA-256 hex length


@pytest.mark.anyio
async def test_deliver_creates_log(db_session):
    """deliver must create a WebhookDeliveryLog entry."""
    from datetime import UTC, datetime
    import uuid

    from app.models import WebhookDeliveryLog

    service = WebhookService()
    event = FakeEvent(
        id=uuid.uuid4(),
        type="registration.created",
        payload={"id": "123"},
        created_at=datetime.now(UTC),
    )
    sub = FakeSubscription(
        id=uuid.uuid4(),
        url="https://httpbin.org/post",
        secret="shhh",
        events=["registration.created"],
    )

    log = await service.deliver(db_session, event, sub)
    assert str(log.subscription_id) == str(sub.id)
    assert str(log.event_id) == str(event.id)
    assert log.status in ("success", "failed")
    assert log.id is not None

    # Verify DB row exists
    result = await db_session.get(WebhookDeliveryLog, log.id)
    assert result is not None
