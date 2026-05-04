"""Qdrant vector store integration for the assistant."""

import logging
from typing import Any, Dict, List, Optional

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    CollectionStatus,
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointIdsList,
    PointStruct,
    VectorParams,
)

from app.config import settings

logger = logging.getLogger(__name__)

# Collection names
DOCUMENTS_COLLECTION = "assistant_documents"
MESSAGES_COLLECTION = "assistant_messages"

# Vector dimensions for all-MiniLM-L6-v2
VECTOR_DIM = 384


class VectorStore:
    """Manages Qdrant vector store for assistant documents and messages."""

    _instance: Optional["VectorStore"] = None
    _client: Optional[AsyncQdrantClient] = None

    def __new__(cls) -> "VectorStore":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def client(self) -> AsyncQdrantClient:
        """Get or create Qdrant client."""
        if self._client is None:
            self._client = AsyncQdrantClient(url=settings.qdrant_url)
        return self._client

    async def initialize(self) -> None:
        """Initialize collections if they don't exist."""
        await self._ensure_collection(DOCUMENTS_COLLECTION)
        await self._ensure_collection(MESSAGES_COLLECTION)
        logger.info("Vector store initialized")

    async def _ensure_collection(self, name: str) -> None:
        """Ensure a collection exists with proper schema."""
        try:
            collections = await self.client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if name not in collection_names:
                await self.client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(
                        size=VECTOR_DIM,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info(f"Created collection: {name}")
            else:
                # Verify collection is ready
                info = await self.client.get_collection(name)
                if info.status != CollectionStatus.GREEN:
                    logger.warning(f"Collection {name} status: {info.status}")
        except Exception as e:
            logger.error(f"Failed to ensure collection {name}: {e}")
            raise

    async def index_document(
        self,
        doc_id: str,
        embedding: List[float],
        content: str,
        hackathon_id: str,
        doc_type: str,
        title: str,
        metadata: Optional[Dict[str, Any]] = None,
        role_access: Optional[List[str]] = None,
    ) -> None:
        """Index a document with its embedding."""
        payload = {
            "content": content,
            "hackathon_id": str(hackathon_id),
            "doc_type": doc_type,
            "title": title,
            "metadata": metadata or {},
            "role_access": role_access or ["participant", "judge", "organizer"],
        }

        point = PointStruct(id=doc_id, vector=embedding, payload=payload)

        await self.client.upsert(
            collection_name=DOCUMENTS_COLLECTION,
            points=[point],
        )

    async def search_documents(
        self,
        query_embedding: List[float],
        hackathon_id: Optional[str] = None,
        doc_type: Optional[str] = None,
        role: Optional[str] = None,
        limit: int = 5,
        score_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """Search documents by similarity with filters."""
        must_conditions = []

        if hackathon_id:
            must_conditions.append(
                FieldCondition(
                    key="hackathon_id",
                    match=MatchValue(value=str(hackathon_id)),
                )
            )

        if doc_type:
            must_conditions.append(
                FieldCondition(
                    key="doc_type",
                    match=MatchValue(value=doc_type),
                )
            )

        if role:
            # Role must be in role_access list
            must_conditions.append(
                FieldCondition(
                    key="role_access",
                    match=MatchValue(value=role),
                )
            )

        search_filter = Filter(must=must_conditions) if must_conditions else None

        results = await self.client.search(
            collection_name=DOCUMENTS_COLLECTION,
            query_vector=query_embedding,
            query_filter=search_filter,
            limit=limit,
            score_threshold=score_threshold,
        )

        return [
            {
                "id": r.id,
                "score": r.score,
                "content": r.payload.get("content", ""),
                "title": r.payload.get("title", ""),
                "doc_type": r.payload.get("doc_type", ""),
                "metadata": r.payload.get("metadata", {}),
            }
            for r in results
        ]

    async def delete_by_hackathon(self, hackathon_id: str) -> int:
        """Delete all documents for a hackathon."""
        filter_ = Filter(
            must=[
                FieldCondition(
                    key="hackathon_id",
                    match=MatchValue(value=str(hackathon_id)),
                )
            ]
        )

        # Get points to delete
        results = await self.client.scroll(
            collection_name=DOCUMENTS_COLLECTION,
            scroll_filter=filter_,
            limit=10000,
        )

        if results[0]:
            point_ids = [p.id for p in results[0]]
            await self.client.delete(
                collection_name=DOCUMENTS_COLLECTION,
                points_selector=PointIdsList(points=point_ids),
            )
            return len(point_ids)

        return 0

    async def delete_document(self, doc_id: str) -> None:
        """Delete a specific document."""
        await self.client.delete(
            collection_name=DOCUMENTS_COLLECTION,
            points_selector=PointIdsList(points=[doc_id]),
        )

    async def index_message(
        self,
        message_id: str,
        conversation_id: str,
        embedding: List[float],
        content: str,
        role: str,
    ) -> None:
        """Index a message for semantic search in history."""
        payload = {
            "content": content,
            "conversation_id": str(conversation_id),
            "role": role,
        }

        point = PointStruct(id=message_id, vector=embedding, payload=payload)

        await self.client.upsert(
            collection_name=MESSAGES_COLLECTION,
            points=[point],
        )

    async def search_messages(
        self,
        query_embedding: List[float],
        conversation_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search messages by similarity."""
        must_conditions = []

        if conversation_id:
            must_conditions.append(
                FieldCondition(
                    key="conversation_id",
                    match=MatchValue(value=str(conversation_id)),
                )
            )

        search_filter = Filter(must=must_conditions) if must_conditions else None

        results = await self.client.search(
            collection_name=MESSAGES_COLLECTION,
            query_vector=query_embedding,
            query_filter=search_filter,
            limit=limit,
            score_threshold=0.6,
        )

        return [
            {
                "id": r.id,
                "score": r.score,
                "content": r.payload.get("content", ""),
                "role": r.payload.get("role", ""),
            }
            for r in results
        ]

    async def delete_conversation_messages(self, conversation_id: str) -> None:
        """Delete all messages for a conversation."""
        filter_ = Filter(
            must=[
                FieldCondition(
                    key="conversation_id",
                    match=MatchValue(value=str(conversation_id)),
                )
            ]
        )

        results = await self.client.scroll(
            collection_name=MESSAGES_COLLECTION,
            scroll_filter=filter_,
            limit=10000,
        )

        if results[0]:
            point_ids = [p.id for p in results[0]]
            await self.client.delete(
                collection_name=MESSAGES_COLLECTION,
                points_selector=PointIdsList(points=point_ids),
            )


# Global instance
vector_store = VectorStore()
