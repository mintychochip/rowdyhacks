"""Document indexing pipeline for the assistant."""

import logging
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.embedder import embedder
from app.assistant.vector_store import vector_store
from app.models import Hackathon, Track
from app.models_assistant import AssistantDocument, DocumentType

logger = logging.getLogger(__name__)


class DocumentIndexer:
    """Indexes hackathon data into the assistant's RAG vector store.

    Converts hackathon metadata, prize tracks, and FAQ entries into
    embedded documents stored in Qdrant so the assistant can retrieve
    them semantically during conversations.
    """

    def __init__(self, db: AsyncSession):
        """Initialize the indexer with a database session.

        Behavior:
        1. Store the database session as an instance attribute.

        Raises: None
        Side Effects: None (read-only, no state mutation beyond self).
        Dependencies: sqlalchemy.ext.asyncio.AsyncSession.
        Consumers: DocumentIndexer instantiation.
        """
        self.db = db

    async def index_hackathon(self, hackathon: Hackathon) -> int:
        """Index all assistant-relevant data for a hackathon.

        Behavior:
        1. Index general hackathon info.
        2. Index prize tracks.
        3. Index default FAQ entries.
        4. Log and return the total document count.

        Raises: None
        Side Effects: Writes to Qdrant and the relational database.
        Dependencies: DocumentIndexer._index_hackathon_info, DocumentIndexer._index_tracks, DocumentIndexer._index_faq.
        Consumers: Hackathon creation/update hooks.
        """
        count = 0

        # Index hackathon info
        count += await self._index_hackathon_info(hackathon)

        # Index tracks
        count += await self._index_tracks(hackathon)

        # Index FAQ (if any)
        count += await self._index_faq(hackathon)

        logger.info(f"Indexed {count} documents for hackathon {hackathon.name}")
        return count

    async def _index_hackathon_info(self, hackathon: Hackathon) -> int:
        """Index general hackathon information as a single document.

        Behavior:
        1. Build a text block from hackathon metadata (name, dates, venue, WiFi, etc.).
        2. Generate an embedding for the content.
        3. Upsert an AssistantDocument record (create or update existing).
        4. Index the document in Qdrant.
        5. Commit and return 1.

        Raises: None
        Side Effects: Inserts/updates AssistantDocument row; writes to Qdrant.
        Dependencies: app.assistant.embedder.embedder, app.assistant.vector_store.vector_store.
        Consumers: DocumentIndexer.index_hackathon.
        """
        # Build content
        content_parts = [
            f"Hackathon: {hackathon.name}",
            f"Start Date: {hackathon.start_date}",
            f"End Date: {hackathon.end_date}",
        ]

        if hackathon.application_deadline:
            content_parts.append(f"Application Deadline: {hackathon.application_deadline}")

        if hackathon.venue_address:
            content_parts.append(f"Venue: {hackathon.venue_address}")

        if hackathon.wifi_ssid:
            content_parts.append(f"WiFi: {hackathon.wifi_ssid} / {hackathon.wifi_password or 'Ask at check-in'}")

        if hackathon.parking_info:
            content_parts.append(f"Parking: {hackathon.parking_info}")

        if hackathon.description:
            content_parts.append(f"Description: {hackathon.description}")

        if hackathon.discord_invite_url:
            content_parts.append(f"Discord: {hackathon.discord_invite_url}")

        if hackathon.devpost_url:
            content_parts.append(f"Devpost: {hackathon.devpost_url}")

        if hackathon.max_participants:
            content_parts.append(f"Max Participants: {hackathon.max_participants}")

        content = "\n".join(content_parts)

        # Generate embedding
        embedding = embedder.embed_text(content)

        # Create metadata record
        doc_id = str(uuid4())
        qdrant_point_id = str(uuid4())

        # Check if exists
        result = await self.db.execute(
            select(AssistantDocument)
            .where(AssistantDocument.hackathon_id == hackathon.id)
            .where(AssistantDocument.doc_type == DocumentType.HACKATHON_INFO)
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing - use stored Qdrant point ID
            existing.version += 1
            existing.doc_metadata["content"] = content
            qdrant_point_id = existing.qdrant_id
        else:
            # Create new
            doc = AssistantDocument(
                id=uuid4(),
                hackathon_id=hackathon.id,
                qdrant_id=qdrant_point_id,
                doc_type=DocumentType.HACKATHON_INFO,
                title=f"{hackathon.name} - General Information",
                doc_metadata={"content": content},
            )
            self.db.add(doc)

        # Index in vector store
        await vector_store.index_document(
            doc_id=qdrant_point_id,
            embedding=embedding,
            content=content,
            hackathon_id=str(hackathon.id),
            doc_type=DocumentType.HACKATHON_INFO.value,
            title=f"{hackathon.name} - Information",
            metadata={"source": "hackathon"},
            role_access=["participant", "judge", "organizer"],
        )

        await self.db.commit()
        return 1

    async def _index_tracks(self, hackathon: Hackathon) -> int:
        """Index all prize tracks for a hackathon.

        Behavior:
        1. Query all Track rows for the hackathon.
        2. For each track, build a text block, embed it, and upsert an AssistantDocument.
        3. Index each track document in Qdrant.
        4. Commit and return the count.

        Raises: None
        Side Effects: Inserts/updates AssistantDocument rows; writes to Qdrant.
        Dependencies: app.assistant.embedder.embedder, app.assistant.vector_store.vector_store.
        Consumers: DocumentIndexer.index_hackathon.
        """
        result = await self.db.execute(select(Track).where(Track.hackathon_id == hackathon.id))
        tracks = result.scalars().all()

        count = 0
        for track in tracks:
            content_parts = [
                f"Track: {track.name}",
            ]

            if track.description:
                content_parts.append(f"Description: {track.description}")

            if track.criteria:
                content_parts.append(f"Judging Criteria: {track.criteria}")

            if track.prize:
                content_parts.append(f"Prize: {track.prize}")

            if track.resources:
                content_parts.append(f"Resources: {track.resources}")

            content = "\n".join(content_parts)
            embedding = embedder.embed_text(content)

            qdrant_point_id = str(uuid4())

            # Check if exists
            result = await self.db.execute(
                select(AssistantDocument)
                .where(AssistantDocument.source_id == track.id)
                .where(AssistantDocument.doc_type == DocumentType.TRACK_INFO)
            )
            existing = result.scalar_one_or_none()

            if existing:
                existing.version += 1
                existing.doc_metadata["content"] = content
                qdrant_point_id = existing.qdrant_id
            else:
                doc = AssistantDocument(
                    id=uuid4(),
                    hackathon_id=hackathon.id,
                    qdrant_id=qdrant_point_id,
                    doc_type=DocumentType.TRACK_INFO,
                    title=track.name,
                    source_id=track.id,
                    doc_metadata={"content": content, "track_id": str(track.id)},
                )
                self.db.add(doc)

            # Index in vector store
            await vector_store.index_document(
                doc_id=qdrant_point_id,
                embedding=embedding,
                content=content,
                hackathon_id=str(hackathon.id),
                doc_type=DocumentType.TRACK_INFO.value,
                title=track.name,
                metadata={"track_id": str(track.id)},
                role_access=["participant", "judge", "organizer"],
            )

            count += 1

        await self.db.commit()
        return count

    async def _index_faq(self, hackathon: Hackathon) -> int:
        """Index default FAQ entries for a hackathon.

        Behavior:
        1. Define a set of default FAQ question/answer pairs.
        2. Check if any FAQ already exists for this hackathon; if so, skip.
        3. For each default FAQ, build text, embed it, create an AssistantDocument, and index in Qdrant.
        4. Commit and return the count.

        Raises: None
        Side Effects: Inserts AssistantDocument rows; writes to Qdrant.
        Dependencies: app.assistant.embedder.embedder, app.assistant.vector_store.vector_store.
        Consumers: DocumentIndexer.index_hackathon.
        """
        # For now, create some default FAQ entries
        default_faqs = [
            {
                "question": "What should I bring?",
                "answer": "Laptop, charger, student ID, water bottle, and any hardware you want to hack with. We'll provide food, WiFi, and a place to work!",
            },
            {
                "question": "Can I work on a previous project?",
                "answer": "No, all projects must be started from scratch at the hackathon. You can use open source libraries and APIs, but the core project should be new.",
            },
            {
                "question": "What if I don't have a team?",
                "answer": "No worries! We'll have team formation activities at the start. You can also join our Discord to find teammates beforehand.",
            },
            {
                "question": "When is the submission deadline?",
                "answer": f"Submissions are due by the end of the hackathon on {hackathon.end_date}. Make sure to submit on Devpost before the deadline!",
            },
        ]

        count = 0
        for i, faq in enumerate(default_faqs):
            content = f"Q: {faq['question']}\nA: {faq['answer']}"
            embedding = embedder.embed_text(content)

            qdrant_point_id = str(uuid4())

            # Check if this FAQ already exists (skip if any FAQ exists for this hackathon)
            result = await self.db.execute(
                select(AssistantDocument)
                .where(AssistantDocument.hackathon_id == hackathon.id)
                .where(AssistantDocument.doc_type == DocumentType.FAQ)
                .limit(1)
            )
            any_existing = result.scalar_one_or_none()

            if any_existing:
                # Already indexed FAQs for this hackathon, skip
                break

            # Create new
            doc = AssistantDocument(
                id=uuid4(),
                hackathon_id=hackathon.id,
                qdrant_id=qdrant_point_id,
                doc_type=DocumentType.FAQ,
                title=f"FAQ: {faq['question'][:50]}...",
                doc_metadata={"question": faq["question"], "answer": faq["answer"]},
            )
            self.db.add(doc)

            # Index in vector store
            await vector_store.index_document(
                doc_id=qdrant_point_id,
                embedding=embedding,
                content=content,
                hackathon_id=str(hackathon.id),
                doc_type=DocumentType.FAQ.value,
                title=faq["question"],
                metadata={"question": faq["question"]},
                role_access=["participant", "judge", "organizer"],
            )

            count += 1

        await self.db.commit()
        return count

    async def add_faq_entry(
        self,
        hackathon: Hackathon,
        question: str,
        answer: str,
    ) -> str:
        """Add a custom FAQ entry and index it for semantic retrieval.

        Behavior:
        1. Build the FAQ text block.
        2. Generate an embedding.
        3. Create an AssistantDocument and index it in Qdrant.
        4. Commit and return the Qdrant point ID.

        Raises: None
        Side Effects: Inserts AssistantDocument row; writes to Qdrant.
        Dependencies: app.assistant.embedder.embedder, app.assistant.vector_store.vector_store.
        Consumers: FAQ management endpoints.
        """
        content = f"Q: {question}\nA: {answer}"
        embedding = embedder.embed_text(content)

        doc_id = str(uuid4())

        doc = AssistantDocument(
            id=uuid4(),
            hackathon_id=hackathon.id,
            qdrant_id=doc_id,
            doc_type=DocumentType.FAQ,
            title=f"FAQ: {question[:50]}...",
            doc_metadata={"question": question, "answer": answer},
        )
        self.db.add(doc)

        await vector_store.index_document(
            doc_id=doc_id,
            embedding=embedding,
            content=content,
            hackathon_id=str(hackathon.id),
            doc_type=DocumentType.FAQ.value,
            title=question,
            metadata={"question": question},
            role_access=["participant", "judge", "organizer"],
        )

        await self.db.commit()
        return doc_id

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
        """Split text into overlapping chunks for embedding.

        Behavior:
        1. Slide a window of size ``chunk_size`` over the text.
        2. Move the window forward by ``chunk_size - overlap`` on each step.
        3. Return a list of chunk strings.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: None.
        Consumers: DocumentIndexer.index_uploaded_document.
        """
        chunks = []
        step = chunk_size - overlap
        for i in range(0, len(text), step):
            chunk = text[i : i + chunk_size]
            if chunk.strip():
                chunks.append(chunk.strip())
            if i + chunk_size >= len(text):
                break
        return chunks

    async def index_uploaded_document(
        self,
        hackathon: Hackathon,
        filename: str,
        content: str,
        s3_url: str | None = None,
        s3_key: str | None = None,
    ) -> dict:
        """Index an uploaded document by chunking, embedding, and storing in Qdrant.

        Behavior:
        1. Chunk the document text into overlapping segments.
        2. Embed each chunk using the embedder.
        3. Create an AssistantDocument row to track the upload.
        4. Index each chunk as a separate Qdrant point with shared metadata.
        5. Commit and return chunk count and IDs.

        Raises: None
        Side Effects: Inserts AssistantDocument row; writes multiple points to Qdrant.
        Dependencies: embedder, vector_store.
        Consumers: Document upload endpoints.
        """
        chunks = self._chunk_text(content)
        if not chunks:
            chunks = [content.strip() or filename]

        embeddings = embedder.embed_chunks(chunks)

        # Create a single DB record to track this uploaded file
        doc_id = str(uuid4())
        chunk_ids = [str(uuid4()) for _ in chunks]

        doc = AssistantDocument(
            id=uuid4(),
            hackathon_id=hackathon.id,
            qdrant_id=doc_id,
            doc_type=DocumentType.RESOURCES,
            title=filename,
            doc_metadata={
                "filename": filename,
                "s3_url": s3_url,
                "s3_key": s3_key,
                "chunk_count": len(chunks),
                "chunk_qdrant_ids": chunk_ids,
            },
        )
        self.db.add(doc)

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=False)):
            await vector_store.index_document(
                doc_id=chunk_ids[i],
                embedding=embedding,
                content=chunk,
                hackathon_id=str(hackathon.id),
                doc_type=DocumentType.RESOURCES.value,
                title=f"{filename} (chunk {i + 1}/{len(chunks)})",
                metadata={
                    "filename": filename,
                    "chunk_index": i,
                    "chunk_count": len(chunks),
                    "document_id": str(doc.id),
                },
                role_access=["participant", "judge", "organizer"],
            )

        await self.db.commit()
        return {
            "document_id": str(doc.id),
            "chunk_count": len(chunks),
            "chunk_ids": chunk_ids,
        }

    async def delete_uploaded_document(self, doc_id: str) -> bool:
        """Delete an uploaded document and its chunks from Qdrant and the database.

        Behavior:
        1. Load the AssistantDocument row by its UUID string.
        2. Extract chunk_qdrant_ids from metadata.
        3. Delete all chunk points from Qdrant.
        4. Delete the DB row.
        5. Commit and return True if found, False otherwise.

        Raises: None
        Side Effects: Deletes rows from PostgreSQL and points from Qdrant.
        Dependencies: vector_store.delete_documents.
        Consumers: Document deletion endpoints.
        """
        from uuid import UUID

        result = await self.db.execute(select(AssistantDocument).where(AssistantDocument.id == UUID(doc_id)))
        doc = result.scalar_one_or_none()
        if not doc:
            return False

        chunk_ids = doc.doc_metadata.get("chunk_qdrant_ids", [])
        if chunk_ids:
            await vector_store.delete_documents(chunk_ids)

        await self.db.delete(doc)
        await self.db.commit()
        return True

    async def delete_hackathon_documents(self, hackathon_id: str) -> int:
        """Delete all indexed documents associated with a hackathon.

        Behavior:
        1. Delete matching points from Qdrant.
        2. Query and delete matching AssistantDocument rows from the database.
        3. Commit and return the Qdrant deletion count.

        Raises: None
        Side Effects: Deletes rows from PostgreSQL and points from Qdrant.
        Dependencies: app.assistant.vector_store.vector_store.delete_by_hackathon.
        Consumers: Hackathon cleanup endpoints.
        """
        # Delete from Qdrant
        count = await vector_store.delete_by_hackathon(hackathon_id)

        # Delete from database
        result = await self.db.execute(select(AssistantDocument).where(AssistantDocument.hackathon_id == hackathon_id))
        docs = result.scalars().all()

        for doc in docs:
            await self.db.delete(doc)

        await self.db.commit()
        return count


async def initialize_vector_store() -> None:
    """Initialize the Qdrant vector store on application startup.

    Behavior:
    1. Call ``vector_store.initialize`` to ensure collections exist.
    2. Log success.
    3. On exception, log the error but do not raise, so the assistant can still operate without semantic search.

    Raises: None (all exceptions are caught and logged).
    Side Effects: Creates Qdrant collections if missing.
    Dependencies: vector_store.initialize.
    Consumers: Application lifespan startup.
    """
    try:
        await vector_store.initialize()
        logger.info("Vector store initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize vector store: {e}")
        # Don't raise - assistant can work without vector search
