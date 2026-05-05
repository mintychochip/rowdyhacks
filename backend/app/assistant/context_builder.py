"""Context builder for assembling system prompts and retrieving relevant documents."""

import logging
import re
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.embedder import embedder
from app.assistant.permissions import get_tools_for_role
from app.assistant.vector_store import vector_store
from app.models import Hackathon, Registration, Track, User

# Build intent detection patterns
BUILD_INTENT_PATTERNS = [
    # Direct "I want to" patterns
    r"i\s+want\s+to\s+(build|create|make|develop|start)\s+(a|an|my|the)",
    r"i\s+want\s+to\s+(build|create|make|develop|start)\s+\w+",
    # Active building patterns
    r"i['']?m\s+(building|creating|making|developing|starting)\s+(a|an|my|the)",
    r"i['']?m\s+(building|creating|making|developing)\s+\w+",
    r"i\s+am\s+(building|creating|making|developing|starting)\s+(a|an|my|the)",
    r"i\s+am\s+(building|creating|making|developing)\s+\w+",
    # "Let's" collaborative patterns
    r"let['']?s\s+(build|create|make|develop|start)\s+(a|an|my|the)",
    r"let['']?s\s+(build|create|make|develop)\s+\w+",
    r"lets\s+(build|create|make|develop|start)\s+(a|an|my|the)",
    r"lets\s+(build|create|make|develop)\s+\w+",
    # Help/request patterns
    r"help\s+me\s+(build|create|make|develop|start)\s+(a|an|my|the)",
    r"help\s+me\s+(build|create|make|develop)\s+\w+",
    r"i\s+need\s+to\s+(build|create|make|develop|start)\s+(a|an|my|the)",
    r"i\s+need\s+to\s+(build|create|make|develop)\s+\w+",
    r"i\s+would\s+like\s+to\s+(build|create|make|develop|start)",
    # Planning/intention patterns
    r"(plan|planning)\s+to\s+(build|create|make|develop|start)",
    r"thinking\s+about\s+(building|creating|making|developing|starting)",
    # Project/hackathon specific patterns
    r"starting\s+(a|an|my|the)\s+(new\s+)?project",
    r"new\s+project\s+(idea|concept|plan)",
    r"hackathon\s+project\s+(idea|concept|plan|for)",
    r"app\s+(idea|concept|for)",
    r"website\s+(idea|concept|for)",
    r"(build|create|make)\s+(an?|my)\s+(app|website|tool|bot|game|service|platform)",
    r"(build|create|make)\s+(an?|my)\s+\w+\s+(app|website|tool|bot|game|service|platform)",
    # Question patterns
    r"how\s+(can|do|should)\s+i\s+(build|create|make|develop|start)",
    r"what\s+should\s+i\s+(build|create|make|develop)",
    r"any\s+ideas\s+for\s+(a|an)\s+\w+\s+(project|app|website)",
    # Technical implementation patterns
    r"implement\s+(a|an|my)\s+",
    r"code\s+(a|an|my)\s+",
    r"prototype\s+(a|an|my)\s+",
    r"mvp\s+for\s+(a|an|my)\s+",
    r"demo\s+(for|of)\s+",
]

logger = logging.getLogger(__name__)


def detect_build_intent(message: str) -> dict[str, Any]:
    """
    Detect if a user message contains intent to build something.

    Args:
        message: The user's message text

    Returns:
        Dict with:
        - hasBuildIntent: bool indicating if build intent was detected
        - suggestedMode: str ('plan', 'build', or 'chat')
        - confidence: float (0.0-1.0) indicating confidence level
        - matchedPattern: str | None - the pattern that matched, if any
    """
    if not message or not message.strip():
        return {
            "hasBuildIntent": False,
            "suggestedMode": "chat",
            "confidence": 0.0,
            "matchedPattern": None,
        }

    message_lower = message.lower().strip()

    # Check against all patterns
    matched_pattern = None
    for pattern in BUILD_INTENT_PATTERNS:
        if re.search(pattern, message_lower):
            matched_pattern = pattern
            break

    # Determine suggested mode based on context
    if matched_pattern:
        # Check for planning keywords to suggest 'plan' mode
        planning_keywords = ["plan", "planning", "idea", "concept", "strategy", "roadmap"]
        has_planning_keywords = any(kw in message_lower for kw in planning_keywords)

        # Check for immediate action keywords to suggest 'build' mode
        action_keywords = ["start", "begin", "now", "immediately", "let's", "lets"]
        has_action_keywords = any(kw in message_lower for kw in action_keywords)

        if has_planning_keywords:
            suggested_mode = "plan"
            confidence = 0.9
        elif has_action_keywords:
            suggested_mode = "build"
            confidence = 0.85
        else:
            # Default to plan for build intent (safer starting point)
            suggested_mode = "plan"
            confidence = 0.8

        return {
            "hasBuildIntent": True,
            "suggestedMode": suggested_mode,
            "confidence": confidence,
            "matchedPattern": matched_pattern,
        }

    return {
        "hasBuildIntent": False,
        "suggestedMode": "chat",
        "confidence": 0.0,
        "matchedPattern": None,
    }


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

    def build_plan_generation_prompt(
        self,
        project_name: str,
        project_description: str,
        hackathon: Hackathon | None = None,
        tracks: list[Any] | None = None,
    ) -> str:
        """Build a system prompt for generating a project plan."""
        parts = []

        # Identity
        parts.append("You are an expert hackathon project planner. Your task is to create detailed, actionable project plans for hackathon participants.")
        parts.append(f"Current date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        # Hackathon context
        if hackathon:
            parts.append(f"\nHackathon: {hackathon.name}")
            parts.append(f"Dates: {hackathon.start_date} to {hackathon.end_date}")

        # Available tracks
        if tracks:
            parts.append("\nAvailable tracks for this hackathon:")
            for track in tracks:
                parts.append(f"- {track.name}: {track.description or 'No description'}")

        # Plan requirements
        parts.append("\n" + "=" * 50)
        parts.append("PLAN GENERATION REQUIREMENTS")
        parts.append("=" * 50)
        parts.append("\nGenerate a detailed project plan in JSON format with the following structure:")
        parts.append("""
{
  "name": "Project name (refined from user input)",
  "description": "Clear, concise project description (2-3 sentences)",
  "targetTrack": "Best matching track name from available tracks, or 'General' if none match",
  "estimatedHours": integer estimate (1-48 for hackathon scope),
  "techStack": ["Technology 1", "Technology 2", ...],
  "tasks": [
    {
      "id": "task-1",
      "description": "Clear task description",
      "estimatedMinutes": integer (in minutes, 15-480),
      "dependencies": ["task-1"] // IDs of tasks that must complete before this one
    }
  ],
  "stretchGoals": [
    "Optional feature or enhancement 1",
    "Optional feature or enhancement 2"
  ]
}
""")

        # Guidelines
        parts.append("\n" + "=" * 50)
        parts.append("GUIDELINES")
        parts.append("=" * 50)
        parts.append("1. Tasks should be ordered logically (dependencies first)")
        parts.append("2. Keep tasks concrete and actionable (not vague like 'work on frontend')")
        parts.append("3. Each task should be completable in 15-480 minutes (30 min - 8 hours)")
        parts.append("4. Tech stack should be practical for the hackathon timeframe")
        parts.append("5. Estimated hours should be realistic for a hackathon (typically 4-24 hours)")
        parts.append("6. Stretch goals should be features that enhance but aren't essential to the core demo")
        parts.append("7. If tracks are provided, recommend the best-matching track")
        parts.append("8. Use modern, beginner-friendly technologies when possible")
        parts.append("9. Include setup/deployment tasks in the plan")

        # Response format reminder
        parts.append("\n" + "=" * 50)
        parts.append("OUTPUT FORMAT")
        parts.append("=" * 50)
        parts.append("Return ONLY valid JSON matching the structure above.")
        parts.append("Do not include markdown formatting, explanations, or any other text.")
        parts.append("The JSON must be parseable by a standard JSON parser.")

        return "\n".join(parts)


# Need to import this for the organizer query
from app.models import HackathonOrganizer
