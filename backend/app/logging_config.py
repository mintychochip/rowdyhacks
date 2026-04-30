"""Structured logging configuration for HackVerify."""
import logging
import sys
from datetime import datetime
from typing import Any

import structlog
from structlog.types import EventDict


def add_timestamp(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add ISO timestamp to log entry."""
    event_dict["timestamp"] = datetime.utcnow().isoformat()
    return event_dict


def add_service_name(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add service name for identification."""
    event_dict["service"] = "hackverify"
    return event_dict


def configure_logging(log_level: str = "INFO", json_logs: bool = False):
    """Configure structured logging."""
    
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
    """Get a structured logger."""
    return structlog.get_logger(name)


# Request context logging
import contextvars

request_id_var = contextvars.ContextVar("request_id", default=None)
user_id_var = contextvars.ContextVar("user_id", default=None)


def set_request_context(request_id: str | None = None, user_id: str | None = None):
    """Set context for the current request."""
    if request_id:
        request_id_var.set(request_id)
    if user_id:
        user_id_var.set(user_id)


def get_request_context() -> dict:
    """Get current request context."""
    return {
        "request_id": request_id_var.get(),
        "user_id": user_id_var.get(),
    }


# Performance monitoring
import time
from functools import wraps
from typing import Callable, TypeVar

T = TypeVar("T")


def timed(operation: str):
    """Decorator to time function execution."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            logger = get_logger("performance")
            start = time.monotonic()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.monotonic() - start) * 1000
                logger.info(
                    "operation_completed",
                    operation=operation,
                    duration_ms=round(duration_ms, 2),
                    **get_request_context()
                )
                return result
            except Exception as e:
                duration_ms = (time.monotonic() - start) * 1000
                logger.error(
                    "operation_failed",
                    operation=operation,
                    duration_ms=round(duration_ms, 2),
                    error=str(e),
                    **get_request_context()
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            logger = get_logger("performance")
            start = time.monotonic()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.monotonic() - start) * 1000
                logger.info(
                    "operation_completed",
                    operation=operation,
                    duration_ms=round(duration_ms, 2),
                    **get_request_context()
                )
                return result
            except Exception as e:
                duration_ms = (time.monotonic() - start) * 1000
                logger.error(
                    "operation_failed",
                    operation=operation,
                    duration_ms=round(duration_ms, 2),
                    error=str(e),
                    **get_request_context()
                )
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


import asyncio
