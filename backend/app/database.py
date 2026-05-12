"""Database session management and SQLAlchemy base.

Provides the declarative base for all ORM models, an async engine,
and a FastAPI-compatible dependency that yields sessions with
row-level security (RLS) context applied automatically.
"""

import sqlite3
import uuid
from contextvars import ContextVar
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# Register UUID adapter for SQLite so uuid.UUID objects can be bound to String columns
sqlite3.register_adapter(uuid.UUID, lambda u: str(u))


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all ORM models.

    All tables in the hackathon platform inherit from this base so
    that metadata and migration tools can discover them consistently.
    """

    pass


# Context variable to track current user ID for RLS
_current_user_context: ContextVar[Optional[str]] = ContextVar("current_user_id", default=None)


engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def set_current_user_id(user_id: Optional[str]) -> None:
    """Set the current user ID for RLS context.

    Behavior:
    1. Store the provided user_id in the thread-local context variable.

    Raises: None
    Side Effects: Mutates the ``_current_user_context`` ContextVar.
    Dependencies: contextvars.ContextVar.
    Consumers: Internal helper used by auth middleware and route dependencies.
    """
    _current_user_context.set(user_id)


def get_current_user_id() -> Optional[str]:
    """Get the current user ID from RLS context.

    Behavior:
    1. Retrieve the value stored in the ``_current_user_context`` ContextVar.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: contextvars.ContextVar.
    Consumers: Internal helper used by RLS policy functions and route guards.
    """
    return _current_user_context.get()


async def get_db() -> AsyncSession:
    """FastAPI dependency that yields a database session with RLS context.

    Behavior:
    1. Open an async SQLAlchemy session.
    2. Read the current user ID from the RLS context variable.
    3. Execute ``SET LOCAL app.current_user_id`` with the user ID (or empty string).
    4. Yield the session to the route handler.
    5. In the finally block, clear the RLS user ID and close the session.

    Raises: None
    Side Effects: Executes SET LOCAL on the database connection; closes the session.
    Dependencies: app.database.async_session, app.database.get_current_user_id, sqlalchemy.text.
    Consumers: FastAPI Depends() across all route modules.
    """
    async with async_session() as session:
        try:
            # Set RLS context for this session
            user_id = get_current_user_id()
            if user_id:
                await session.execute(text(f"SET LOCAL app.current_user_id = '{user_id}'"))
            else:
                await session.execute(text("SET LOCAL app.current_user_id = ''"))

            yield session
        finally:
            # Clear RLS context
            try:
                await session.execute(text("SET LOCAL app.current_user_id = ''"))
            except Exception:
                pass  # Connection might already be closed
            await session.close()
