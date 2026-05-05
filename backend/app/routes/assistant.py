"""API routes for the AI assistant."""

import json
import logging
from datetime import datetime, timedelta
from typing import AsyncGenerator, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.context_builder import ContextBuilder
from app.assistant.embedder import embedder
from app.assistant.llm import llm_client
from app.assistant.permissions import can_use_tool, get_tools_for_role
from app.assistant.tools import ToolExecutor
from app.assistant.vector_store import vector_store
from app.database import get_db
from app.models import Hackathon, User
from app.models_assistant import (
    AssistantConversation,
    AssistantMessage,
    AssistantMessageStatus,
    ConversationRole,
)
from app.routes.auth import get_current_user
from app.schemas.builder import (
    GenerateProjectRequest,
    GenerateProjectResponse,
    ProjectPlanSchema,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["assistant"])


async def get_hackathon(
    hackathon_id: Optional[UUID],
    db: AsyncSession = Depends(get_db),
) -> Optional[Hackathon]:
    """Get hackathon by ID if provided."""
    if not hackathon_id:
        return None

    result = await db.execute(
        select(Hackathon).where(Hackathon.id == hackathon_id)
    )
    return result.scalar_one_or_none()


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
    """Create a new chat message and start processing."""

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
        result = await db.execute(
            select(Hackathon).where(Hackathon.id == hackathon_id)
        )
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
    """Get current user from either Authorization header or query param (for SSE). Supports Clerk tokens."""
    from app.clerk_auth import is_clerk_token, decode_clerk_token, extract_clerk_user_id
    from app.auth import decode_token
    from app.database import set_current_user_id

    # Try header first
    auth_header = request.headers.get("Authorization")
    token = None

    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]  # Remove "Bearer " prefix
    else:
        # Try query parameter (for EventSource which can't set headers)
        token = request.query_params.get("token")

    if not token:
        raise HTTPException(status_code=401, detail="Missing authentication token")

    user_id = None
    user_email = None
    user_name = None

    # Try Clerk token first
    if is_clerk_token(token):
        try:
            payload = await decode_clerk_token(token)
            user_id = extract_clerk_user_id(payload)
            user_email = payload.get("email") or payload.get("public_metadata", {}).get("email")
            user_name = payload.get("name") or payload.get("public_metadata", {}).get("name")
        except ValueError as e:
            raise HTTPException(status_code=401, detail=f"Invalid Clerk token: {e}")
    else:
        # Fall back to internal JWT
        try:
            payload = decode_token(token)
            user_id = payload.get("sub")
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid token")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token: no user ID")

    # Set RLS context
    set_current_user_id(user_id)

    # Look up user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    # Auto-create user for Clerk tokens
    if not user and is_clerk_token(token) and user_email:
        user = User(
            id=user_id,
            email=user_email,
            name=user_name or user_email.split("@")[0],
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.get("/stream/{message_id}")
async def stream_response(
    message_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_sse),
):
    """Stream the assistant response for a message."""

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
    result = await db.execute(
        select(AssistantConversation)
        .where(AssistantConversation.id == message.conversation_id)
    )
    conversation = result.scalar_one()

    # Get hackathon
    hackathon = None
    if conversation.hackathon_id:
        result = await db.execute(
            select(Hackathon).where(Hackathon.id == conversation.hackathon_id)
        )
        hackathon = result.scalar_one_or_none()

    async def generate_stream() -> AsyncGenerator[str, None]:
        """Generate streaming response."""
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
                *[{ "role": h["role"], "content": h["content"] } for h in history],
                {"role": "user", "content": user_message.content},
            ]

            # Debug: log what we're sending
            import json as json_lib
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
                if chunk.startswith("{\"tool\":"):
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
                    message.tool_results.append({
                        "tool": tool_name,
                        "result": tool_result,
                    })

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
    """List user's conversation history."""

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
    """Get a specific conversation with all messages."""

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
    """Delete a conversation and all its messages."""

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
    """List tools available to the current user."""
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
    """Detect if user message indicates intent to build a project."""
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
    """Generate a project plan from user description."""
    import json

    # Get hackathon context
    hackathon = None
    tracks = []
    if hackathon_id:
        result = await db.execute(
            select(Hackathon).where(Hackathon.id == hackathon_id)
        )
        hackathon = result.scalar_one_or_none()

        if hackathon:
            # Get tracks
            from app.models import Track
            result = await db.execute(
                select(Track).where(Track.hackathon_id == hackathon_id)
            )
            track_rows = result.scalars().all()
            tracks = [
                {"name": t.name, "description": t.description or ""}
                for t in track_rows
            ]

    # Build prompt
    prompt = build_plan_generation_prompt(
        user_description=description,
        hackathon_name=hackathon.name if hackathon else None,
        tracks=tracks if tracks else None,
    )

    # Call LLM
    messages = [
        {"role": "system", "content": "You are a helpful AI that generates project plans. Always respond with valid JSON."},
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
            "raw_response": content if 'content' in locals() else None,
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
    """Generate project files from a plan."""
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
        {"role": "system", "content": "You are a helpful AI that generates code. Always respond with valid JSON containing a 'files' array."},
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
            readme_content = f"""# {plan_dict.get('name', 'Project')}

Generated for RowdyHacks hackathon.

## Quick Start

1. Open the files in your code editor
2. Follow the setup instructions below
3. Start hacking!

## Files

"""
            for f in project_data["files"]:
                readme_content += f"- {f.get('name', 'file')} - {f.get('description', 'Project file')}\n"

            project_data["files"].append({
                "path": "README.md",
                "name": "README.md",
                "content": readme_content,
                "language": "markdown",
            })

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
            "raw_response": content if 'content' in locals() else None,
        }
    except Exception as e:
        logger.error(f"Error generating project: {e}")
        return {
            "success": False,
            "error": str(e),
        }
