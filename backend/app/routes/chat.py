"""Real-time chat routes for participant-to-organizer messaging.

Routes support sending messages, retrieving chat history, an organizer-wide
view, and marking messages as read.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import require_clerk_user_with_db
from app.database import get_db
from app.models import Hackathon, UserRole
from app.services.chat_service import ChatService

router = APIRouter(prefix="/api", tags=["chat"])


class SendMessageRequest(BaseModel):
    """Request body for sending a chat message within a hackathon."""

    message: str
    recipient_id: str | None = None


@router.post("/hackathons/{hackathon_id}/chat")
async def send_chat_message(
    hackathon_id: str,
    body: SendMessageRequest,
    auth: dict = Depends(require_clerk_user_with_db),
    db: AsyncSession = Depends(get_db),
):
    """Send a chat message to organizers (or a specific recipient) within a hackathon.

    Behavior:
    1. Verify the hackathon exists.
    2. Verify the sender is a participant (accepted/checked_in) or an organizer.
    3. Instantiate ChatService and persist the message.
    4. Return the serialized message with id, sender_id, message, and created_at.

    Raises: HTTPException(404) if hackathon not found. HTTPException(403) if sender is not a participant or organizer.
    Side Effects: Inserts a ChatMessage row.
    Dependencies: app.services.chat_service.ChatService.
    Consumers: POST /api/hackathons/{id}/chat, participant messaging UI.
    """
    user = auth["user"]
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    service = ChatService()
    is_participant = await service.is_hackathon_participant(db, uuid.UUID(hackathon_id), user.id)
    is_organizer = user.role == UserRole.organizer
    is_co_organizer = False

    if not is_organizer:
        from app.models import HackathonOrganizer

        co_result = await db.execute(
            select(HackathonOrganizer).where(
                HackathonOrganizer.hackathon_id == hackathon_id,
                HackathonOrganizer.user_id == user.id,
            )
        )
        is_co_organizer = co_result.scalar_one_or_none() is not None

    if not is_participant and not is_organizer and not is_co_organizer:
        raise HTTPException(status_code=403, detail="Only participants and organizers can use chat")

    msg = await service.send_message(
        db,
        hackathon_id=uuid.UUID(hackathon_id),
        sender_id=user.id,
        recipient_id=body.recipient_id,
        message=body.message,
    )

    return {
        "id": str(msg.id),
        "hackathon_id": str(msg.hackathon_id),
        "sender_id": msg.sender_id,
        "recipient_id": msg.recipient_id,
        "message": msg.message,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
        "read_at": msg.read_at.isoformat() if msg.read_at else None,
    }


@router.get("/hackathons/{hackathon_id}/chat")
async def get_chat_history(
    hackathon_id: str,
    auth: dict = Depends(require_clerk_user_with_db),
    db: AsyncSession = Depends(get_db),
):
    """Get chat history for the current user within a hackathon.

    Behavior:
    1. Verify the hackathon exists.
    2. Instantiate ChatService and load messages where the user is sender or recipient.
    3. Return a serialized list of messages.

    Raises: HTTPException(404) if hackathon not found.
    Side Effects: None (read-only).
    Dependencies: app.services.chat_service.ChatService.
    Consumers: GET /api/hackathons/{id}/chat, participant messaging UI.
    """
    user = auth["user"]
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    service = ChatService()
    messages = await service.get_chat_history(db, uuid.UUID(hackathon_id), user.id)

    return [
        {
            "id": str(m.id),
            "hackathon_id": str(m.hackathon_id),
            "sender_id": m.sender_id,
            "recipient_id": m.recipient_id,
            "message": m.message,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "read_at": m.read_at.isoformat() if m.read_at else None,
        }
        for m in messages
    ]


@router.get("/hackathons/{hackathon_id}/organizer-chat")
async def get_organizer_chat(
    hackathon_id: str,
    auth: dict = Depends(require_clerk_user_with_db),
    db: AsyncSession = Depends(get_db),
):
    """Get all chat messages for a hackathon (organizer view).

    Behavior:
    1. Verify the hackathon exists.
    2. Verify the caller is an organizer or co-organizer.
    3. Instantiate ChatService and load all messages scoped to the hackathon.
    4. Return a serialized list of messages.

    Raises: HTTPException(404) if hackathon not found. HTTPException(403) if not organizer.
    Side Effects: None (read-only).
    Dependencies: app.services.chat_service.ChatService, app.models.HackathonOrganizer.
    Consumers: GET /api/hackathons/{id}/organizer-chat, organizer messaging dashboard.
    """
    user = auth["user"]
    result = await db.execute(select(Hackathon).where(Hackathon.id == hackathon_id))
    hackathon = result.scalar_one_or_none()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    is_organizer = user.role == UserRole.organizer and hackathon.organizer_id == user.id
    is_co_organizer = False
    if not is_organizer:
        from app.models import HackathonOrganizer

        co_result = await db.execute(
            select(HackathonOrganizer).where(
                HackathonOrganizer.hackathon_id == hackathon_id,
                HackathonOrganizer.user_id == user.id,
            )
        )
        is_co_organizer = co_result.scalar_one_or_none() is not None

    if not is_organizer and not is_co_organizer:
        raise HTTPException(status_code=403, detail="Only organizers can view all chat messages")

    service = ChatService()
    messages = await service.get_organizer_chat_view(db, uuid.UUID(hackathon_id))

    return [
        {
            "id": str(m.id),
            "hackathon_id": str(m.hackathon_id),
            "sender_id": m.sender_id,
            "recipient_id": m.recipient_id,
            "message": m.message,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "read_at": m.read_at.isoformat() if m.read_at else None,
        }
        for m in messages
    ]


@router.post("/chat/{message_id}/read")
async def mark_message_read(
    message_id: str,
    auth: dict = Depends(require_clerk_user_with_db),
    db: AsyncSession = Depends(get_db),
):
    """Mark a chat message as read.

    Behavior:
    1. Instantiate ChatService and attempt to mark the message as read.
    2. Return 404 if the message does not exist.
    3. Return the updated message with read_at timestamp.

    Raises: HTTPException(404) if message not found.
    Side Effects: Updates the ChatMessage row.
    Dependencies: app.services.chat_service.ChatService.
    Consumers: POST /api/chat/{message_id}/read, messaging UI read receipts.
    """
    service = ChatService()
    msg = await service.mark_as_read(db, uuid.UUID(message_id), auth["user"].id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    return {
        "id": str(msg.id),
        "hackathon_id": str(msg.hackathon_id),
        "sender_id": msg.sender_id,
        "recipient_id": msg.recipient_id,
        "message": msg.message,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
        "read_at": msg.read_at.isoformat() if msg.read_at else None,
    }
