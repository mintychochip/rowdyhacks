import logging
from typing import Callable
from datetime import UTC, datetime
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Event

logger = logging.getLogger(__name__)


class EventService:
    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = {}

    async def publish(self, db: AsyncSession, type: str, payload: dict) -> Event:
        """Persist event to DB and dispatch to in-memory subscribers."""
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
        """Register an in-memory callback for an event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable):
        """Remove a callback."""
        if event_type in self._subscribers:
            self._subscribers[event_type] = [c for c in self._subscribers[event_type] if c != callback]


# Singleton instance for app-wide use
_event_service = EventService()


async def publish_event(db: AsyncSession, type: str, payload: dict) -> Event:
    """Convenience wrapper around the singleton EventService."""
    return await _event_service.publish(db, type, payload)
