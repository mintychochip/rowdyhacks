"""Tests for assistant tool executor."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.tools import ToolExecutor
from app.models import Hackathon, User


@pytest.fixture
def mock_db_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_user():
    u = MagicMock(spec=User)
    u.id = str(uuid4())
    u.role = "participant"
    u.name = "Test User"
    u.email = "test@example.com"
    return u


@pytest.fixture
def mock_hackathon():
    h = MagicMock(spec=Hackathon)
    h.id = uuid4()
    h.name = "HackTest"
    h.start_date = "2025-01-01"
    h.end_date = "2025-01-02"
    h.venue = "Room 101"
    h.address = "123 Main St"
    h.wifi_ssid = "HackWifi"
    h.wifi_password = "secret"
    h.parking_info = "Lot A"
    h.discord_invite_url = "https://discord.gg/test"
    h.devpost_url = "https://devpost.com/test"
    return h


@pytest.fixture
def executor(mock_db_session, mock_user, mock_hackathon):
    return ToolExecutor(mock_db_session, mock_user, mock_hackathon)


@pytest.mark.asyncio
class TestExecute:
    async def test_dispatches_known_tool(self, executor):
        result = await executor.execute("query_hackathon_info", {"query": "wifi"})
        assert "hackathon" in result

    async def test_raises_on_unknown_tool(self, executor):
        with pytest.raises(ValueError, match="Unknown tool"):
            await executor.execute("nonexistent_tool", {})


@pytest.mark.asyncio
class TestQueryHackathonInfo:
    async def test_returns_info(self, executor, mock_hackathon):
        result = await executor.tool_query_hackathon_info("wifi")
        assert result["hackathon"]["name"] == mock_hackathon.name

    async def test_no_hackathon(self, mock_db_session, mock_user):
        exec_ = ToolExecutor(mock_db_session, mock_user, None)
        result = await exec_.tool_query_hackathon_info("wifi")
        assert "error" in result


@pytest.mark.asyncio
class TestGetTracks:
    async def test_returns_tracks(self, executor, mock_db_session):
        from app.models import Track

        track = MagicMock(spec=Track)
        track.id = uuid4()
        track.name = "AI"
        track.description = "AI track"
        track.criteria = "Innovation"
        track.resources = None
        track.prize = "$100"
        track.color = "#000"

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [track]
        mock_db_session.execute.return_value = result_mock

        result = await executor.tool_get_tracks()
        assert len(result) == 1
        assert result[0]["name"] == "AI"

    async def test_no_hackathon(self, mock_db_session, mock_user):
        exec_ = ToolExecutor(mock_db_session, mock_user, None)
        result = await exec_.tool_get_tracks()
        assert "error" in result


@pytest.mark.asyncio
class TestViewSchedule:
    async def test_returns_schedule(self, executor, mock_hackathon):
        result = await executor.tool_view_schedule()
        assert result["hackathon_name"] == mock_hackathon.name

    async def test_no_hackathon(self, mock_db_session, mock_user):
        exec_ = ToolExecutor(mock_db_session, mock_user, None)
        result = await exec_.tool_view_schedule("Saturday")
        assert "error" in result


@pytest.mark.asyncio
class TestFaqQuery:
    async def test_returns_matches(self, executor):
        with (
            patch("app.assistant.embedder.embedder.embed_text", return_value=[0.1] * 384),
            patch(
                "app.assistant.vector_store.vector_store.search_documents",
                new_callable=AsyncMock,
                return_value=[{"metadata": {"question": "Q1"}, "content": "A1"}],
            ) as mock_search,
        ):
            result = await executor.tool_faq_query("What to bring?")
            assert len(result["matches"]) == 1
            mock_search.assert_awaited_once()

    async def test_no_results(self, executor):
        with (
            patch("app.assistant.embedder.embedder.embed_text", return_value=[0.1] * 384),
            patch("app.assistant.vector_store.vector_store.search_documents", new_callable=AsyncMock, return_value=[]),
        ):
            result = await executor.tool_faq_query("zzz")
            assert result["matches"] == []


@pytest.mark.asyncio
class TestIdeationHelp:
    async def test_returns_suggestions(self, executor):
        result = await executor.tool_ideation_help(["python", "ai"])
        assert "suggestions" in result
        assert result["interests"] == ["python", "ai"]

    async def test_with_track(self, executor, mock_db_session):
        from app.models import Track

        track = MagicMock(spec=Track)
        track.name = "AI Track"
        track.criteria = "Innovation"

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = track
        mock_db_session.execute.return_value = result_mock

        result = await executor.tool_ideation_help(["python"], track_id=str(uuid4()))
        assert "track_focus" in result


@pytest.mark.asyncio
class TestSubmissionGuidance:
    async def test_general_guidance(self, executor):
        result = await executor.tool_submission_guidance()
        assert "general_requirements" in result

    async def test_video_focus(self, executor):
        result = await executor.tool_submission_guidance("demo video")
        assert result["focus"]["topic"] == "demo video"

    async def test_devpost_focus(self, executor):
        result = await executor.tool_submission_guidance("devpost")
        assert result["focus"]["topic"] == "devpost"

    async def test_github_focus(self, executor):
        result = await executor.tool_submission_guidance("github")
        assert result["focus"]["topic"] == "GitHub"


@pytest.mark.asyncio
class TestViewOwnSubmissionStatus:
    async def test_returns_submissions(self, executor, mock_db_session):
        from app.models import Submission

        sub = MagicMock(spec=Submission)
        sub.id = uuid4()
        sub.devpost_url = "https://devpost.com/x"
        sub.github_url = "https://github.com/x"
        sub.project_name = "Proj"
        sub.status = "completed"
        sub.risk_score = 10
        sub.submitted_at = None

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [sub]
        mock_db_session.execute.return_value = result_mock

        result = await executor.tool_view_own_submission_status()
        assert "submissions" in result
        assert len(result["submissions"]) == 1

    async def test_no_submissions(self, executor, mock_db_session):
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = result_mock

        result = await executor.tool_view_own_submission_status()
        assert "No submissions found" in result["status"]


@pytest.mark.asyncio
class TestJudgingGuidelines:
    async def test_no_hackathon(self, mock_db_session, mock_user):
        exec_ = ToolExecutor(mock_db_session, mock_user, None)
        result = await exec_.tool_judging_guidelines()
        assert "error" in result

    async def test_no_session(self, executor, mock_db_session):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = result_mock
        result = await executor.tool_judging_guidelines()
        assert "error" in result


@pytest.mark.asyncio
class TestViewAssignedSubmissions:
    async def test_returns_assignments(self, executor, mock_db_session):
        from app.models import JudgeAssignment, Submission

        ja = MagicMock(spec=JudgeAssignment)
        ja.id = uuid4()
        ja.status = "pending"
        ja.scores_submitted = False

        sub = MagicMock(spec=Submission)
        sub.id = uuid4()
        sub.project_name = "Proj"
        sub.devpost_url = "https://devpost.com/x"

        result_mock = MagicMock()
        result_mock.all.return_value = [(ja, sub)]
        mock_db_session.execute.return_value = result_mock

        result = await executor.tool_view_assigned_submissions()
        assert len(result) == 1
        assert result[0]["project_name"] == "Proj"

    async def test_no_hackathon(self, mock_db_session, mock_user):
        exec_ = ToolExecutor(mock_db_session, mock_user, None)
        result = await exec_.tool_view_assigned_submissions()
        assert "error" in result


@pytest.mark.asyncio
class TestViewSubmissionDetails:
    async def test_returns_details(self, executor, mock_db_session):
        from app.models import Submission

        sub = MagicMock(spec=Submission)
        sub.id = uuid4()
        sub.project_name = "Proj"
        sub.project_description = "Desc"
        sub.devpost_url = "https://devpost.com/x"
        sub.github_url = "https://github.com/x"
        sub.demo_url = "https://demo.com"
        sub.submitter_id = uuid4()
        sub.status = "completed"
        sub.risk_score = 5
        sub.verdict = "clean"

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = sub
        mock_db_session.execute.return_value = result_mock

        result = await executor.tool_view_submission_details(str(sub.id))
        assert result["project_name"] == "Proj"

    async def test_not_found(self, executor, mock_db_session):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = result_mock

        result = await executor.tool_view_submission_details("missing")
        assert "error" in result


@pytest.mark.asyncio
class TestParticipantSearch:
    async def test_search_results(self, executor, mock_db_session):
        from app.models import Registration, User

        user = MagicMock(spec=User)
        user.id = uuid4()
        user.name = "Alice"
        user.email = "alice@example.com"

        reg = MagicMock(spec=Registration)
        reg.school = "MIT"
        reg.team_name = "Team A"
        reg.status = "accepted"

        result_mock = MagicMock()
        result_mock.all.return_value = [(user, reg)]
        mock_db_session.execute.return_value = result_mock

        result = await executor.tool_participant_search("Alice")
        assert len(result) == 1
        assert result[0]["name"] == "Alice"

    async def test_no_hackathon(self, mock_db_session, mock_user):
        exec_ = ToolExecutor(mock_db_session, mock_user, None)
        result = await exec_.tool_participant_search("Alice")
        assert "error" in result


@pytest.mark.asyncio
class TestSubmissionAnalytics:
    async def test_returns_analytics(self, executor, mock_db_session):
        result_mock = MagicMock()
        result_mock.scalar.return_value = 10
        mock_db_session.execute.return_value = result_mock

        result = await executor.tool_submission_analytics()
        assert result["total_submissions"] == 10

    async def test_no_hackathon(self, mock_db_session, mock_user):
        exec_ = ToolExecutor(mock_db_session, mock_user, None)
        result = await exec_.tool_submission_analytics()
        assert "error" in result


@pytest.mark.asyncio
class TestAdminStats:
    async def test_returns_stats(self, executor, mock_db_session):
        result_mock = MagicMock()
        result_mock.all.return_value = [("accepted", 5), ("checked_in", 3)]
        mock_db_session.execute.return_value = result_mock

        result = await executor.tool_admin_stats()
        assert "registrations" in result
        assert "check_in_rate" in result

    async def test_no_hackathon(self, mock_db_session, mock_user):
        exec_ = ToolExecutor(mock_db_session, mock_user, None)
        result = await exec_.tool_admin_stats()
        assert "error" in result


@pytest.mark.asyncio
class TestCheckInStatus:
    async def test_returns_status(self, executor, mock_db_session):
        result_mock = MagicMock()
        result_mock.all.return_value = [("checked_in", 10), ("accepted", 5)]
        mock_db_session.execute.return_value = result_mock

        result = await executor.tool_check_in_status()
        assert result["checked_in"] == 10
        assert result["total_eligible"] == 15

    async def test_no_hackathon(self, mock_db_session, mock_user):
        exec_ = ToolExecutor(mock_db_session, mock_user, None)
        result = await exec_.tool_check_in_status()
        assert "error" in result


@pytest.mark.asyncio
class TestJudgingProgress:
    async def test_returns_progress(self, executor, mock_db_session):
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result_mock = MagicMock()
            result_mock.scalar.return_value = 20 if call_count <= 2 else 5
            return result_mock

        mock_db_session.execute.side_effect = side_effect

        result = await executor.tool_judging_progress()
        assert result["total_assignments"] == 20
        assert "completion_rate" in result

    async def test_no_hackathon(self, mock_db_session, mock_user):
        exec_ = ToolExecutor(mock_db_session, mock_user, None)
        result = await exec_.tool_judging_progress()
        assert "error" in result


@pytest.mark.asyncio
class TestModifyFaq:
    async def test_returns_success(self, executor):
        result = await executor.tool_modify_faq("Q?", "A.")
        assert result["success"] is True
        assert "Q?" in result["message"]


@pytest.mark.asyncio
class TestQuerySitePages:
    async def test_returns_pages(self, executor):
        with (
            patch("app.assistant.embedder.embedder.embed_text", return_value=[0.1] * 384),
            patch(
                "app.assistant.vector_store.vector_store.search_documents",
                new_callable=AsyncMock,
                return_value=[{"title": "Home", "score": 0.9, "metadata": {"path": "/", "description": "Landing"}}],
            ) as mock_search,
        ):
            result = await executor.tool_query_site_pages("home page")
            assert len(result["pages"]) == 1
            assert result["pages"][0]["title"] == "Home"

    async def test_no_results(self, executor):
        with (
            patch("app.assistant.embedder.embedder.embed_text", return_value=[0.1] * 384),
            patch("app.assistant.vector_store.vector_store.search_documents", new_callable=AsyncMock, return_value=[]),
        ):
            result = await executor.tool_query_site_pages("zzz")
            assert result["pages"] == []
