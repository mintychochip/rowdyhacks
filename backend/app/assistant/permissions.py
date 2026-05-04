"""Permission system for the assistant - role-based tool access."""

from enum import Enum
from typing import Dict, List, Set

from fastapi import HTTPException


class UserRole(str, Enum):
    """User roles in the system."""

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
            "properties": {
                "query": {"type": "string", "description": "The specific question about the hackathon"}
            },
            "required": ["query"]
        }
    },
    "get_tracks": {
        "name": "get_tracks",
        "description": "List all prize tracks/categories with their descriptions, criteria, and prizes",
        "parameters": {
            "type": "object",
            "properties": {
                "hackathon_id": {"type": "string", "description": "The hackathon ID (optional, defaults to current context)"}
            },
            "required": []
        }
    },
    "view_schedule": {
        "name": "view_schedule",
        "description": "Get the hackathon schedule, events, workshops, and important times",
        "parameters": {
            "type": "object",
            "properties": {
                "day": {"type": "string", "description": "Specific day (optional, e.g., 'Saturday', 'Sunday')"}
            },
            "required": []
        }
    },
    "faq_query": {
        "name": "faq_query",
        "description": "Search the FAQ for answers to common questions",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "The question to search for"}
            },
            "required": ["question"]
        }
    },
    # Participant tools
    "ideation_help": {
        "name": "ideation_help",
        "description": "Get project ideation help and suggestions based on interests and track",
        "parameters": {
            "type": "object",
            "properties": {
                "interests": {"type": "array", "items": {"type": "string"}, "description": "List of interests/technologies"},
                "track_id": {"type": "string", "description": "Specific track to focus on (optional)"}
            },
            "required": ["interests"]
        }
    },
    "submission_guidance": {
        "name": "submission_guidance",
        "description": "Get help with submission requirements, deadlines, and what to include",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Specific submission topic (e.g., 'demo video', 'devpost', 'github')"}
            },
            "required": []
        }
    },
    "view_own_submission_status": {
        "name": "view_own_submission_status",
        "description": "View the status of your team's submission",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    # Judge tools
    "judging_guidelines": {
        "name": "judging_guidelines",
        "description": "Get detailed judging criteria and guidelines for a track",
        "parameters": {
            "type": "object",
            "properties": {
                "track_id": {"type": "string", "description": "Specific track ID"}
            },
            "required": []
        }
    },
    "view_assigned_submissions": {
        "name": "view_assigned_submissions",
        "description": "List all submissions assigned to you for judging",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    "view_submission_details": {
        "name": "view_submission_details",
        "description": "Get detailed information about a specific submission",
        "parameters": {
            "type": "object",
            "properties": {
                "submission_id": {"type": "string", "description": "The submission ID"}
            },
            "required": ["submission_id"]
        }
    },
    # Organizer tools
    "participant_search": {
        "name": "participant_search",
        "description": "Search participants by name, email, school, or team",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        }
    },
    "submission_analytics": {
        "name": "submission_analytics",
        "description": "Get analytics and statistics about submissions",
        "parameters": {
            "type": "object",
            "properties": {
                "track_id": {"type": "string", "description": "Filter by specific track (optional)"}
            },
            "required": []
        }
    },
    "admin_stats": {
        "name": "admin_stats",
        "description": "Get overall hackathon statistics: registrations, check-ins, teams, etc.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    "check_in_status": {
        "name": "check_in_status",
        "description": "Get real-time check-in statistics and status",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    "judging_progress": {
        "name": "judging_progress",
        "description": "Get judging progress and completion rates",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    "modify_faq": {
        "name": "modify_faq",
        "description": "Add or update FAQ entries (will update assistant knowledge)",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "FAQ question"},
                "answer": {"type": "string", "description": "FAQ answer"}
            },
            "required": ["question", "answer"]
        }
    },
}

# Role-based tool permissions
ROLE_TOOLS: Dict[UserRole, Set[str]] = {
    UserRole.PARTICIPANT: {
        "query_hackathon_info",
        "get_tracks",
        "view_schedule",
        "faq_query",
        "ideation_help",
        "submission_guidance",
        "view_own_submission_status",
    },
    UserRole.JUDGE: {
        "query_hackathon_info",
        "get_tracks",
        "view_schedule",
        "faq_query",
        "judging_guidelines",
        "view_assigned_submissions",
        "view_submission_details",
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
    },
}


def get_tools_for_role(role: str) -> List[Dict]:
    """Get tool definitions available to a role."""
    try:
        user_role = UserRole(role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {role}")

    allowed_tools = ROLE_TOOLS.get(user_role, set())
    return [TOOL_DEFINITIONS[tool] for tool in allowed_tools if tool in TOOL_DEFINITIONS]


def can_use_tool(role: str, tool_name: str) -> bool:
    """Check if a role can use a specific tool."""
    try:
        user_role = UserRole(role)
    except ValueError:
        return False

    return tool_name in ROLE_TOOLS.get(user_role, set())


def get_all_tools() -> List[str]:
    """Get all available tool names."""
    return list(TOOL_DEFINITIONS.keys())


def get_tool_definition(tool_name: str) -> Optional[Dict]:
    """Get definition for a specific tool."""
    return TOOL_DEFINITIONS.get(tool_name)
