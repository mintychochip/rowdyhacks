"""In-memory event bus with database persistence.

Provides a pub/sub event system where events are persisted to PostgreSQL
and also dispatched to in-memory subscribers for real-time handling.
"""

import logging
from typing import Callable
from datetime import UTC, datetime
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Event

logger = logging.getLogger(__name__)


class EventService:
    """Publish and subscribe to events with DB persistence.

    Events are written to the database for audit and replay, then dispatched
    to any registered in-memory callbacks. Subscriber exceptions are logged
    but do not prevent event persistence.
    """

    def __init__(self):
        """Initialize the subscriber registry."""
        self._subscribers: dict[str, list[Callable]] = {}

    async def publish(self, db: AsyncSession, type: str, payload: dict) -> Event:
        """Persist event to DB and dispatch to in-memory subscribers.

        Behavior:
        1. Build an Event instance with the given type and payload.
        2. Persist it to the database.
        3. Iterate subscribers for the event type and invoke each callback.
        4. Log subscriber exceptions without aborting dispatch.

        Raises: None
        Side Effects: Inserts Event row; invokes subscriber callbacks.
        Dependencies: app.models.Event.
        Consumers: EventService.publish_event wrapper.
        """
        event = Event(id=uuid.uuid4(), type=type, payload=payload, created_at=datetime.now(UTC))
        db.add(event)
        await db.commit()
        await db.refresh(event)

        # Dispatch to subscribers
        for callback in self._subscribers.get(type, []):
            try:
                await callback(event)
            except Exception:
                logger.exception(f"Subscriber error for event type {type}")

        return event

    def subscribe(self, event_type: str, callback: Callable):
        """Register an in-memory callback for an event type.

        Behavior:
        1. Initialize the subscriber list for the event type if absent.
        2. Append the callback.

        Raises: None
        Side Effects: Mutates ``_subscribers`` dict.
        Dependencies: None
        Consumers: Event bootstrap / wiring code.
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable):
        """Remove a previously registered callback for an event type.

        Behavior:
        1. Filter the subscriber list to exclude the given callback.

        Raises: None
        Side Effects: Mutates ``_subscribers`` dict.
        Dependencies: None
        Consumers: Event teardown / wiring code.
        """
        if event_type in self._subscribers:
            self._subscribers[event_type] = [c for c in self._subscribers[event_type] if c != callback]


# Singleton instance for app-wide use
_event_service = EventService()


async def publish_event(db: AsyncSession, type: str, payload: dict) -> Event:
    """Convenience wrapper around the singleton EventService.

    Behavior:
    1. Delegate to the global ``_event_service.publish`` method.

    Raises: None
    Side Effects: Persists Event row.
    Dependencies: EventService.publish.
    Consumers: Routes and services that fire events.
    """
    return await _event_service.publish(db, type, payload)
