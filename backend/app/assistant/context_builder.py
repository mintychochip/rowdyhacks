"""Context builder for assembling system prompts and retrieving relevant documents."""

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.embedder import embedder
from app.assistant.permissions import get_tools_for_role
from app.assistant.vector_store import vector_store
from app.models import Hackathon, Registration, Track, User

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Builds context for LLM conversations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def build_system_prompt(
        self,
        user: User,
        hackathon: Hackathon | None = None,
        user_query: str | None = None,
    ) -> str:
        """Build a comprehensive system prompt for the LLM."""
        parts = []

        # Identity and role
        parts.append("You are an AI assistant for Hack the Valley, a hackathon management platform.")
        parts.append(f"The user's role is: {user.role}")
        parts.append(f"Current date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        # Available tools
        tools = get_tools_for_role(user.role)
        if tools:
            parts.append("\nYou have access to the following tools:")
            for tool in tools:
                # Tool is now in OpenAI format with type and function wrapper
                func = tool.get("function", {})
                parts.append(f"- {func.get('name', 'unknown')}: {func.get('description', '')}")
            parts.append("\nWhen you need to use a tool, respond with a JSON object in this format:")
            parts.append('{"tool": "tool_name", "parameters": {...}}')
            parts.append("After the tool returns, I'll provide the result and you can continue.")

        # Hackathon context
        if hackathon:
            parts.append(f"\nCurrent hackathon context: {hackathon.name}")
            parts.append(f"Dates: {hackathon.start_date} to {hackathon.end_date}")

            # Get tracks
            tracks = await self._get_tracks(hackathon.id)
            if tracks:
                parts.append("\nAvailable tracks:")
                for track in tracks:
                    parts.append(f"- {track['name']}: {track['description'][:100]}...")

        # Retrieve relevant documents
        if user_query:
            relevant_docs = await self._get_relevant_documents(
                query=user_query,
                hackathon_id=str(hackathon.id) if hackathon else None,
                role=user.role,
            )
            if relevant_docs:
                parts.append("\nRelevant information from knowledge base:")
                for doc in relevant_docs:
                    parts.append(f"[{doc['doc_type']}] {doc['title']}: {doc['content'][:200]}...")

        # Response guidelines
        parts.append("\nGuidelines:")
        parts.append("- Be helpful, friendly, and concise")
        parts.append("- If you don't know something, say so clearly")
        parts.append("- Use the tools available to you to provide accurate information")
        parts.append("- When helping with ideation, be creative but practical")
        parts.append("- For judging questions, emphasize fairness and consistency")
        parts.append("- Format responses clearly with bullet points or numbered lists when appropriate")

        return "\n".join(parts)

    async def build_conversation_history(
        self,
        conversation_id: str,
        limit: int = 10,
    ) -> list[dict[str, str]]:
        """Build conversation history for context window."""
        from app.models_assistant import AssistantMessage

        result = await self.db.execute(
            select(AssistantMessage)
            .where(AssistantMessage.conversation_id == conversation_id)
            .order_by(AssistantMessage.created_at.desc())
            .limit(limit)
        )
        messages = result.scalars().all()

        # Reverse to get chronological order
        messages = list(reversed(messages))

        history = []
        for msg in messages:
            history.append({
                "role": msg.role.value,
                "content": msg.content,
            })

        return history

    async def _get_tracks(self, hackathon_id: str) -> list[dict[str, Any]]:
        """Get tracks for a hackathon."""
        result = await self.db.execute(
            select(Track)
            .where(Track.hackathon_id == hackathon_id)
            .order_by(Track.name)
        )
        tracks = result.scalars().all()

        return [
            {
                "id": str(t.id),
                "name": t.name,
                "description": t.description or "",
                "prize": t.prize or "TBA",
            }
            for t in tracks
        ]

    async def _get_relevant_documents(
        self,
        query: str,
        hackathon_id: str | None,
        role: str,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        """Get relevant documents via semantic search."""
        try:
            query_embedding = embedder.embed_text(query)
            docs = await vector_store.search_documents(
                query_embedding=query_embedding,
                hackathon_id=hackathon_id,
                role=role,
                limit=limit,
                score_threshold=0.75,
            )
            return docs
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return []

    async def get_user_active_hackathons(self, user_id: str) -> list[dict[str, Any]]:
        """Get hackathons the user is actively participating in."""
        # Get registrations
        result = await self.db.execute(
            select(Registration, Hackathon)
            .join(Hackathon, Registration.hackathon_id == Hackathon.id)
            .where(Registration.user_id == user_id)
            .where(Registration.status.in_(["accepted", "checked_in"]))
            .where(Hackathon.end_date >= datetime.now() - timedelta(days=7))
        )
        rows = result.all()

        hackathons = []
        for reg, hack in rows:
            hackathons.append({
                "id": str(hack.id),
                "name": hack.name,
                "role": "participant",
                "status": reg.status,
            })

        # Get hackathons where user is organizer
        result = await self.db.execute(
            select(Hackathon)
            .where(
                (Hackathon.organizer_id == user_id) |
                (Hackathon.id.in_(
                    select(HackathonOrganizer.hackathon_id)
                    .where(HackathonOrganizer.user_id == user_id)
                ))
            )
            .where(Hackathon.end_date >= datetime.now() - timedelta(days=7))
        )
        org_hackathons = result.scalars().all()

        for hack in org_hackathons:
            # Check not already added
            if not any(h["id"] == str(hack.id) for h in hackathons):
                hackathons.append({
                    "id": str(hack.id),
                    "name": hack.name,
                    "role": "organizer",
                    "status": "active",
                })

        return hackathons


# Need to import this for the organizer query
from app.models import HackathonOrganizer
