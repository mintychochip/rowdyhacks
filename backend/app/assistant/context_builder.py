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
from app.config import settings
from app.models import Hackathon, Registration, Track, User

logger = logging.getLogger(__name__)

# Build intent detection patterns
BUILD_INTENT_PATTERNS = [
    # Direct build statements
    r"i want to build\b",
    r"i wanna build\b",
    r"i want to create\b",
    r"i wanna make\b",
    r"i want to make\b",
    r"i'm building\b",
    r"i am building\b",
    r"i'm creating\b",
    r"i am creating\b",
    r"i'm making\b",
    r"help me build\b",
    r"help me create\b",
    r"help me make\b",
    r"generate a prototype\b",
    r"create a prototype\b",
    r"build a prototype\b",
    r"help me code\b",
    r"i have an idea for\b",
    r"i have an idea\b",
    r"can you help me with\s+(?:react|vue|angular|python|flask|django|node|javascript|typescript|html|css|arduino|raspberry pi|iot)",
    # Project type indicators
    r"(?:web app|website|mobile app|chrome extension|discord bot|slack bot|api|dashboard|game|hack|project)\b",
    r"(?:arduino|raspberry pi|sensor|hardware|iot|embedded)\b",
    r"(?:react|vue|angular|svelte|next\.?js|nuxt)\b",
    r"(?:flask|django|fastapi|express|nodejs)\b",
    # Planning phrases
    r"plan (?:out|for|my)?\s+(?:a|an|the)?\s*(?:project|hack|app|website)",
    r"create a plan\b",
    r"generate a plan\b",
    r"roadmap for\b",
    r"step.?by.?step (?:guide|plan|tutorial)",
    # Hackathon-specific
    r"(?:submit|demo|present)\s+(?:this|my|our|the)?\s*(?:project|hack|app)",
    r"prize track\b",
    r"what (?:track|prize)\s+(?:should|could)",
]


def detect_build_intent(message: str) -> tuple[bool, float]:
    """Detect whether a user message signals intent to build a hackathon project.

    Behavior:
    1. Lowercase the input message.
    2. Match against curated regex patterns for build statements, project types, planning phrases, and hackathon vocabulary.
    3. Count the number of matches.
    4. Return a boolean flag and a confidence score (0.6 / 0.75 / 0.9 based on match count).

    Raises: None
    Side Effects: None (read-only).
    Dependencies: re.search.
    Consumers: Assistant response routing.
    """
    message_lower = message.lower()

    matches = 0
    for pattern in BUILD_INTENT_PATTERNS:
        if re.search(pattern, message_lower):
            matches += 1

    # Calculate confidence based on number of matches
    if matches >= 3:
        return True, 0.9
    elif matches >= 2:
        return True, 0.75
    elif matches >= 1:
        return True, 0.6

    return False, 0.0


def build_plan_generation_prompt(
    user_description: str,
    hackathon_name: str | None = None,
    tracks: list[dict] | None = None,
) -> str:
    """Assemble a structured prompt for AI project-plan generation.

    Behavior:
    1. Start with the AI mentor identity and a 6-hour hackathon constraint.
    2. Inject the user's project description.
    3. Optionally append hackathon name and prize track context.
    4. Return the fully formatted prompt string.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: None
    Consumers: Assistant plan-generation endpoint.
    """
    parts = []

    parts.append("You are an AI hackathon mentor. Create a detailed project plan based on the user's description.")
    parts.append("The plan should be realistic for a 6-hour hackathon.")
    parts.append("")
    parts.append("User's project description:")
    parts.append(f'"""{user_description}"""')
    parts.append("")

    if hackathon_name:
        parts.append(f"Hackathon: {hackathon_name}")
        parts.append("")

    if tracks:
        parts.append("Available prize tracks:")
        for track in tracks:
            parts.append(f"- {track['name']}: {track.get('description', 'No description')}")
        parts.append("")

    parts.append("Generate a project plan with the following structure:")
    parts.append("")
    parts.append("1. Project Name: A catchy, descriptive name (1-4 words)")
    parts.append("2. Target Track: Which prize track this project best fits")
    parts.append("3. Estimated Hours: Realistic time estimate (2-6 hours)")
    parts.append("4. Tech Stack: List of recommended technologies (3-6 items)")
    parts.append("5. MVP Tasks: 4-6 specific tasks to complete the MVP, each with:")
    parts.append("   - Task description")
    parts.append("   - Estimated minutes (15-120)")
    parts.append("   - Dependencies (task IDs that must complete first)")
    parts.append("6. Stretch Goals: 2-4 additional features if time permits")
    parts.append("")
    parts.append("Format the response as a JSON object matching this structure:")
    parts.append(
        '{"name": "...", "targetTrack": "...", "estimatedHours": 4, "techStack": [...], "tasks": [...], "stretchGoals": [...]}'
    )
    parts.append("")
    parts.append("Make the plan specific and actionable, not generic.")

    return "\n".join(parts)


def build_project_generation_prompt(
    plan: dict,
    project_type: str,
) -> str:
    """Assemble a structured prompt for AI starter-code generation.

    Behavior:
    1. Start with the AI code-generator identity.
    2. Inject the project plan (name, type, tech stack, tasks).
    3. Add file-type instructions based on the project_type category.
    4. Return the fully formatted prompt string.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: None
    Consumers: Assistant starter-code endpoint.
    """
    parts = []

    parts.append("You are an AI code generator. Create starter code for a hackathon project.")
    parts.append("")
    parts.append("Project Plan:")
    parts.append(f"- Name: {plan.get('name', 'Untitled')}")
    parts.append(f"- Type: {project_type}")
    parts.append(f"- Tech Stack: {', '.join(plan.get('techStack', []))}")
    parts.append("")
    parts.append("Tasks to implement:")
    for i, task in enumerate(plan.get("tasks", []), 1):
        parts.append(f"{i}. {task.get('description', 'Task')}")
    parts.append("")
    parts.append("Generate the following files:")
    parts.append("")

    if project_type == "web":
        parts.append("1. index.html - Main HTML file with basic structure")
        parts.append("2. style.css - CSS styling (modern, clean design)")
        parts.append("3. script.js - JavaScript functionality")
        parts.append("4. README.md - Setup and usage instructions")
    elif project_type == "python":
        parts.append("1. app.py - Main Python application")
        parts.append("2. requirements.txt - Python dependencies")
        parts.append("3. README.md - Setup and usage instructions")
    elif project_type == "fullstack":
        parts.append("1. index.html - Frontend HTML")
        parts.append("2. style.css - Frontend styling")
        parts.append("3. app.py - Flask backend")
        parts.append("4. requirements.txt - Python dependencies")
        parts.append("5. README.md - Setup and usage instructions")
    else:
        parts.append("1. Main code file(s) appropriate for the project type")
        parts.append("2. README.md - Setup and usage instructions")

    parts.append("")
    parts.append("Format the response as a JSON object with a 'files' array.")
    parts.append('Each file should have: {"path": "...", "name": "...", "content": "...", "language": "..."}')
    parts.append("")
    parts.append("Make the code functional, well-commented, and ready to run.")
    parts.append("Include placeholder comments where the user should add their own logic.")

    return "\n".join(parts)


class ContextBuilder:
    """Constructs LLM system prompts and conversation history.

    Gathers hackathon metadata, available prize tracks, role-scoped tools,
    and semantically relevant documents to produce a rich context string
    for each assistant interaction.
    """

    def __init__(self, db: AsyncSession):
        """Initialize the context builder with a database session.

        Behavior:
        1. Store the database session as an instance attribute.

        Raises: None
        Side Effects: None (read-only, no state mutation beyond self).
        Dependencies: sqlalchemy.ext.asyncio.AsyncSession.
        Consumers: ContextBuilder instantiation.
        """
        self.db = db

    async def build_system_prompt(
        self,
        user: User,
        hackathon: Hackathon | None = None,
        user_query: str | None = None,
    ) -> str:
        """Build a comprehensive system prompt for the LLM.

        Behavior:
        1. Append identity and role lines.
        2. Append available tool definitions for the user's role.
        3. Append hackathon metadata and prize tracks if provided.
        4. Inject semantically relevant knowledge-base documents.
        5. Append response guidelines and return the joined prompt.

        Raises: None
        Side Effects: None (read-only from caller perspective, but triggers vector search).
        Dependencies: app.assistant.permissions.get_tools_for_role, app.assistant.embedder.embedder, app.assistant.vector_store.vector_store.
        Consumers: Assistant chat endpoint.
        """
        parts = []

        # Identity and role
        system_prompt = f"You are an AI assistant for {settings.hackathon_name}, {settings.hackathon_tagline}."
        parts.append(system_prompt)
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
        parts.append(
            "- You can help users navigate the platform: use the query_site_pages tool to find relevant pages, then share the URL path with the user"
        )

        return "\n".join(parts)

    async def build_conversation_history(
        self,
        conversation_id: str,
        limit: int = 10,
    ) -> list[dict[str, str]]:
        """Fetch recent messages for a conversation in chronological order.

        Behavior:
        1. Query AssistantMessage rows filtered by conversation_id.
        2. Order by created_at descending and apply the limit.
        3. Reverse the list to restore chronological order.
        4. Map each row to a dict with role and content.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models_assistant.AssistantMessage.
        Consumers: Assistant chat endpoint.
        """
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
            history.append(
                {
                    "role": msg.role.value,
                    "content": msg.content,
                }
            )

        return history

    async def _get_tracks(self, hackathon_id: str) -> list[dict[str, Any]]:
        """Retrieve prize tracks for a hackathon.

        Behavior:
        1. Query Track rows filtered by hackathon_id ordered by name.
        2. Map each track to a dict with id, name, description, and prize.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models.Track.
        Consumers: ContextBuilder.build_system_prompt.
        """
        result = await self.db.execute(select(Track).where(Track.hackathon_id == hackathon_id).order_by(Track.name))
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
        """Retrieve semantically relevant documents from the knowledge base.

        Behavior:
        1. Embed the user's query text.
        2. Search the vector store for matching documents filtered by hackathon, role, and score threshold.
        3. Return the documents or an empty list on failure.

        Raises: None
        Side Effects: None (read-only from caller perspective, but triggers vector search).
        Dependencies: app.assistant.embedder.embedder, app.assistant.vector_store.vector_store.
        Consumers: ContextBuilder.build_system_prompt.
        """
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
        """List hackathons the user is actively participating in or organizing.

        Behavior:
        1. Query accepted/checked-in registrations joined with hackathons ending within the last 7 days.
        2. Query hackathons where the user is an organizer (also ending within the last 7 days).
        3. Deduplicate and return a combined list of hackathon dicts.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models.Registration, app.models.Hackathon.
        Consumers: Assistant context builder, user dashboard.
        """
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
            hackathons.append(
                {
                    "id": str(hack.id),
                    "name": hack.name,
                    "role": "participant",
                    "status": reg.status,
                }
            )

        # Get hackathons where user is organizer
        result = await self.db.execute(
            select(Hackathon)
            .where(
                (Hackathon.organizer_id == user_id)
                | (
                    Hackathon.id.in_(
                        select(HackathonOrganizer.hackathon_id).where(HackathonOrganizer.user_id == user_id)
                    )
                )
            )
            .where(Hackathon.end_date >= datetime.now() - timedelta(days=7))
        )
        org_hackathons = result.scalars().all()

        for hack in org_hackathons:
            # Check not already added
            if not any(h["id"] == str(hack.id) for h in hackathons):
                hackathons.append(
                    {
                        "id": str(hack.id),
                        "name": hack.name,
                        "role": "organizer",
                        "status": "active",
                    }
                )

        return hackathons


# Need to import this for the organizer query
from app.models import HackathonOrganizer
