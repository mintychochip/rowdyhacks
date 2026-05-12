"""Centralized audit log service and decorator.

Provides a simple ``log_action`` helper and a FastAPI-compatible
``@audit_log`` decorator that records actions after successful route execution.
"""

import functools
import inspect
import uuid
from datetime import UTC, datetime
from typing import Callable

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


async def log_action(
    db: AsyncSession,
    action: str,
    user_id: str | None = None,
    hackathon_id: uuid.UUID | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """Write a single audit log entry.

    Behavior:
    1. Build an AuditLog row with the provided fields.
    2. Add to the session and commit.
    3. Return the created AuditLog instance.

    Raises: None
    Side Effects: Inserts an AuditLog row.
    """
    entry = AuditLog(
        user_id=user_id,
        hackathon_id=hackathon_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details_json=details or {},
        ip_address=ip_address,
        created_at=datetime.now(UTC),
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


def audit_log(action: str, entity_type: str | None = None, entity_id_param: str | None = None):
    """Decorator that records an audit log after a successful route handler.

    Behavior:
    1. Wrap the route handler so that after successful execution an AuditLog row is written.
    2. Extract ``user_id`` from the ``auth`` or ``user_payload`` kwargs if present.
    3. Extract ``hackathon_id`` from kwargs if present (common param name).
    4. Extract ``entity_id`` from the return value dict if it contains ``id``, or from kwargs via ``entity_id_param``.
    5. Use ``ip_address`` from the request if a ``request`` kwarg is present.

    Args:
        action: The action name to log (e.g. "create_hackathon").
        entity_type: Optional entity type label.
        entity_id_param: The name of a kwarg whose value should be used as entity_id.

    Raises: None (audit logging failures are silently ignored so the route still succeeds).
    Side Effects: Inserts an AuditLog row on success.

    Example:
        @router.post("/api/hackathons")
        @audit_log(action="create_hackathon", entity_type="hackathon")
        async def create_hackathon(..., auth: dict = Depends(require_clerk_user_with_db), db: AsyncSession = Depends(get_db)):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            try:
                db: AsyncSession | None = kwargs.get("db")
                if db is None:
                    return result

                user_id: str | None = None
                auth = kwargs.get("auth") or kwargs.get("user_payload")
                if isinstance(auth, dict):
                    user_id = auth.get("sub") or auth.get("user_id")
                    if hasattr(auth.get("user"), "id"):
                        user_id = auth["user"].id

                hackathon_id: uuid.UUID | None = kwargs.get("hackathon_id")
                if hackathon_id and isinstance(hackathon_id, str):
                    try:
                        hackathon_id = uuid.UUID(hackathon_id)
                    except ValueError:
                        hackathon_id = None

                entity_id: str | None = None
                if entity_id_param and entity_id_param in kwargs:
                    raw = kwargs[entity_id_param]
                    entity_id = str(raw) if raw is not None else None
                elif isinstance(result, dict) and "id" in result:
                    entity_id = str(result["id"])

                ip_address: str | None = None
                request = kwargs.get("request")
                if isinstance(request, Request):
                    ip_address = request.client.host if request.client else None

                details: dict | None = None
                if isinstance(result, dict):
                    details = {"status_code": 200}

                await log_action(
                    db=db,
                    action=action,
                    user_id=user_id,
                    hackathon_id=hackathon_id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    details=details,
                    ip_address=ip_address,
                )
            except Exception:
                # Never fail the original request because of audit logging
                pass

            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            try:
                db: AsyncSession | None = kwargs.get("db")
                if db is None:
                    return result

                user_id: str | None = None
                auth = kwargs.get("auth") or kwargs.get("user_payload")
                if isinstance(auth, dict):
                    user_id = auth.get("sub") or auth.get("user_id")
                    if hasattr(auth.get("user"), "id"):
                        user_id = auth["user"].id

                hackathon_id: uuid.UUID | None = kwargs.get("hackathon_id")
                if hackathon_id and isinstance(hackathon_id, str):
                    try:
                        hackathon_id = uuid.UUID(hackathon_id)
                    except ValueError:
                        hackathon_id = None

                entity_id: str | None = None
                if entity_id_param and entity_id_param in kwargs:
                    raw = kwargs[entity_id_param]
                    entity_id = str(raw) if raw is not None else None
                elif isinstance(result, dict) and "id" in result:
                    entity_id = str(result["id"])

                ip_address: str | None = None
                request = kwargs.get("request")
                if isinstance(request, Request):
                    ip_address = request.client.host if request.client else None

                details: dict | None = None
                if isinstance(result, dict):
                    details = {"status_code": 200}

                # For sync wrappers we cannot await; skip logging in sync context
                # or fire-and-forget if there's an event loop
                import asyncio

                try:
                    loop = asyncio.get_running_loop()
                    if loop.is_running():
                        loop.create_task(
                            log_action(
                                db=db,
                                action=action,
                                user_id=user_id,
                                hackathon_id=hackathon_id,
                                entity_type=entity_type,
                                entity_id=entity_id,
                                details=details,
                                ip_address=ip_address,
                            )
                        )
                except RuntimeError:
                    pass
            except Exception:
                pass

            return result

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
