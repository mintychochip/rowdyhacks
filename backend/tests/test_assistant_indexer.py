"""Tests for assistant document indexer."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.indexer import DocumentIndexer, initialize_vector_store
from app.models import Hackathon
from app.models_assistant import AssistantDocument


@pytest.fixture
def mock_hackathon():
    h = MagicMock(spec=Hackathon)
    h.id = uuid4()
    h.name = "TestHack"
    h.start_date = "2025-01-01"
    h.end_date = "2025-01-02"
    h.application_deadline = None
    h.venue_address = None
    h.wifi_ssid = None
    h.wifi_password = None
    h.parking_info = None
    h.description = "A test hackathon"
    h.discord_invite_url = None
    h.devpost_url = None
    h.max_participants = None
    return h


@pytest.fixture
def mock_db_session():
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture(autouse=True)
def reset_vector_store():
    from app.assistant.vector_store import VectorStore

    VectorStore._instance = None
    VectorStore._client = None
    yield
    VectorStore._instance = None
    VectorStore._client = None


@pytest.mark.asyncio
class TestIndexHackathon:
    async def test_index_hackathon_info_new(self, mock_db_session, mock_hackathon):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = result_mock

        with (
            patch("app.assistant.indexer.embedder.embed_text", return_value=[0.1] * 384) as mock_embed,
            patch("app.assistant.indexer.vector_store.index_document", new_callable=AsyncMock) as mock_index,
        ):
            indexer = DocumentIndexer(mock_db_session)
            count = await indexer.index_hackathon(mock_hackathon)
            assert count >= 1
            assert mock_embed.call_count >= 1
            assert mock_index.await_count >= 1
            mock_db_session.commit.assert_awaited()

    async def test_index_hackathon_info_existing(self, mock_db_session, mock_hackathon):
        existing = MagicMock(spec=AssistantDocument)
        existing.version = 1
        existing.doc_metadata = {}
        existing.qdrant_id = str(uuid4())

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = existing
        mock_db_session.execute.return_value = result_mock

        with (
            patch("app.assistant.indexer.embedder.embed_text", return_value=[0.1] * 384),
            patch("app.assistant.indexer.vector_store.index_document", new_callable=AsyncMock) as mock_index,
        ):
            indexer = DocumentIndexer(mock_db_session)
            count = await indexer._index_hackathon_info(mock_hackathon)
            assert count == 1
            assert existing.version == 2
            mock_index.assert_awaited_once()


@pytest.mark.asyncio
class TestIndexTracks:
    async def test_index_tracks(self, mock_db_session, mock_hackathon):
        from app.models import Track

        track = MagicMock(spec=Track)
        track.id = uuid4()
        track.name = "AI Track"
        track.description = "ML/AI projects"
        track.criteria = "Innovation"
        track.prize = "$500"
        track.resources = None

        track_result = MagicMock()
        track_result.scalars.return_value.all.return_value = [track]

        doc_result = MagicMock()
        doc_result.scalar_one_or_none.return_value = None

        call_count = 0

        async def side_effect(stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return track_result
            return doc_result

        mock_db_session.execute.side_effect = side_effect

        with (
            patch("app.assistant.indexer.embedder.embed_text", return_value=[0.1] * 384),
            patch("app.assistant.indexer.vector_store.index_document", new_callable=AsyncMock) as mock_index,
        ):
            indexer = DocumentIndexer(mock_db_session)
            count = await indexer._index_tracks(mock_hackathon)
            assert count == 1
            mock_index.assert_awaited_once()


@pytest.mark.asyncio
class TestIndexFaq:
    async def test_index_faq_new(self, mock_db_session, mock_hackathon):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = result_mock

        with (
            patch("app.assistant.indexer.embedder.embed_text", return_value=[0.1] * 384),
            patch("app.assistant.indexer.vector_store.index_document", new_callable=AsyncMock) as mock_index,
        ):
            indexer = DocumentIndexer(mock_db_session)
            count = await indexer._index_faq(mock_hackathon)
            assert count == 4  # default FAQ count
            assert mock_index.call_count == 4

    async def test_index_faq_skips_when_exists(self, mock_db_session, mock_hackathon):
        existing = MagicMock(spec=AssistantDocument)
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = existing
        mock_db_session.execute.return_value = result_mock

        with (
            patch("app.assistant.indexer.embedder.embed_text", return_value=[0.1] * 384),
            patch("app.assistant.indexer.vector_store.index_document", new_callable=AsyncMock) as mock_index,
        ):
            indexer = DocumentIndexer(mock_db_session)
            count = await indexer._index_faq(mock_hackathon)
            assert count == 0
            mock_index.assert_not_called()


@pytest.mark.asyncio
class TestAddFaqEntry:
    async def test_add_faq_entry(self, mock_db_session, mock_hackathon):
        with (
            patch("app.assistant.indexer.embedder.embed_text", return_value=[0.1] * 384),
            patch("app.assistant.indexer.vector_store.index_document", new_callable=AsyncMock) as mock_index,
        ):
            indexer = DocumentIndexer(mock_db_session)
            doc_id = await indexer.add_faq_entry(mock_hackathon, "Q?", "A.")
            assert isinstance(doc_id, str)
            mock_index.assert_awaited_once()
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_awaited()


@pytest.mark.asyncio
class TestDeleteHackathonDocuments:
    async def test_delete_hackathon_documents(self, mock_db_session):
        doc = MagicMock(spec=AssistantDocument)
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [doc]
        mock_db_session.execute.return_value = result_mock

        with patch(
            "app.assistant.indexer.vector_store.delete_by_hackathon", new_callable=AsyncMock, return_value=5
        ) as mock_delete:
            indexer = DocumentIndexer(mock_db_session)
            count = await indexer.delete_hackathon_documents("hack-1")
            assert count == 5
            mock_delete.assert_awaited_once_with("hack-1")
            mock_db_session.delete.assert_awaited_once_with(doc)


@pytest.mark.asyncio
class TestInitializeVectorStore:
    async def test_initialize_success(self):
        with patch("app.assistant.indexer.vector_store.initialize", new_callable=AsyncMock) as mock_init:
            await initialize_vector_store()
            mock_init.assert_awaited_once()

    async def test_initialize_failure_logged(self):
        with patch(
            "app.assistant.indexer.vector_store.initialize", new_callable=AsyncMock, side_effect=Exception("boom")
        ) as mock_init:
            await initialize_vector_store()
            mock_init.assert_awaited_once()
