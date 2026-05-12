"""Permission system for the assistant - role-based tool access."""

from enum import Enum
from typing import Optional

from fastapi import HTTPException


class UserRole(str, Enum):
    """Enumeration of user roles in the hackathon platform.

    Each role determines which assistant tools and data the user can access.
    """

    PARTICIPANT = "participant"
    JUDGE = "judge"
    ORGANIZER = "organizer"


# Tool definitions with descriptions for LLM
TOOL_DEFINITIONS = {
    # Common tools (all roles)
    "query_hackathon_info": {
        "name": "query_hackathon_info",
        "description": "Get general information about a hackathon including dates, venue, WiFi, parking, etc.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "The specific question about the hackathon"}},
            "required": ["query"],
        },
    },
    "get_tracks": {
        "name": "get_tracks",
        "description": "List all prize tracks/categories with their descriptions, criteria, and prizes",
        "parameters": {
            "type": "object",
            "properties": {
                "hackathon_id": {
                    "type": "string",
                    "description": "The hackathon ID (optional, defaults to current context)",
                }
            },
            "required": [],
        },
    },
    "view_schedule": {
        "name": "view_schedule",
        "description": "Get the hackathon schedule, events, workshops, and important times",
        "parameters": {
            "type": "object",
            "properties": {
                "day": {"type": "string", "description": "Specific day (optional, e.g., 'Saturday', 'Sunday')"}
            },
            "required": [],
        },
    },
    "faq_query": {
        "name": "faq_query",
        "description": "Search the FAQ for answers to common questions",
        "parameters": {
            "type": "object",
            "properties": {"question": {"type": "string", "description": "The question to search for"}},
            "required": ["question"],
        },
    },
    # Participant tools
    "ideation_help": {
        "name": "ideation_help",
        "description": "Get project ideation help and suggestions based on interests and track",
        "parameters": {
            "type": "object",
            "properties": {
                "interests": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of interests/technologies",
                },
                "track_id": {"type": "string", "description": "Specific track to focus on (optional)"},
            },
            "required": ["interests"],
        },
    },
    "submission_guidance": {
        "name": "submission_guidance",
        "description": "Get help with submission requirements, deadlines, and what to include",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Specific submission topic (e.g., 'demo video', 'devpost', 'github')",
                }
            },
            "required": [],
        },
    },
    "view_own_submission_status": {
        "name": "view_own_submission_status",
        "description": "View the status of your team's submission",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    # Judge tools
    "judging_guidelines": {
        "name": "judging_guidelines",
        "description": "Get detailed judging criteria and guidelines for a track",
        "parameters": {
            "type": "object",
            "properties": {"track_id": {"type": "string", "description": "Specific track ID"}},
            "required": [],
        },
    },
    "view_assigned_submissions": {
        "name": "view_assigned_submissions",
        "description": "List all submissions assigned to you for judging",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    "view_submission_details": {
        "name": "view_submission_details",
        "description": "Get detailed information about a specific submission",
        "parameters": {
            "type": "object",
            "properties": {"submission_id": {"type": "string", "description": "The submission ID"}},
            "required": ["submission_id"],
        },
    },
    # Organizer tools
    "participant_search": {
        "name": "participant_search",
        "description": "Search participants by name, email, school, or team",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search query"}},
            "required": ["query"],
        },
    },
    "submission_analytics": {
        "name": "submission_analytics",
        "description": "Get analytics and statistics about submissions",
        "parameters": {
            "type": "object",
            "properties": {"track_id": {"type": "string", "description": "Filter by specific track (optional)"}},
            "required": [],
        },
    },
    "admin_stats": {
        "name": "admin_stats",
        "description": "Get overall hackathon statistics: registrations, check-ins, teams, etc.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    "check_in_status": {
        "name": "check_in_status",
        "description": "Get real-time check-in statistics and status",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    "judging_progress": {
        "name": "judging_progress",
        "description": "Get judging progress and completion rates",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    "modify_faq": {
        "name": "modify_faq",
        "description": "Add or update FAQ entries (will update assistant knowledge)",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "FAQ question"},
                "answer": {"type": "string", "description": "FAQ answer"},
            },
            "required": ["question", "answer"],
        },
    },
    # Site navigation tool (all roles)
    "query_site_pages": {
        "name": "query_site_pages",
        "description": "Search the site for relevant pages by describing what you're looking for. Returns links to pages like application forms, the project gallery, judging portal, resources, leaderboard, and other site features. Use this when a user asks about navigating the platform or finding a specific page.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What the user is looking for, e.g., 'submitting a project', 'checking scores', 'finding resources'",
                }
            },
            "required": ["query"],
        },
    },
}

# Role-based tool permissions
ROLE_TOOLS: dict[UserRole, set[str]] = {
    UserRole.PARTICIPANT: {
        "query_hackathon_info",
        "get_tracks",
        "view_schedule",
        "faq_query",
        "ideation_help",
        "submission_guidance",
        "view_own_submission_status",
        "query_site_pages",
    },
    UserRole.JUDGE: {
        "query_hackathon_info",
        "get_tracks",
        "view_schedule",
        "faq_query",
        "judging_guidelines",
        "view_assigned_submissions",
        "view_submission_details",
        "query_site_pages",
    },
    UserRole.ORGANIZER: {
        # Inherits all tools
        "query_hackathon_info",
        "get_tracks",
        "view_schedule",
        "faq_query",
        "ideation_help",
        "submission_guidance",
        "judging_guidelines",
        "view_assigned_submissions",
        "view_submission_details",
        "participant_search",
        "submission_analytics",
        "admin_stats",
        "check_in_status",
        "judging_progress",
        "modify_faq",
        "query_site_pages",
    },
}


def get_tools_for_role(role: str) -> list[dict]:
    """Return tool definitions available to a role in OpenAI function format.

    Behavior:
    1. Validate the role string against UserRole enum.
    2. Look up the allowed tool names for the role.
    3. Wrap each tool definition in OpenAI function-calling format.
    4. Return the list.

    Raises: HTTPException(400) if the role string is not a valid UserRole.
    Side Effects: None (read-only).
    Dependencies: app.assistant.permissions.UserRole, app.assistant.permissions.TOOL_DEFINITIONS.
    Consumers: Assistant context builder, tool authorization.
    """
    try:
        user_role = UserRole(role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {role}")

    allowed_tools = ROLE_TOOLS.get(user_role, set())
    # Convert to OpenAI function calling format (requires type + function wrapper)
    tools = []
    for tool_name in allowed_tools:
        if tool_name in TOOL_DEFINITIONS:
            tool_def = TOOL_DEFINITIONS[tool_name]
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool_def["name"],
                        "description": tool_def["description"],
                        "parameters": tool_def["parameters"],
                    },
                }
            )
    return tools


def can_use_tool(role: str, tool_name: str) -> bool:
    """Check whether a role is permitted to invoke a specific tool.

    Behavior:
    1. Parse the role string into a UserRole enum.
    2. Return whether the tool_name is in the role's allowed tool set.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.assistant.permissions.UserRole, app.assistant.permissions.ROLE_TOOLS.
    Consumers: Assistant tool dispatch, permission checks.
    """
    try:
        user_role = UserRole(role)
    except ValueError:
        return False

    return tool_name in ROLE_TOOLS.get(user_role, set())


def get_all_tools() -> list[str]:
    """Return every registered tool name.

    Behavior:
    1. Extract and return all keys from TOOL_DEFINITIONS.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.assistant.permissions.TOOL_DEFINITIONS.
    Consumers: Tool enumeration endpoints.
    """
    return list(TOOL_DEFINITIONS.keys())


def get_tool_definition(tool_name: str) -> Optional[dict]:
    """Retrieve the raw definition dict for a single tool.

    Behavior:
    1. Look up ``tool_name`` in ``TOOL_DEFINITIONS``.
    2. Return the matching dict, or ``None`` if not found.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: app.assistant.permissions.TOOL_DEFINITIONS.
    Consumers: Tool metadata endpoints, assistant debugging.
    """
    return TOOL_DEFINITIONS.get(tool_name)


def tools_to_flat_format(tools: list) -> list:
    """Unwrap OpenAI-format tool definitions into flat dicts.

    Behavior:
    1. Iterate over the provided tool dicts.
    2. If a dict contains a ``function`` key, extract the nested dict.
    3. Otherwise keep the dict as-is.
    4. Return the collected flat definitions.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: None
    Consumers: Tool formatting helpers, LLM prompt builders.
    """
    result = []
    for t in tools:
        if isinstance(t, dict) and "function" in t:
            result.append(t["function"])
        else:
            result.append(t)
    return result
