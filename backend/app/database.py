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
    pass


# Context variable to track current user ID for RLS
_current_user_context: ContextVar[Optional[str]] = ContextVar("current_user_id", default=None)


engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def set_current_user_id(user_id: Optional[str]) -> None:
    """Set the current user ID for RLS context."""
    _current_user_context.set(user_id)


def get_current_user_id() -> Optional[str]:
    """Get the current user ID from RLS context."""
    return _current_user_context.get()


async def get_db() -> AsyncSession:
    """FastAPI dependency that yields a database session with RLS context."""
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
