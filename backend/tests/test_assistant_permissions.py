"""Tests for assistant permission system."""

import pytest
from fastapi import HTTPException

from app.assistant.permissions import (
    TOOL_DEFINITIONS,
    UserRole,
    can_use_tool,
    get_all_tools,
    get_tool_definition,
    get_tools_for_role,
    tools_to_flat_format,
)


class TestUserRole:
    def test_role_values(self):
        assert UserRole.PARTICIPANT == "participant"
        assert UserRole.JUDGE == "judge"
        assert UserRole.ORGANIZER == "organizer"


class TestGetToolsForRole:
    def test_participant_tools(self):
        tools = get_tools_for_role("participant")
        assert isinstance(tools, list)
        names = [t["function"]["name"] for t in tools]
        assert "query_hackathon_info" in names
        assert "ideation_help" in names
        assert "participant_search" not in names

    def test_judge_tools(self):
        tools = get_tools_for_role("judge")
        names = [t["function"]["name"] for t in tools]
        assert "judging_guidelines" in names
        assert "view_assigned_submissions" in names
        assert "participant_search" not in names

    def test_organizer_tools(self):
        tools = get_tools_for_role("organizer")
        names = [t["function"]["name"] for t in tools]
        assert "participant_search" in names
        assert "admin_stats" in names
        assert "modify_faq" in names

    def test_invalid_role_raises(self):
        with pytest.raises(HTTPException) as exc:
            get_tools_for_role("superuser")
        assert exc.value.status_code == 400

    def test_openai_format_structure(self):
        tools = get_tools_for_role("participant")
        for tool in tools:
            assert tool["type"] == "function"
            assert "name" in tool["function"]
            assert "description" in tool["function"]
            assert "parameters" in tool["function"]


class TestCanUseTool:
    def test_participant_can_use_common_tool(self):
        assert can_use_tool("participant", "faq_query") is True

    def test_participant_cannot_use_organizer_tool(self):
        assert can_use_tool("participant", "admin_stats") is False

    def test_judge_can_use_judging_tool(self):
        assert can_use_tool("judge", "view_submission_details") is True

    def test_organizer_can_use_all_tools(self):
        assert can_use_tool("organizer", "modify_faq") is True
        assert can_use_tool("organizer", "ideation_help") is True

    def test_invalid_role_returns_false(self):
        assert can_use_tool("unknown", "faq_query") is False

    def test_invalid_tool_returns_false(self):
        assert can_use_tool("participant", "nonexistent_tool") is False


class TestGetAllTools:
    def test_returns_all_registered_tools(self):
        tools = get_all_tools()
        assert isinstance(tools, list)
        assert len(tools) == len(TOOL_DEFINITIONS)
        assert "query_hackathon_info" in tools
        assert "modify_faq" in tools


class TestGetToolDefinition:
    def test_returns_definition_for_existing_tool(self):
        definition = get_tool_definition("faq_query")
        assert definition is not None
        assert definition["name"] == "faq_query"

    def test_returns_none_for_missing_tool(self):
        assert get_tool_definition("nonexistent") is None


class TestToolsToFlatFormat:
    def test_unwraps_openai_format(self):
        openai_tools = [
            {"type": "function", "function": {"name": "a", "description": "d"}},
        ]
        flat = tools_to_flat_format(openai_tools)
        assert flat == [{"name": "a", "description": "d"}]

    def test_keeps_flat_tools_as_is(self):
        flat_tools = [{"name": "a", "description": "d"}]
        result = tools_to_flat_format(flat_tools)
        assert result == flat_tools

    def test_mixed_tools(self):
        mixed = [
            {"type": "function", "function": {"name": "a"}},
            {"name": "b"},
        ]
        result = tools_to_flat_format(mixed)
        assert result == [{"name": "a"}, {"name": "b"}]
