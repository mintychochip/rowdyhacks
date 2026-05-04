"""Document indexing pipeline for the assistant."""

import logging
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.embedder import embedder
from app.assistant.vector_store import vector_store
from app.models import Hackathon, Track
from app.models_assistant import AssistantDocument, DocumentType

logger = logging.getLogger(__name__)


class DocumentIndexer:
    """Indexes hackathon data for assistant RAG."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def index_hackathon(self, hackathon: Hackathon) -> int:
        """Index all data for a hackathon."""
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
        """Index general hackathon information."""
        # Build content
        content_parts = [
            f"Hackathon: {hackathon.name}",
            f"Start Date: {hackathon.start_date}",
            f"End Date: {hackathon.end_date}",
        ]

        if hackathon.application_deadline:
            content_parts.append(f"Application Deadline: {hackathon.application_deadline}")

        if hackathon.venue:
            content_parts.append(f"Venue: {hackathon.venue}")

        if hackathon.address:
            content_parts.append(f"Address: {hackathon.address}")

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
        qdrant_id = f"hackathon_{hackathon.id}_info"

        # Check if exists
        result = await self.db.execute(
            select(AssistantDocument)
            .where(AssistantDocument.qdrant_id == qdrant_id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing
            existing.version += 1
            existing.metadata["content"] = content
        else:
            # Create new
            doc = AssistantDocument(
                id=uuid4(),
                hackathon_id=hackathon.id,
                qdrant_id=qdrant_id,
                doc_type=DocumentType.HACKATHON_INFO,
                title=f"{hackathon.name} - General Information",
                doc_doc_metadata={"content": content},
            )
            self.db.add(doc)

        # Index in vector store
        await vector_store.index_document(
            doc_id=qdrant_id,
            embedding=embedding,
            content=content,
            hackathon_id=str(hackathon.id),
            doc_type=DocumentType.HACKATHON_INFO.value,
            title=f"{hackathon.name} - Information",
            doc_doc_metadata={"source": "hackathon"},
            role_access=["participant", "judge", "organizer"],
        )

        await self.db.commit()
        return 1

    async def _index_tracks(self, hackathon: Hackathon) -> int:
        """Index all tracks for a hackathon."""
        result = await self.db.execute(
            select(Track).where(Track.hackathon_id == hackathon.id)
        )
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

            qdrant_id = f"hackathon_{hackathon.id}_track_{track.id}"

            # Check if exists
            result = await self.db.execute(
                select(AssistantDocument)
                .where(AssistantDocument.qdrant_id == qdrant_id)
            )
            existing = result.scalar_one_or_none()

            if existing:
                existing.version += 1
                existing.metadata["content"] = content
            else:
                doc = AssistantDocument(
                    id=uuid4(),
                    hackathon_id=hackathon.id,
                    qdrant_id=qdrant_id,
                    doc_type=DocumentType.TRACK_INFO,
                    title=track.name,
                    source_id=track.id,
                    doc_metadata={"content": content, "track_id": str(track.id)},
                )
                self.db.add(doc)

            # Index in vector store
            await vector_store.index_document(
                doc_id=qdrant_id,
                embedding=embedding,
                content=content,
                hackathon_id=str(hackathon.id),
                doc_type=DocumentType.TRACK_INFO.value,
                title=track.name,
                doc_metadata={"track_id": str(track.id)},
                role_access=["participant", "judge", "organizer"],
            )

            count += 1

        await self.db.commit()
        return count

    async def _index_faq(self, hackathon: Hackathon) -> int:
        """Index FAQ entries."""
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

            qdrant_id = f"hackathon_{hackathon.id}_faq_{i}"

            # Check if exists
            result = await self.db.execute(
                select(AssistantDocument)
                .where(AssistantDocument.qdrant_id == qdrant_id)
            )
            existing = result.scalar_one_or_none()

            if not existing:
                doc = AssistantDocument(
                    id=uuid4(),
                    hackathon_id=hackathon.id,
                    qdrant_id=qdrant_id,
                    doc_type=DocumentType.FAQ,
                    title=f"FAQ: {faq['question'][:50]}...",
                    doc_metadata={"question": faq["question"], "answer": faq["answer"]},
                )
                self.db.add(doc)

                # Index in vector store
                await vector_store.index_document(
                    doc_id=qdrant_id,
                    embedding=embedding,
                    content=content,
                    hackathon_id=str(hackathon.id),
                    doc_type=DocumentType.FAQ.value,
                    title=faq["question"],
                    doc_metadata={"question": faq["question"]},
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
        """Add a new FAQ entry and index it."""
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
            doc_metadata={"question": question},
            role_access=["participant", "judge", "organizer"],
        )

        await self.db.commit()
        return doc_id

    async def delete_hackathon_documents(self, hackathon_id: str) -> int:
        """Delete all documents for a hackathon."""
        # Delete from Qdrant
        count = await vector_store.delete_by_hackathon(hackathon_id)

        # Delete from database
        result = await self.db.execute(
            select(AssistantDocument)
            .where(AssistantDocument.hackathon_id == hackathon_id)
        )
        docs = result.scalars().all()

        for doc in docs:
            await self.db.delete(doc)

        await self.db.commit()
        return count


async def initialize_vector_store() -> None:
    """Initialize the vector store on startup."""
    try:
        await vector_store.initialize()
        logger.info("Vector store initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize vector store: {e}")
        # Don't raise - assistant can work without vector search
