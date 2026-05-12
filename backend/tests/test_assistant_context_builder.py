"""Tests for assistant context builder."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.context_builder import (
    ContextBuilder,
    build_plan_generation_prompt,
    build_project_generation_prompt,
    detect_build_intent,
)
from app.models import Hackathon, Track, User


class TestDetectBuildIntent:
    def test_direct_build_statements(self):
        assert detect_build_intent("I want to build a web app")[0] is True
        assert detect_build_intent("I'm building a Discord bot")[0] is True

    def test_project_type_indicators(self):
        assert detect_build_intent("Let's make a mobile app")[0] is True
        assert detect_build_intent("Using React and Node.js")[0] is True

    def test_no_build_intent(self):
        assert detect_build_intent("What time is lunch?") == (False, 0.0)

    def test_confidence_levels(self):
        assert detect_build_intent("I want to build a web app using React")[1] >= 0.6


class TestBuildPlanGenerationPrompt:
    def test_basic_prompt(self):
        prompt = build_plan_generation_prompt("A todo app")
        assert "AI hackathon mentor" in prompt
        assert "todo app" in prompt
        assert "MVP Tasks" in prompt

    def test_prompt_with_hackathon(self):
        prompt = build_plan_generation_prompt("A game", hackathon_name="HackFest")
        assert "HackFest" in prompt

    def test_prompt_with_tracks(self):
        tracks = [{"name": "AI", "description": "Machine learning"}]
        prompt = build_plan_generation_prompt("An AI app", tracks=tracks)
        assert "AI" in prompt


class TestBuildProjectGenerationPrompt:
    def test_web_project(self):
        plan = {"name": "MyApp", "techStack": ["React"], "tasks": [{"description": "Setup"}]}
        prompt = build_project_generation_prompt(plan, "web")
        assert "index.html" in prompt
        assert "style.css" in prompt

    def test_python_project(self):
        plan = {"name": "MyApp", "techStack": ["Flask"], "tasks": []}
        prompt = build_project_generation_prompt(plan, "python")
        assert "app.py" in prompt
        assert "requirements.txt" in prompt

    def test_fullstack_project(self):
        plan = {"name": "MyApp", "techStack": ["Flask", "React"], "tasks": []}
        prompt = build_project_generation_prompt(plan, "fullstack")
        assert "app.py" in prompt
        assert "index.html" in prompt

    def test_unknown_project_type(self):
        plan = {"name": "X", "techStack": [], "tasks": []}
        prompt = build_project_generation_prompt(plan, "other")
        assert "README.md" in prompt


@pytest.fixture
def mock_db_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_user():
    u = MagicMock(spec=User)
    u.role = "participant"
    u.id = str(uuid4())
    return u


@pytest.fixture
def mock_hackathon():
    h = MagicMock(spec=Hackathon)
    h.id = uuid4()
    h.name = "HackTest"
    h.start_date = "2025-01-01"
    h.end_date = "2025-01-02"
    return h


@pytest.mark.asyncio
class TestBuildSystemPrompt:
    async def test_builds_basic_prompt(self, mock_db_session, mock_user, mock_hackathon):
        with (
            patch("app.assistant.context_builder.get_tools_for_role", return_value=[]),
            patch.object(ContextBuilder, "_get_tracks", new_callable=AsyncMock, return_value=[]),
            patch.object(ContextBuilder, "_get_relevant_documents", new_callable=AsyncMock, return_value=[]),
        ):
            builder = ContextBuilder(mock_db_session)
            prompt = await builder.build_system_prompt(mock_user, mock_hackathon, "hello")
            assert "AI assistant" in prompt
            assert "participant" in prompt
            assert "HackTest" in prompt

    async def test_includes_tools(self, mock_db_session, mock_user, mock_hackathon):
        tools = [{"type": "function", "function": {"name": "faq_query", "description": "Search FAQ"}}]
        with (
            patch("app.assistant.context_builder.get_tools_for_role", return_value=tools),
            patch.object(ContextBuilder, "_get_tracks", new_callable=AsyncMock, return_value=[]),
            patch.object(ContextBuilder, "_get_relevant_documents", new_callable=AsyncMock, return_value=[]),
        ):
            builder = ContextBuilder(mock_db_session)
            prompt = await builder.build_system_prompt(mock_user, mock_hackathon)
            assert "faq_query" in prompt
            assert "Search FAQ" in prompt

    async def test_includes_tracks(self, mock_db_session, mock_user, mock_hackathon):
        tracks = [{"name": "AI", "description": "Machine learning track for cool stuff"}]
        with (
            patch("app.assistant.context_builder.get_tools_for_role", return_value=[]),
            patch.object(ContextBuilder, "_get_tracks", new_callable=AsyncMock, return_value=tracks),
            patch.object(ContextBuilder, "_get_relevant_documents", new_callable=AsyncMock, return_value=[]),
        ):
            builder = ContextBuilder(mock_db_session)
            prompt = await builder.build_system_prompt(mock_user, mock_hackathon)
            assert "AI" in prompt

    async def test_includes_relevant_docs(self, mock_db_session, mock_user, mock_hackathon):
        docs = [{"doc_type": "faq", "title": "Q1", "content": "Answer here"}]
        with (
            patch("app.assistant.context_builder.get_tools_for_role", return_value=[]),
            patch.object(ContextBuilder, "_get_tracks", new_callable=AsyncMock, return_value=[]),
            patch.object(ContextBuilder, "_get_relevant_documents", new_callable=AsyncMock, return_value=docs),
        ):
            builder = ContextBuilder(mock_db_session)
            prompt = await builder.build_system_prompt(mock_user, mock_hackathon, "wifi password")
            assert "faq" in prompt
            assert "Q1" in prompt

    async def test_no_hackathon_context(self, mock_db_session, mock_user):
        with patch("app.assistant.context_builder.get_tools_for_role", return_value=[]):
            builder = ContextBuilder(mock_db_session)
            prompt = await builder.build_system_prompt(mock_user)
            assert "Hackathon context" not in prompt or "Current hackathon context" not in prompt


@pytest.mark.asyncio
class TestBuildConversationHistory:
    async def test_fetch_messages(self, mock_db_session):
        from app.models_assistant import AssistantMessage, ConversationRole

        msg = MagicMock(spec=AssistantMessage)
        msg.role = ConversationRole.USER
        msg.content = "hi"

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [msg]
        mock_db_session.execute.return_value = result_mock

        builder = ContextBuilder(mock_db_session)
        history = await builder.build_conversation_history(str(uuid4()), limit=10)
        assert len(history) == 1
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "hi"


@pytest.mark.asyncio
class TestGetTracks:
    async def test_get_tracks(self, mock_db_session):

        track = MagicMock(spec=Track)
        track.id = uuid4()
        track.name = "Web"
        track.description = "Web dev"
        track.prize = "$100"

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [track]
        mock_db_session.execute.return_value = result_mock

        builder = ContextBuilder(mock_db_session)
        tracks = await builder._get_tracks(str(uuid4()))
        assert len(tracks) == 1
        assert tracks[0]["name"] == "Web"


@pytest.mark.asyncio
class TestGetRelevantDocuments:
    async def test_returns_documents(self, mock_db_session):
        with (
            patch("app.assistant.context_builder.embedder.embed_text", return_value=[0.1] * 384),
            patch(
                "app.assistant.context_builder.vector_store.search_documents",
                new_callable=AsyncMock,
                return_value=[{"id": "d1"}],
            ) as mock_search,
        ):
            builder = ContextBuilder(mock_db_session)
            docs = await builder._get_relevant_documents("query", "hack-1", "participant")
            assert len(docs) == 1
            mock_search.assert_awaited_once()

    async def test_returns_empty_on_error(self, mock_db_session):
        with patch("app.assistant.context_builder.embedder.embed_text", side_effect=Exception("boom")):
            builder = ContextBuilder(mock_db_session)
            docs = await builder._get_relevant_documents("query", "hack-1", "participant")
            assert docs == []


@pytest.mark.asyncio
class TestGetUserActiveHackathons:
    async def test_returns_hackathons(self, mock_db_session):
        hack = MagicMock(spec=Hackathon)
        hack.id = uuid4()
        hack.name = "Hack"
        hack.end_date = "2099-01-01"

        reg = MagicMock()
        reg.status = "accepted"

        result_mock = MagicMock()
        result_mock.all.return_value = [(reg, hack)]
        mock_db_session.execute.return_value = result_mock

        builder = ContextBuilder(mock_db_session)
        hacks = await builder.get_user_active_hackathons("user-1")
        assert len(hacks) == 1
        assert hacks[0]["name"] == "Hack"
