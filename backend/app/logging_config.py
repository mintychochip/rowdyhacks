"""Structured logging configuration for HackVerify."""

import logging
import sys
from datetime import datetime
from typing import Any

import structlog
from structlog.types import EventDict


def add_timestamp(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add an ISO timestamp to a structlog event dictionary.

    Behavior:
    1. Compute the current UTC time in ISO format.
    2. Inject it into the event dict under the ``timestamp`` key.
    3. Return the mutated dict.

    Raises: None
    Side Effects: Mutates the provided event_dict.
    Dependencies: datetime.datetime.utcnow.
    Consumers: structlog processor pipeline configured in configure_logging.
    """
    event_dict["timestamp"] = datetime.now(datetime.now().astimezone().tzinfo).isoformat()
    return event_dict


def add_service_name(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add the service name to a structlog event dictionary.

    Behavior:
    1. Set the ``service`` key to ``hackverify``.
    2. Return the mutated dict.

    Raises: None
    Side Effects: Mutates the provided event_dict.
    Dependencies: None.
    Consumers: structlog processor pipeline configured in configure_logging.
    """
    event_dict["service"] = "hackverify"
    return event_dict


def configure_logging(log_level: str = "INFO", json_logs: bool = False):
    """Configure structlog and standard-library logging for the application.

    Behavior:
    1. Build the shared processor list (contextvars merge, log level, ISO timestamp, service name, extra adder).
    2. In production mode (json_logs=True), append exception formatting and a JSON renderer.
    3. In development mode, append a pretty console renderer.
    4. Call ``structlog.configure`` with the processors, filtering wrapper, and print logger factory.
    5. Set ``logging.basicConfig`` to route standard-library logs to stdout.

    Raises: None
    Side Effects: Mutates global structlog and stdlib logging configuration.
    Dependencies: structlog, logging, sys.
    Consumers: app.main startup sequence.
    """

    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        add_service_name,
        structlog.stdlib.ExtraAdder(),
    ]

    if json_logs:
        # Production: JSON logs
        shared_processors.append(structlog.processors.format_exc_info)
        shared_processors.append(structlog.processors.JSONRenderer())
    else:
        # Development: pretty console logs
        shared_processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, log_level)),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level),
    )


def get_logger(name: str):
    """Retrieve a structured logger instance by name.

    Behavior:
    1. Call ``structlog.get_logger`` with the provided name.
    2. Return the bound logger.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: structlog.get_logger.
    Consumers: Application modules and the ``timed`` decorator.
    """
    return structlog.get_logger(name)


# Request context logging
import contextvars

request_id_var = contextvars.ContextVar("request_id", default=None)
user_id_var = contextvars.ContextVar("user_id", default=None)


def set_request_context(request_id: str | None = None, user_id: str | None = None):
    """Set request-scoped context variables for structured logging.

    Behavior:
    1. If a request_id is provided, store it in the ``request_id_var`` ContextVar.
    2. If a user_id is provided, store it in the ``user_id_var`` ContextVar.

    Raises: None
    Side Effects: Mutates asyncio context variables.
    Dependencies: contextvars.ContextVar.
    Consumers: FastAPI middleware and route handlers.
    """
    if request_id is not None:
        request_id_var.set(request_id)
    if user_id is not None:
        user_id_var.set(user_id)


def get_request_context() -> dict:
    """Retrieve the current request-scoped logging context.

    Behavior:
    1. Read the values from ``request_id_var`` and ``user_id_var``.
    2. Return them in a dict with keys ``request_id`` and ``user_id``.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: contextvars.ContextVar.
    Consumers: app.logging_config.timed decorator and structured log processors.
    """
    return {
        "request_id": request_id_var.get(),
        "user_id": user_id_var.get(),
    }


# Performance monitoring
import time
from collections.abc import Callable
from functools import wraps
from typing import TypeVar

T = TypeVar("T")


def timed(operation: str):
    """Decorator that records execution duration and logs completion or failure.

    Behavior:
    1. Detect whether the wrapped function is async or sync.
    2. On entry, capture a monotonic start timestamp.
    3. On successful exit, compute duration and emit an ``operation_completed`` info log.
    4. On exception, compute duration and emit an ``operation_failed`` error log, then re-raise.
    5. Return the appropriate wrapper (async or sync).

    Raises: None (the decorator itself does not raise; it re-raises the wrapped function's exceptions).
    Side Effects: Emits structured log events via structlog.
    Dependencies: app.logging_config.get_logger, app.logging_config.get_request_context, time.monotonic.
    Consumers: Performance-sensitive functions across the codebase.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        """Wrap a function with execution timing and logging.

        Behavior:
        1. Preserve the original function's metadata via ``functools.wraps``.
        2. Inspect the function to decide between the async and sync wrapper.
        3. Return the chosen wrapper.

        Raises: None
        Side Effects: None at decoration time.
        Dependencies: functools.wraps, asyncio.iscoroutinefunction.
        Consumers: Internal decorator factory used by ``timed()``.
        """

        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            """Time an async function invocation and log the outcome.

            Behavior:
            1. Capture a monotonic start timestamp.
            2. Await the wrapped function.
            3. On success, compute duration and emit an ``operation_completed`` info log.
            4. On exception, compute duration, emit an ``operation_failed`` error log, and re-raise.

            Raises: Whatever the wrapped function raises.
            Side Effects: Emits structured log events.
            Dependencies: app.logging_config.get_logger, app.logging_config.get_request_context.
            Consumers: Runtime invocations of decorated async functions.
            """
            logger = get_logger("performance")
            start = time.monotonic()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.monotonic() - start) * 1000
                logger.info(
                    "operation_completed",
                    operation=operation,
                    duration_ms=round(duration_ms, 2),
                    **get_request_context(),
                )
                return result
            except Exception as e:
                duration_ms = (time.monotonic() - start) * 1000
                logger.error(
                    "operation_failed",
                    operation=operation,
                    duration_ms=round(duration_ms, 2),
                    error=str(e),
                    **get_request_context(),
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            """Time a sync function invocation and log the outcome.

            Behavior:
            1. Capture a monotonic start timestamp.
            2. Call the wrapped function.
            3. On success, compute duration and emit an ``operation_completed`` info log.
            4. On exception, compute duration, emit an ``operation_failed`` error log, and re-raise.

            Raises: Whatever the wrapped function raises.
            Side Effects: Emits structured log events.
            Dependencies: app.logging_config.get_logger, app.logging_config.get_request_context.
            Consumers: Runtime invocations of decorated sync functions.
            """
            logger = get_logger("performance")
            start = time.monotonic()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.monotonic() - start) * 1000
                logger.info(
                    "operation_completed",
                    operation=operation,
                    duration_ms=round(duration_ms, 2),
                    **get_request_context(),
                )
                return result
            except Exception as e:
                duration_ms = (time.monotonic() - start) * 1000
                logger.error(
                    "operation_failed",
                    operation=operation,
                    duration_ms=round(duration_ms, 2),
                    error=str(e),
                    **get_request_context(),
                )
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


import asyncio
