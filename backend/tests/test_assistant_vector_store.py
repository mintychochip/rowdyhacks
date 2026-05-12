"""Tests for assistant Qdrant vector store wrapper."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.assistant.vector_store import (
    DOCUMENTS_COLLECTION,
    GLOBAL_HACKATHON_ID,
    MESSAGES_COLLECTION,
    VECTOR_DIM,
    VectorStore,
)


@pytest.fixture(autouse=True)
def reset_vector_store():
    """Reset the vector store singleton between tests."""
    VectorStore._instance = None
    VectorStore._client = None
    yield
    VectorStore._instance = None
    VectorStore._client = None


@pytest.fixture
def mock_qdrant_client():
    client = AsyncMock()
    return client


@pytest.fixture
def vs(mock_qdrant_client):
    store = VectorStore()
    store._client = mock_qdrant_client
    return store


@pytest.mark.asyncio
class TestInitialize:
    async def test_creates_missing_collections(self, vs, mock_qdrant_client):
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])
        mock_qdrant_client.create_collection.return_value = None

        await vs.initialize()

        assert mock_qdrant_client.create_collection.call_count == 2
        calls = [c.kwargs["collection_name"] for c in mock_qdrant_client.create_collection.call_args_list]
        assert DOCUMENTS_COLLECTION in calls
        assert MESSAGES_COLLECTION in calls

    async def test_skips_existing_collections(self, vs, mock_qdrant_client):
        col1 = MagicMock()
        col1.name = DOCUMENTS_COLLECTION
        col2 = MagicMock()
        col2.name = MESSAGES_COLLECTION
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[col1, col2])
        mock_qdrant_client.get_collection.return_value = MagicMock(status="green")

        await vs.initialize()

        mock_qdrant_client.create_collection.assert_not_called()

    async def test_warns_on_non_green_status(self, vs, mock_qdrant_client):
        col1 = MagicMock()
        col1.name = DOCUMENTS_COLLECTION
        col2 = MagicMock()
        col2.name = MESSAGES_COLLECTION
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[col1, col2])
        mock_qdrant_client.get_collection.return_value = MagicMock(status="yellow")

        await vs.initialize()
        mock_qdrant_client.create_collection.assert_not_called()

    async def test_raises_on_qdrant_error(self, vs, mock_qdrant_client):
        mock_qdrant_client.get_collections.side_effect = Exception("connection refused")
        with pytest.raises(Exception, match="connection refused"):
            await vs.initialize()


@pytest.mark.asyncio
class TestIndexDocument:
    async def test_upserts_point(self, vs, mock_qdrant_client):
        await vs.index_document(
            doc_id="doc-1",
            embedding=[0.1] * VECTOR_DIM,
            content="hello",
            doc_type="faq",
            title="FAQ",
            hackathon_id="hack-1",
            metadata={"q": "q1"},
            role_access=["participant"],
        )
        mock_qdrant_client.upsert.assert_awaited_once()
        call = mock_qdrant_client.upsert.call_args
        assert call.kwargs["collection_name"] == DOCUMENTS_COLLECTION

    async def test_defaults_global_hackathon(self, vs, mock_qdrant_client):
        await vs.index_document(
            doc_id="doc-1",
            embedding=[0.1] * VECTOR_DIM,
            content="hello",
            doc_type="site_page",
            title="Home",
        )
        call = mock_qdrant_client.upsert.call_args
        point = call.kwargs["points"][0]
        assert point.payload["hackathon_id"] == GLOBAL_HACKATHON_ID
        assert point.payload["role_access"] == ["participant", "judge", "organizer"]


@pytest.mark.asyncio
class TestSearchDocuments:
    async def test_search_without_filters(self, vs, mock_qdrant_client):
        mock_qdrant_client.search.return_value = []
        result = await vs.search_documents(query_embedding=[0.1] * VECTOR_DIM)
        assert result == []
        mock_qdrant_client.search.assert_awaited_once()

    async def test_search_with_filters(self, vs, mock_qdrant_client):
        mock_point = MagicMock()
        mock_point.id = "p1"
        mock_point.version = 1
        mock_point.score = 0.85
        mock_point.payload = {"content": "c1", "title": "t1", "doc_type": "faq", "metadata": {}}
        mock_qdrant_client.search.return_value = [mock_point]

        result = await vs.search_documents(
            query_embedding=[0.1] * VECTOR_DIM,
            hackathon_id="hack-1",
            doc_type="faq",
            role="participant",
            limit=3,
            score_threshold=0.7,
        )
        assert len(result) == 1
        assert result[0]["id"] == "p1"
        assert result[0]["score"] == 0.85


@pytest.mark.asyncio
class TestDeleteByHackathon:
    async def test_deletes_points(self, vs, mock_qdrant_client):
        from qdrant_client.http.models import Record

        mock_qdrant_client.scroll.return_value = (
            [Record(id="a", payload={}), Record(id="b", payload={})],
            None,
        )
        count = await vs.delete_by_hackathon("hack-1")
        assert count == 2
        mock_qdrant_client.delete.assert_awaited_once()

    async def test_returns_zero_when_no_points(self, vs, mock_qdrant_client):
        mock_qdrant_client.scroll.return_value = ([], None)
        count = await vs.delete_by_hackathon("hack-1")
        assert count == 0
        mock_qdrant_client.delete.assert_not_called()


@pytest.mark.asyncio
class TestDeleteDocument:
    async def test_deletes_single_point(self, vs, mock_qdrant_client):
        await vs.delete_document("doc-1")
        mock_qdrant_client.delete.assert_awaited_once()


@pytest.mark.asyncio
class TestIndexMessage:
    async def test_upserts_message(self, vs, mock_qdrant_client):
        await vs.index_message("msg-1", "conv-1", [0.1] * VECTOR_DIM, "hello", "user")
        call = mock_qdrant_client.upsert.call_args
        assert call.kwargs["collection_name"] == MESSAGES_COLLECTION


@pytest.mark.asyncio
class TestSearchMessages:
    async def test_search_messages(self, vs, mock_qdrant_client):
        from qdrant_client.http.models import ScoredPoint

        mock_qdrant_client.search.return_value = [
            ScoredPoint(
                id="m1",
                version=1,
                score=0.9,
                payload={"content": "hi", "role": "user"},
            )
        ]
        result = await vs.search_messages([0.1] * VECTOR_DIM, conversation_id="conv-1")
        assert len(result) == 1
        assert result[0]["role"] == "user"


@pytest.mark.asyncio
class TestDeleteConversationMessages:
    async def test_deletes_conversation_messages(self, vs, mock_qdrant_client):
        from qdrant_client.http.models import Record

        mock_qdrant_client.scroll.return_value = ([Record(id="m1", payload={})], None)
        await vs.delete_conversation_messages("conv-1")
        mock_qdrant_client.delete.assert_awaited_once()

    async def test_no_messages_no_delete(self, vs, mock_qdrant_client):
        mock_qdrant_client.scroll.return_value = ([], None)
        await vs.delete_conversation_messages("conv-1")
        mock_qdrant_client.delete.assert_not_called()
