import pytest
from sqlalchemy import select

from app.models import Event
from app.services.event_service import EventService


@pytest.fixture
def service():
    return EventService()


@pytest.mark.asyncio
async def test_publish_creates_db_row(service, db_session):
    event = await service.publish(db_session, "submission.created", {"id": "123"})
    assert isinstance(event, Event)
    assert event.type == "submission.created"
    assert event.payload == {"id": "123"}

    result = await db_session.execute(select(Event).where(Event.id == event.id))
    db_event = result.scalar_one_or_none()
    assert db_event is not None
    assert db_event.type == "submission.created"
    assert db_event.payload == {"id": "123"}


@pytest.mark.asyncio
async def test_subscriber_receives_event(service, db_session):
    received = []

    async def callback(event):
        received.append(event)

    service.subscribe("submission.created", callback)
    event = await service.publish(db_session, "submission.created", {"id": "456"})

    assert len(received) == 1
    assert received[0].id == event.id
    assert received[0].payload == {"id": "456"}
