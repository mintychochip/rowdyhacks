"""API routes for the AI assistant."""

import json
import logging
from datetime import datetime, timedelta
from typing import AsyncGenerator, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.context_builder import ContextBuilder
from app.assistant.embedder import embedder
from app.assistant.indexer import DocumentIndexer
from app.assistant.llm import llm_client, get_llm_client
from app.assistant.permissions import can_use_tool, get_tools_for_role
from app.config import settings
from app.assistant.tools import ToolExecutor
from app.assistant.vector_store import vector_store
from app.auth import get_current_user, require_organizer, verify_access_token
from app.database import get_db
from app.models import Hackathon, User
from app.models_assistant import (
    AssistantConversation,
    AssistantDocument,
    AssistantMessage,
    AssistantMessageStatus,
    ConversationRole,
    DocumentType,
)
from app.storage import StorageService


from app.schemas.builder import (
    GenerateProjectRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["assistant"])


async def get_hackathon(
    hackathon_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
) -> Optional[Hackathon]:
    """Get hackathon by ID if provided.

    Behavior:
    1. Return None if no hackathon_id is provided.
    2. Query the Hackathon table by id.
    3. Return the Hackathon ORM instance or None if not found.

    Side Effects: None (read-only).
    Dependencies: app.models.Hackathon, app.database.get_db.
    Consumers: Internal helper used by assistant routes.
    """
    if not hackathon_id:
        return None

    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    return result.scalar_one_or_none()


# DEPRECATED: Replaced by client-side AgentLoop + POST /api/llm/chat.
# Kept for backward compat; remove after verifying new harness in production.
@router.post("/chat")
async def create_chat_message(
    request: Request,
    message: str,
    conversation_id: Optional[UUID] = None,
    hackathon_id: Optional[UUID] = None,
    model: str = "fast",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new chat message and start processing.

    Deprecated: Replaced by client-side AgentLoop + POST /api/llm/chat.
    Kept for backward compatibility.

    Behavior:
    1. Get or create an AssistantConversation for the user.
    2. Raise 404 if an existing conversation_id does not belong to the user.
    3. Save the user message as an AssistantMessage.
    4. Create a pending assistant response placeholder.
    5. Commit and return the conversation and message ids with status.

    Raises: HTTPException(404) if conversation not found or does not belong to user.
    Side Effects: Inserts AssistantConversation and AssistantMessage rows.
    Dependencies: app.models_assistant.AssistantConversation, app.models_assistant.AssistantMessage, app.models.Hackathon.
    Consumers: POST /api/chat, assistant chat (deprecated).
    """

    # Get or create conversation
    if conversation_id:
        result = await db.execute(
            select(AssistantConversation)
            .where(AssistantConversation.id == conversation_id)
            .where(AssistantConversation.user_id == current_user.id)
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        # Create new conversation
        conversation = AssistantConversation(
            id=uuid4(),
            user_id=current_user.id,
            hackathon_id=hackathon_id,
            expires_at=datetime.utcnow() + timedelta(days=30),
        )

        # Generate title from first message
        title = message[:50] + "..." if len(message) > 50 else message
        conversation.title = title

        db.add(conversation)
        await db.flush()

    # Get hackathon context
    hackathon = None
    if hackathon_id:
        result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
        hackathon = result.scalar_one_or_none()

    # Save user message
    user_msg = AssistantMessage(
        id=uuid4(),
        conversation_id=conversation.id,
        role=ConversationRole.USER,
        content=message,
    )
    db.add(user_msg)

    # Create placeholder for assistant response
    assistant_msg = AssistantMessage(
        id=uuid4(),
        conversation_id=conversation.id,
        role=ConversationRole.ASSISTANT,
        content="",
        status=AssistantMessageStatus.PENDING,
        model_used=model,  # Store selected model for streaming
    )
    db.add(assistant_msg)

    await db.commit()

    return {
        "conversation_id": str(conversation.id),
        "message_id": str(assistant_msg.id),
        "status": "processing",
        "model": model,
    }


async def get_current_user_sse(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current user from Authorization header or query param (for SSE).

    Behavior:
    1. Read the Bearer token from the Authorization header or query param.
    2. Raise 401 if the token is missing.
    3. Verify the access token and extract the user_id.
    4. Set the current user_id for RLS.
    5. Look up the User in the database.
    6. Return the User ORM instance.

    Raises: HTTPException(401) if token missing or invalid.
    Side Effects: Sets RLS user context via app.database.set_current_user_id.
    Dependencies: app.auth.verify_access_token, app.database.set_current_user_id, app.models.User.
    Consumers: Internal helper used by SSE streaming routes.
    """
    from app.database import set_current_user_id

    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
    else:
        token = request.query_params.get("token")

    if not token:
        raise HTTPException(status_code=401, detail="Missing authentication token")

    try:
        payload = verify_access_token(token)
        user_id = payload.get("sub")
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token: no user ID")

    set_current_user_id(user_id)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# DEPRECATED: Replaced by client-side AgentLoop. Remove after verifying new harness.
@router.get("/stream/{message_id}")
async def stream_response(
    message_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_sse),
):
    """Stream the assistant response for a message.

    Deprecated: Replaced by client-side AgentLoop. Kept for backward compat.

    Behavior:
    1. Load the assistant message and verify ownership via conversation user_id.
    2. Raise 404 if the message is not found or does not belong to the user.
    3. Return the existing content if the message is already completed.
    4. Build conversation context, history, and available tools.
    5. Stream LLM response chunks via SSE.
    6. Execute any tool calls and yield results.
    7. Persist final content and index for semantic search.
    8. Return a StreamingResponse.

    Raises: HTTPException(404) if message not found or does not belong to user.
    Side Effects: Mutates AssistantMessage content, status, tool_results; indexes message in vector store.
    Dependencies: app.assistant.context_builder.ContextBuilder, app.assistant.llm.llm_client, app.assistant.tools.ToolExecutor, app.assistant.embedder.embedder, app.assistant.vector_store.vector_store.
    Consumers: GET /api/stream/{message_id}, assistant streaming (deprecated).
    """

    # Get the message and verify ownership
    result = await db.execute(
        select(AssistantMessage)
        .join(AssistantConversation)
        .where(AssistantMessage.id == message_id)
        .where(AssistantConversation.user_id == current_user.id)
    )
    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    if message.status == AssistantMessageStatus.COMPLETED:
        # Already done, just return the content
        return {"content": message.content, "completed": True}

    # Get conversation context
    result = await db.execute(select(AssistantConversation).where(AssistantConversation.id == message.conversation_id))
    conversation = result.scalar_one()

    # Get hackathon
    hackathon = None
    if conversation.hackathon_id:
        result = await db.execute(select(Hackathon).where(Hackathon.id == conversation.hackathon_id))
        hackathon = result.scalar_one_or_none()

    async def generate_stream() -> AsyncGenerator[str, None]:
        """Generate streaming response.

        Yields SSE data chunks containing assistant content, tool calls, and
        completion signals. Also persists the final message content and indexes it
        for semantic search.

        Yields:
            Server-Sent Event formatted strings (data: <json>\n\n).
        """
        try:
            # Send initial heartbeat to confirm connection
            yield f"data: {json.dumps({'connected': True})}\n\n"

            # Update status to streaming
            message.status = AssistantMessageStatus.STREAMING
            await db.commit()

            # Build context
            builder = ContextBuilder(db)
            system_prompt = await builder.build_system_prompt(
                user=current_user,
                hackathon=hackathon,
                user_query=message.content,
            )

            # Get conversation history
            history = await builder.build_conversation_history(
                str(conversation.id),
                limit=10,
            )

            # Get available tools
            tools = get_tools_for_role(current_user.role)

            # Get user message content
            result = await db.execute(
                select(AssistantMessage)
                .where(AssistantMessage.conversation_id == conversation.id)
                .where(AssistantMessage.role == ConversationRole.USER)
                .order_by(AssistantMessage.created_at.desc())
                .limit(1)
            )
            user_message = result.scalar_one()

            # Build messages for LLM
            messages = [
                {"role": "system", "content": system_prompt},
                *[{"role": h["role"], "content": h["content"]} for h in history],
                {"role": "user", "content": user_message.content},
            ]

            # Debug: log what we're sending
            print(f"[DEBUG ASSISTANT] Sending {len(messages)} messages to LLM")
            print(f"[DEBUG ASSISTANT] Tools count: {len(tools) if tools else 0}")
            print(f"[DEBUG ASSISTANT] First message role: {messages[0]['role'] if messages else 'none'}")
            print(f"[DEBUG ASSISTANT] System prompt length: {len(system_prompt)}")

            # Determine which model to use
            from app.config import settings

            selected_model = None
            if message.model_used:
                if message.model_used == "thinking":
                    selected_model = settings.assistant_thinking_model
                elif message.model_used == "fast":
                    selected_model = settings.assistant_fast_model
                else:
                    selected_model = message.model_used  # Allow custom model names

            # Stream response
            full_content = []
            tool_calls = []

            async for chunk in llm_client.chat_completion_stream(
                messages=messages,
                tools=tools if tools else None,
                model=selected_model,
            ):
                # Check if chunk is an error from LLM
                if chunk.startswith('{"error":'):
                    yield f"data: {chunk}\n\n"
                    return

                # Try to parse tool calls (custom format from LLM)
                if chunk.startswith('{"tool":'):
                    try:
                        tool_data = json.loads(chunk)
                        tool_calls.append(tool_data)
                    except json.JSONDecodeError:
                        full_content.append(chunk)
                        # Use json.dumps for proper escaping
                        yield f"data: {json.dumps({'content': chunk})}\n\n"
                else:
                    full_content.append(chunk)
                    # Use json.dumps for proper escaping
                    yield f"data: {json.dumps({'content': chunk})}\n\n"

            # Execute any tool calls
            if tool_calls:
                tool_executor = ToolExecutor(db, current_user, hackathon)

                for tool_call in tool_calls:
                    tool_name = tool_call.get("tool")
                    parameters = tool_call.get("parameters", {})

                    # Verify permission
                    if not can_use_tool(current_user.role, tool_name):
                        tool_result = {"error": "Permission denied"}
                    else:
                        try:
                            result = await tool_executor.execute(tool_name, parameters)
                            tool_result = {"success": True, "result": result}
                        except Exception as e:
                            logger.error(f"Tool execution error: {e}")
                            tool_result = {"success": False, "error": str(e)}

                    # Yield tool result
                    yield f"data: {json.dumps({'tool_call': tool_name, 'result': tool_result})}\n\n"

                    # Add to tool results
                    if not message.tool_results:
                        message.tool_results = []
                    message.tool_results.append(
                        {
                            "tool": tool_name,
                            "result": tool_result,
                        }
                    )

            # Update message with final content
            message.content = "".join(full_content)
            message.status = AssistantMessageStatus.COMPLETED
            message.model_used = selected_model or llm_client.model
            await db.commit()

            # Index message for semantic search
            try:
                embedding = embedder.embed_text(message.content)
                await vector_store.index_message(
                    message_id=str(message.id),
                    conversation_id=str(conversation.id),
                    embedding=embedding,
                    content=message.content,
                    role="assistant",
                )
            except Exception as e:
                logger.error(f"Failed to index message: {e}")

            # Send completion signal
            yield f"data: {json.dumps({'completed': True})}\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}")
            message.status = AssistantMessageStatus.ERROR
            await db.commit()
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
    )


@router.get("/history")
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 20,
    offset: int = 0,
):
    """List user's conversation history.

    Behavior:
    1. Query AssistantConversation rows for the current user.
    2. Order by updated_at descending and apply pagination.
    3. Serialize each conversation to a summary dict.
    4. Return the list and total count.

    Side Effects: None (read-only).
    Dependencies: app.models_assistant.AssistantConversation.
    Consumers: GET /api/history, assistant conversation list.
    """

    result = await db.execute(
        select(AssistantConversation)
        .where(AssistantConversation.user_id == current_user.id)
        .order_by(AssistantConversation.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    conversations = result.scalars().all()

    return {
        "conversations": [
            {
                "id": str(c.id),
                "title": c.title or "New conversation",
                "hackathon_id": str(c.hackathon_id) if c.hackathon_id else None,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            }
            for c in conversations
        ],
        "total": len(conversations),
    }


@router.get("/history/{conversation_id}")
async def get_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific conversation with all messages.

    Behavior:
    1. Load the conversation by id and user_id.
    2. Raise 404 if the conversation is not found or does not belong to the user.
    3. Load all messages ordered by created_at.
    4. Return the conversation metadata and message list.

    Raises: HTTPException(404) if conversation not found or does not belong to user.
    Side Effects: None (read-only).
    Dependencies: app.models_assistant.AssistantConversation, app.models_assistant.AssistantMessage.
    Consumers: GET /api/history/{conversation_id}, assistant conversation detail.
    """

    result = await db.execute(
        select(AssistantConversation)
        .where(AssistantConversation.id == conversation_id)
        .where(AssistantConversation.user_id == current_user.id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get messages
    result = await db.execute(
        select(AssistantMessage)
        .where(AssistantMessage.conversation_id == conversation_id)
        .order_by(AssistantMessage.created_at)
    )
    messages = result.scalars().all()

    return {
        "id": str(conversation.id),
        "title": conversation.title,
        "hackathon_id": str(conversation.hackathon_id) if conversation.hackathon_id else None,
        "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
        "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
        "messages": [
            {
                "id": str(m.id),
                "role": m.role.value,
                "content": m.content,
                "tool_calls": m.tool_calls,
                "tool_results": m.tool_results,
                "status": m.status.value,
                "model": m.model_used,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
    }


@router.delete("/history/{conversation_id}")
async def delete_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a conversation and all its messages.

    Behavior:
    1. Load the conversation by id and user_id.
    2. Raise 404 if the conversation is not found or does not belong to the user.
    3. Delete associated messages from the vector store.
    4. Delete the conversation from the database and commit.
    5. Return a success dict.

    Raises: HTTPException(404) if conversation not found or does not belong to user.
    Side Effects: Deletes AssistantConversation row and vector store entries.
    Dependencies: app.models_assistant.AssistantConversation, app.assistant.vector_store.vector_store.
    Consumers: DELETE /api/history/{conversation_id}, assistant conversation management.
    """

    result = await db.execute(
        select(AssistantConversation)
        .where(AssistantConversation.id == conversation_id)
        .where(AssistantConversation.user_id == current_user.id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Delete from Qdrant
    try:
        await vector_store.delete_conversation_messages(str(conversation_id))
    except Exception as e:
        logger.error(f"Failed to delete messages from vector store: {e}")

    # Delete from database
    await db.delete(conversation)
    await db.commit()

    return {"success": True}


@router.get("/tools")
async def list_available_tools(
    current_user: User = Depends(get_current_user),
):
    """List tools available to the current user.

    Behavior:
    1. Get the tool definitions for the user's role.
    2. Return the role and available tools.

    Side Effects: None (read-only).
    Dependencies: app.assistant.permissions.get_tools_for_role.
    Consumers: GET /api/tools, assistant tool listing.
    """
    tools = get_tools_for_role(current_user.role)
    return {"role": current_user.role, "tools": tools}


# =============================================================================
# Builder Mode Endpoints
# =============================================================================

from app.assistant.context_builder import (
    build_plan_generation_prompt,
    build_project_generation_prompt,
    detect_build_intent,
)


@router.post("/detect-intent")
async def detect_intent(
    message: str,
    current_user: User = Depends(get_current_user),
):
    """Detect if user message indicates intent to build a project.

    Behavior:
    1. Call detect_build_intent on the raw message text.
    2. Return the intent flag, confidence score, and original message.

    Side Effects: None (read-only).
    Dependencies: app.assistant.context_builder.detect_build_intent.
    Consumers: POST /api/detect-intent, builder mode.
    """
    has_intent, confidence = detect_build_intent(message)

    return {
        "has_build_intent": has_intent,
        "confidence": confidence,
        "message": message,
    }


@router.post("/generate-plan")
async def generate_plan(
    description: str,
    hackathon_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a project plan from user description.

    Behavior:
    1. Load optional hackathon context and associated tracks.
    2. Build a plan generation prompt with description, hackathon name, and tracks.
    3. Call the LLM and attempt to parse JSON from the response.
    4. Add a generated UUID to the plan.
    5. Return the plan with a success flag, or an error dict on failure.

    Side Effects: None (read-only, LLM call only).
    Dependencies: app.assistant.context_builder.build_plan_generation_prompt, app.assistant.llm.llm_client, app.models.Hackathon, app.models.Track.
    Consumers: POST /api/generate-plan, builder mode.
    """
    import json

    # Get hackathon context
    hackathon = None
    tracks = []
    if hackathon_id:
        result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
        hackathon = result.scalar_one_or_none()

        if hackathon:
            # Get tracks
            from app.models import Track

            result = await db.execute(select(Track).where(Track.hackathon_id == hackathon_id))
            track_rows = result.scalars().all()
            tracks = [{"name": t.name, "description": t.description or ""} for t in track_rows]

    # Build prompt
    prompt = build_plan_generation_prompt(
        user_description=description,
        hackathon_name=hackathon.name if hackathon else None,
        tracks=tracks if tracks else None,
    )

    # Call LLM
    messages = [
        {
            "role": "system",
            "content": "You are a helpful AI that generates project plans. Always respond with valid JSON.",
        },
        {"role": "user", "content": prompt},
    ]

    try:
        response = await llm_client.chat_completion(
            messages=messages,
            temperature=0.7,
        )

        # Try to parse JSON from response
        content = response.get("content", "")

        # Extract JSON if wrapped in markdown
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        plan_data = json.loads(content)

        # Add generated ID
        from uuid import uuid4

        plan_data["id"] = str(uuid4())

        return {
            "plan": plan_data,
            "success": True,
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse plan JSON: {e}")
        return {
            "success": False,
            "error": "Failed to generate valid plan",
            "raw_response": content if "content" in locals() else None,
        }
    except Exception as e:
        logger.error(f"Error generating plan: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@router.post("/generate-project")
async def generate_project(
    request: GenerateProjectRequest,
    current_user: User = Depends(get_current_user),
):
    """Generate project files from a plan.

    Behavior:
    1. Convert the request plan to a dict.
    2. Build a project generation prompt with the plan and project type.
    3. Call the LLM and attempt to parse JSON from the response.
    4. Validate the response contains a files array.
    5. Auto-generate a README if missing.
    6. Return the files, README, and success flag, or an error dict on failure.

    Side Effects: None (read-only, LLM call only).
    Dependencies: app.assistant.context_builder.build_project_generation_prompt, app.assistant.llm.llm_client, app.schemas.builder.GenerateProjectRequest.
    Consumers: POST /api/generate-project, builder mode.
    """
    import json

    # Convert plan to dict
    plan_dict = request.plan.model_dump()

    # Build prompt
    prompt = build_project_generation_prompt(
        plan=plan_dict,
        project_type=request.projectType,
    )

    # Call LLM
    messages = [
        {
            "role": "system",
            "content": "You are a helpful AI that generates code. Always respond with valid JSON containing a 'files' array.",
        },
        {"role": "user", "content": prompt},
    ]

    try:
        response = await llm_client.chat_completion(
            messages=messages,
            temperature=0.7,
        )

        # Try to parse JSON from response
        content = response.get("content", "")

        # Extract JSON if wrapped in markdown
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        project_data = json.loads(content)

        # Ensure files array exists
        if "files" not in project_data:
            return {
                "success": False,
                "error": "Invalid response format: missing 'files' array",
            }

        # Generate README if not present
        has_readme = any(f.get("name") == "README.md" for f in project_data["files"])
        if not has_readme:
            readme_content = f"""# {plan_dict.get("name", "Project")}

Generated for this hackathon.

## Quick Start

1. Open the files in your code editor
2. Follow the setup instructions below
3. Start hacking!

## Files

"""
            for f in project_data["files"]:
                readme_content += f"- {f.get('name', 'file')} - {f.get('description', 'Project file')}\n"

            project_data["files"].append(
                {
                    "path": "README.md",
                    "name": "README.md",
                    "content": readme_content,
                    "language": "markdown",
                }
            )

        return {
            "files": project_data["files"],
            "readme": next((f["content"] for f in project_data["files"] if f["name"] == "README.md"), ""),
            "success": True,
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse project JSON: {e}")
        return {
            "success": False,
            "error": "Failed to generate valid project files",
            "raw_response": content if "content" in locals() else None,
        }
    except Exception as e:
        logger.error(f"Error generating project: {e}")
        return {
            "success": False,
            "error": str(e),
        }


# ── Tool Execution + RAG + Chat Log ──────────────────────────────────


class ExecuteToolRequest(BaseModel):
    """Request body for executing an assistant tool.

    Behavior:
    1. Define the schema for a tool execution request.
    2. Provide tool_name and parameters fields.

    Side Effects: None (schema definition).
    Dependencies: pydantic.BaseModel.
    Consumers: POST /api/execute-tool, assistant tool execution.
    """

    tool_name: str
    parameters: dict = {}


@router.post("/execute-tool")
async def execute_tool(
    request: ExecuteToolRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Execute a single tool. Auth and permission checked server-side.

    Behavior:
    1. Verify the user's role can use the requested tool.
    2. Raise 403 if the tool is not allowed for the role.
    3. Execute the tool via ToolExecutor.
    4. Return the result under the "result" key.
    5. Raise 500 if tool execution fails unexpectedly.

    Raises: HTTPException(403) if tool not allowed for role. HTTPException(500) if tool execution fails.
    Side Effects: May mutate database state depending on the tool executed.
    Dependencies: app.assistant.permissions.can_use_tool, app.assistant.tools.ToolExecutor.
    Consumers: POST /api/execute-tool, assistant tool execution.
    """
    if not can_use_tool(current_user.role, request.tool_name):
        raise HTTPException(
            status_code=403,
            detail=f"Tool '{request.tool_name}' not allowed for your role",
        )

    try:
        executor = ToolExecutor(db, current_user, None)
        result = await executor.execute(request.tool_name, request.parameters)
        return {"result": result}
    except Exception as e:
        logger.error(f"Tool execution error ({request.tool_name}): {e}")
        raise HTTPException(status_code=500, detail=str(e))


class RAGSearchRequest(BaseModel):
    """Request body for RAG document search.

    Behavior:
    1. Define the schema for a RAG search request.
    2. Provide a query field.

    Side Effects: None (schema definition).
    Dependencies: pydantic.BaseModel.
    Consumers: POST /api/rag-search, assistant document search.
    """

    query: str


@router.post("/rag-search")
async def rag_search(
    request: RAGSearchRequest,
    current_user: User = Depends(get_current_user),
    hackathon: Optional[Hackathon] = Depends(get_hackathon),
):
    """Search Qdrant for relevant hackathon documents.

    Behavior:
    1. Embed the query text.
    2. Search the vector store for matching documents.
    3. Apply role-based and hackathon-scoped filters.
    4. Return the matching documents with relevance scores.

    Side Effects: None (read-only).
    Dependencies: app.assistant.embedder.embedder, app.assistant.vector_store.vector_store.
    Consumers: POST /api/rag-search, assistant document search.
    """
    embedding = embedder.embed_text(request.query)
    results = await vector_store.search_documents(
        query_embedding=embedding,
        hackathon_id=str(hackathon.id) if hackathon else None,
        role=current_user.role,
        limit=5,
        score_threshold=0.2,
    )

    return {
        "documents": [
            {
                "content": r.get("content", ""),
                "title": r.get("title", ""),
                "doc_type": r.get("doc_type", ""),
                "score": r.get("score", 0),
            }
            for r in results
        ]
    }


class ChatLogRequest(BaseModel):
    """Request body for persisting a browser agent conversation.

    Behavior:
    1. Define the schema for a chat log persistence request.
    2. Provide messages and optional conversation_id fields.

    Side Effects: None (schema definition).
    Dependencies: pydantic.BaseModel.
    Consumers: POST /api/chat-log, assistant chat logging.
    """

    messages: list[dict]
    conversation_id: Optional[str] = None


@router.post("/chat-log")
async def chat_log(
    request: ChatLogRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Persist a conversation from the browser agent.

    Behavior:
    1. Create a new conversation if no conversation_id is provided.
    2. Verify an existing conversation_id belongs to the current user.
    3. Raise 404 if the conversation is not found.
    4. Persist each message as an AssistantMessage row.
    5. Commit and return the conversation_id with status "saved".

    Raises: HTTPException(404) if conversation not found or does not belong to user.
    Side Effects: Inserts AssistantConversation and AssistantMessage rows.
    Dependencies: app.models_assistant.AssistantConversation, app.models_assistant.AssistantMessage.
    Consumers: POST /api/chat-log, assistant chat logging.
    """
    conversation_id = request.conversation_id

    if not conversation_id:
        conv = AssistantConversation(
            user_id=current_user.id,
            title=(request.messages[0].get("content", "")[:100] if request.messages else "New conversation"),
        )
        db.add(conv)
        await db.flush()
        conversation_id = str(conv.id)
    else:
        result = await db.execute(
            select(AssistantConversation).where(
                AssistantConversation.id == UUID(conversation_id),
                AssistantConversation.user_id == current_user.id,
            )
        )
        conv = result.scalar_one_or_none()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

    for msg in request.messages:
        db_msg = AssistantMessage(
            conversation_id=UUID(conversation_id),
            role=ConversationRole(msg.get("role", "user")),
            content=msg.get("content", ""),
            status=AssistantMessageStatus.COMPLETED,
        )
        db.add(db_msg)

    await db.commit()
    return {"conversation_id": conversation_id, "status": "saved"}


# ── LLM Proxy (mounted at /api/llm in main.py, not on the assistant router) ──


class LLMChatRequest(BaseModel):
    """Request body for LLM chat proxy.

    Behavior:
    1. Define the schema for an LLM chat proxy request.
    2. Provide messages and model fields.

    Side Effects: None (schema definition).
    Dependencies: pydantic.BaseModel.
    Consumers: POST /api/llm/chat (mounted in main.py), LLM proxy.
    """

    messages: list[dict]
    model: str = "fast"


async def llm_chat_proxy(
    request: LLMChatRequest,
    current_user: User = Depends(get_current_user),
):
    """Proxy LLM chat requests to Poolside.

    Strips client tool definitions and injects server-authorized ones based
    on the user's role. Validates JWT token.

    Behavior:
    1. Get server-authorized tools for the user's role.
    2. Determine the model based on the request model selector.
    3. Call the LLM with messages and authorized tools.
    4. Return the LLM response content.
    5. Raise 502 if the LLM service returns an error.

    Raises: HTTPException(502) if LLM service returns an error.
    Side Effects: None (read-only proxy).
    Dependencies: app.assistant.permissions.get_tools_for_role, app.assistant.llm.llm_client.
    Consumers: POST /api/llm/chat (mounted in main.py), LLM proxy.
    """
    # Inject server-authorized tools — strip whatever client sent.
    # get_tools_for_role() returns OpenAI format:
    #   [{"type":"function","function":{"name":...,"description":...,"parameters":...}}]
    tool_defs = get_tools_for_role(current_user.role)

    # Determine model
    if request.model == "fast":
        model = settings.assistant_fast_model or settings.llm_model
    elif request.model == "thinking":
        model = settings.assistant_thinking_model or settings.llm_model
    else:
        model = settings.llm_model

    if not model:
        raise HTTPException(status_code=500, detail="LLM provider not configured.")

    client = get_llm_client(model)

    try:
        response = await client.chat_completion(
            messages=request.messages,
            tools=tool_defs if tool_defs else None,
            temperature=0.7,
            max_tokens=1500,
            stream=False,
        )
        return response
    except Exception as e:
        logger.error(f"LLM proxy error: {e}")
        raise HTTPException(status_code=502, detail=f"LLM service error: {str(e)}")


# ── Document Upload / Indexing ──

storage_service = StorageService()


ALLOWED_DOC_TYPES = {
    "text/plain",
    "text/markdown",
    "application/pdf",
    "application/octet-stream",
}
MAX_DOC_SIZE = 10 * 1024 * 1024  # 10 MB


def _extract_text_from_pdf(contents: bytes) -> str:
    """Extract plain text from a PDF byte buffer.

    Raises:
        ValueError: If pypdf is not installed or parsing fails.
    """
    try:
        from pypdf import PdfReader
        from io import BytesIO

        reader = PdfReader(BytesIO(contents))
        parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
        return "\n".join(parts)
    except ImportError as e:
        raise ValueError("PDF parsing requires pypdf. Install it and rebuild the container.") from e
    except Exception as e:
        raise ValueError(f"Failed to parse PDF: {e}") from e


def _extract_text(filename: str, contents: bytes, content_type: str) -> str:
    """Extract plain text from an uploaded file depending on its type.

    Raises:
        ValueError: If the file type is unsupported or parsing fails.
    """
    lowered = filename.lower()
    if content_type == "application/pdf" or lowered.endswith(".pdf"):
        return _extract_text_from_pdf(contents)
    if lowered.endswith((".txt", ".md", ".markdown", ".rst")):
        return contents.decode("utf-8", errors="replace")
    # Try plain text for unknown types
    try:
        return contents.decode("utf-8", errors="replace")
    except Exception as e:
        raise ValueError(f"Unsupported file type: {content_type}. Upload .txt, .md, or .pdf") from e


@router.post("/hackathons/{hackathon_id}/documents")
async def upload_document(
    hackathon_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_organizer),
):
    """Upload a document, store it in MinIO, and index it for the assistant.

    Behavior:
    1. Validate the hackathon exists.
    2. Read the uploaded file and validate size/type.
    3. Upload the raw file to MinIO via StorageService.
    4. Extract plain text from the file.
    5. Chunk, embed, and index the text into Qdrant.
    6. Persist metadata in the ``assistant_documents`` table.
    7. Return the created document metadata.

    Raises:
        HTTPException(404): If hackathon not found.
        HTTPException(413): If file exceeds 10MB.
        HTTPException(400): If file type is unsupported or text extraction fails.
        HTTPException(502): If storage or indexing fails.
    """
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    contents = await file.read()
    if len(contents) > MAX_DOC_SIZE:
        raise HTTPException(status_code=413, detail=f"File exceeds 10MB limit ({len(contents)} bytes)")

    detected = file.content_type or "application/octet-stream"
    try:
        import magic

        detected = magic.from_buffer(contents, mime=True)
    except Exception:
        pass

    if detected not in ALLOWED_DOC_TYPES and not file.filename.lower().endswith((".txt", ".md", ".markdown", ".pdf")):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {detected}. Allowed: text/plain, text/markdown, application/pdf",
        )

    # Upload to MinIO
    try:
        upload_result = await storage_service.upload_generic(
            file=file,
            folder="assistant-documents",
            allowed_types=ALLOWED_DOC_TYPES,
            max_size=MAX_DOC_SIZE,
            contents=contents,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Storage error: {e}")

    # Extract text
    try:
        text = _extract_text(file.filename or "document", contents, detected)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Document appears to be empty")

    # Index
    try:
        indexer = DocumentIndexer(db)
        index_result = await indexer.index_uploaded_document(
            hackathon=hackathon,
            filename=file.filename or "document",
            content=text,
            s3_url=upload_result.get("url"),
            s3_key=upload_result.get("key"),
        )
    except Exception as e:
        logger.error(f"Document indexing failed: {e}")
        raise HTTPException(status_code=502, detail=f"Indexing failed: {e}")

    return {
        "document_id": index_result["document_id"],
        "filename": file.filename,
        "chunk_count": index_result["chunk_count"],
        "s3_url": upload_result.get("url"),
    }


@router.get("/hackathons/{hackathon_id}/documents")
async def list_documents(
    hackathon_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List uploaded documents indexed for a hackathon.

    Behavior:
    1. Query ``assistant_documents`` for rows matching the hackathon with type ``resources``.
    2. Return a list with id, filename, chunk_count, s3_url, and created_at.

    Raises: HTTPException(404) if hackathon not found.
    Side Effects: None (read-only).
    """
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    docs_result = await db.execute(
        select(AssistantDocument)
        .where(AssistantDocument.hackathon_id == hackathon_id)
        .where(AssistantDocument.doc_type == DocumentType.RESOURCES)
        .order_by(AssistantDocument.created_at.desc())
    )
    docs = docs_result.scalars().all()

    return {
        "documents": [
            {
                "id": str(d.id),
                "filename": d.doc_metadata.get("filename", d.title),
                "chunk_count": d.doc_metadata.get("chunk_count", 0),
                "s3_url": d.doc_metadata.get("s3_url"),
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in docs
        ]
    }


@router.delete("/hackathons/{hackathon_id}/documents/{doc_id}")
async def delete_document(
    hackathon_id: UUID,
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_organizer),
):
    """Delete an uploaded document and its indexed chunks.

    Behavior:
    1. Verify the hackathon exists.
    2. Use DocumentIndexer to delete the document from Qdrant and PostgreSQL.
    3. Return 204 on success, 404 if the document is not found.

    Raises:
        HTTPException(404): If hackathon or document not found.
        HTTPException(502): If deletion from Qdrant fails.
    """
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    indexer = DocumentIndexer(db)
    deleted = await indexer.delete_uploaded_document(doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")

    return {"status": "deleted"}


@router.post("/index-resources")
async def index_all_resources(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_organizer),
):
    """Re-index all published content pages for the AI assistant.

    Organizer-only endpoint that rebuilds the assistant knowledge base
    for all published site pages (resources, guides, etc.).

    Behavior:
    1. Query all published ContentPage rows.
    2. For each page, re-index into Qdrant via DocumentIndexer.
    3. Return the count of indexed pages.

    Raises: None
    Side Effects: Writes/updates points in Qdrant and AssistantDocument rows.
    """
    from app.assistant.site_pages import index_content_page

    result = await db.execute(select(ContentPage).where(ContentPage.is_published.is_(True)))
    pages = result.scalars().all()

    indexed_count = 0
    for page in pages:
        try:
            await index_content_page(page, db)
            indexed_count += 1
        except Exception as e:
            logger.error(f"Failed to index page '{page.slug}': {e}")

    return {"indexed_count": indexed_count, "total_pages": len(pages)}
