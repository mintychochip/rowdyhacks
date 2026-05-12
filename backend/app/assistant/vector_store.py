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
    MinShould,
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

# Sentinel value for global documents (e.g., site pages) that match any hackathon
GLOBAL_HACKATHON_ID = "global"


class VectorStore:
    """Singleton manager for the Qdrant vector store.

    Maintains two collections: ``assistant_documents`` (RAG knowledge base)
    and ``assistant_messages`` (conversation history). All vectors are
    384-dimensional cosine-similarity embeddings produced by ``all-MiniLM-L6-v2``.
    """

    _instance: Optional["VectorStore"] = None
    _client: Optional[AsyncQdrantClient] = None

    def __new__(cls) -> "VectorStore":
        """Create or return the singleton vector store instance.

        Behavior:
        1. Instantiate the singleton on first call.
        2. Return the existing instance on subsequent calls.

        Raises: None
        Side Effects: Sets ``cls._instance`` on first call.
        Dependencies: None
        Consumers: Global ``vector_store`` instance.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def client(self) -> AsyncQdrantClient:
        """Get or create the async Qdrant client.

        Behavior:
        1. Instantiate the client from ``settings.qdrant_url`` if not cached.
        2. Return the cached client.

        Raises: None
        Side Effects: Sets ``self._client`` on first access.
        Dependencies: qdrant_client.AsyncQdrantClient, app.config.settings.
        Consumers: All VectorStore methods.
        """
        if self._client is None:
            self._client = AsyncQdrantClient(url=settings.qdrant_url)
        return self._client

    async def initialize(self) -> None:
        """Ensure both collections exist with the proper vector schema.

        Creates ``assistant_documents`` and ``assistant_messages`` if they
        do not already exist, using 384-dimensional cosine distance.
        """
        await self._ensure_collection(DOCUMENTS_COLLECTION)
        await self._ensure_collection(MESSAGES_COLLECTION)
        logger.info("Vector store initialized")

    async def _ensure_collection(self, name: str) -> None:
        """Create a collection if missing and verify it is healthy.

        Behavior:
        1. List existing collections.
        2. If the collection is missing, create it with cosine distance and 384 dimensions.
        3. If it exists, verify the status is GREEN and log warnings otherwise.

        Raises: Exception if Qdrant communication fails (re-raised after logging).
        Side Effects: Creates Qdrant collection if missing.
        Dependencies: qdrant_client.AsyncQdrantClient, qdrant_client.http.models.VectorParams, qdrant_client.http.models.Distance.
        Consumers: VectorStore.initialize.
        """
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
        doc_type: str,
        title: str,
        hackathon_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        role_access: Optional[List[str]] = None,
    ) -> None:
        """Index a document with its embedding in the knowledge base.

        Behavior:
        1. Build a payload dict with content, hackathon_id, doc_type, title, metadata, and role_access.
        2. Create a Qdrant PointStruct from the doc_id, embedding, and payload.
        3. Upsert the point into the ``assistant_documents`` collection.

        Raises: None
        Side Effects: Writes to Qdrant DOCUMENTS_COLLECTION.
        Dependencies: qdrant_client.http.models.PointStruct.
        Consumers: DocumentIndexer, FAQ indexing.
        """
        payload = {
            "content": content,
            "hackathon_id": hackathon_id or GLOBAL_HACKATHON_ID,
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
        """Search documents by vector similarity with optional metadata filters.

        Behavior:
        1. Build must conditions for doc_type and role filters.
        2. Build should conditions to match the requested hackathon OR global documents.
        3. Assemble a Qdrant Filter and execute vector search.
        4. Map results into dicts with id, score, content, title, doc_type, and metadata.

        Raises: None
        Side Effects: None (read-only from caller perspective).
        Dependencies: qdrant_client.http.models.Filter, qdrant_client.http.models.FieldCondition, qdrant_client.http.models.MatchValue.
        Consumers: Assistant context builder, FAQ search.
        """
        must_conditions = []
        should_conditions = []

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

        if hackathon_id:
            # Match either the given hackathon OR global documents
            should_conditions = [
                FieldCondition(
                    key="hackathon_id",
                    match=MatchValue(value=str(hackathon_id)),
                ),
                FieldCondition(
                    key="hackathon_id",
                    match=MatchValue(value=GLOBAL_HACKATHON_ID),
                ),
            ]

        search_filter = None
        if must_conditions or should_conditions:
            search_filter = Filter(
                must=must_conditions or None,
                should=should_conditions or None,
                min_should=MinShould(conditions=should_conditions, min_count=1) if should_conditions else None,
            )

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
        """Delete all documents scoped to a specific hackathon.

        Behavior:
        1. Build a Filter matching the hackathon_id field.
        2. Scroll to collect all point IDs in the collection.
        3. Delete the points and return the count.

        Raises: None
        Side Effects: Deletes points from Qdrant DOCUMENTS_COLLECTION.
        Dependencies: qdrant_client.http.models.Filter, qdrant_client.http.models.PointIdsList.
        Consumers: DocumentIndexer.delete_hackathon_documents.
        """
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
        """Delete a single document by its Qdrant point ID.

        Behavior:
        1. Delete the point from the DOCUMENTS_COLLECTION by ID.

        Raises: None
        Side Effects: Deletes a point from Qdrant DOCUMENTS_COLLECTION.
        Dependencies: qdrant_client.http.models.PointIdsList.
        Consumers: Document management endpoints.
        """
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
        """Index a chat message for semantic search within conversation history.

        Behavior:
        1. Build a payload with content, conversation_id, and role.
        2. Create a PointStruct and upsert into MESSAGES_COLLECTION.

        Raises: None
        Side Effects: Writes to Qdrant MESSAGES_COLLECTION.
        Dependencies: qdrant_client.http.models.PointStruct.
        Consumers: Assistant message indexing.
        """
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
        """Search indexed messages by vector similarity.

        Behavior:
        1. Build a must condition for conversation_id if provided.
        2. Execute vector search over MESSAGES_COLLECTION.
        3. Map results into dicts with id, score, content, and role.

        Raises: None
        Side Effects: None (read-only from caller perspective).
        Dependencies: qdrant_client.http.models.Filter, qdrant_client.http.models.FieldCondition, qdrant_client.http.models.MatchValue.
        Consumers: Assistant conversation history retrieval.
        """
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
        """Delete every message belonging to a conversation.

        Behavior:
        1. Build a Filter matching the conversation_id field.
        2. Scroll to collect all point IDs in MESSAGES_COLLECTION.
        3. Delete the points.

        Raises: None
        Side Effects: Deletes points from Qdrant MESSAGES_COLLECTION.
        Dependencies: qdrant_client.http.models.Filter, qdrant_client.http.models.PointIdsList.
        Consumers: Assistant conversation cleanup.
        """
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
