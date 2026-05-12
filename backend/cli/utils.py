"""Shared utilities for the OpenHack CLI."""

import asyncio
from contextlib import asynccontextmanager

import typer
from rich.console import Console
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

console = Console()


def get_engine():
    """Create an async engine from settings."""
    return create_async_engine(settings.database_url, echo=False)


async def get_session() -> AsyncSession:
    """Yield an async DB session for CLI operations."""
    engine = get_engine()
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


@asynccontextmanager
async def db_session():
    """Async context manager for DB sessions in CLI commands."""
    engine = get_engine()
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


def run_async(coro):
    """Run an async coroutine from a sync CLI command."""
    return asyncio.run(coro)


def confirm_action(message: str, abort: bool = True) -> bool:
    """Prompt user for confirmation before destructive actions."""
    confirmed = typer.confirm(message)
    if abort and not confirmed:
        raise typer.Abort()
    return confirmed
