"""AI Assistant package for Hack the Valley."""

from app.assistant.embedder import embedder
from app.assistant.permissions import (
    ROLE_TOOLS,
    TOOL_DEFINITIONS,
    UserRole,
    can_use_tool,
    get_tool_definition,
    get_tools_for_role,
)
from app.assistant.vector_store import vector_store

__all__ = [
    "vector_store",
    "embedder",
    "UserRole",
    "ROLE_TOOLS",
    "TOOL_DEFINITIONS",
    "get_tools_for_role",
    "can_use_tool",
    "get_tool_definition",
]
