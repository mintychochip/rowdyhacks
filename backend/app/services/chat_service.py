"""Real-time chat service for participant-to-organizer messaging.

Provides message creation, retrieval, and read receipt tracking scoped
by hackathon. Messages can be sent by participants to organizers or
vice-versa.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ChatMessage, Registration, RegistrationStatus


class ChatService:
    """Service for hackathon-scoped chat between participants and organizers."""

    async def send_message(
        self,
        db: AsyncSession,
        hackathon_id: uuid.UUID,
        sender_id: str,
        recipient_id: str | None,
        message: str,
    ) -> ChatMessage:
        """Send a chat message within a hackathon.

        Behavior:
        1. Build a ChatMessage record with the provided fields.
        2. Persist and refresh the record.
        3. Return the created ChatMessage.

        Raises: None
        Side Effects: Inserts a ChatMessage row.
        Dependencies: app.models.ChatMessage.
        Consumers: POST /api/hackathons/{id}/chat route.
        """
        chat = ChatMessage(
            hackathon_id=hackathon_id,
            sender_id=sender_id,
            recipient_id=recipient_id,
            message=message,
        )
        db.add(chat)
        await db.commit()
        await db.refresh(chat)
        return chat

    async def get_chat_history(
        self,
        db: AsyncSession,
        hackathon_id: uuid.UUID,
        user_id: str,
    ) -> list[ChatMessage]:
        """Get chat history for a specific user in a hackathon.

        Behavior:
        1. Query ChatMessage rows scoped to the hackathon where the user is
           either the sender or the recipient.
        2. Order by created_at descending.
        3. Return the list of messages.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models.ChatMessage, sqlalchemy.select.
        Consumers: GET /api/hackathons/{id}/chat route.
        """
        result = await db.execute(
            select(ChatMessage)
            .where(
                ChatMessage.hackathon_id == hackathon_id,
                (ChatMessage.sender_id == user_id) | (ChatMessage.recipient_id == user_id),
            )
            .order_by(desc(ChatMessage.created_at))
        )
        return result.scalars().all()

    async def get_organizer_chat_view(
        self,
        db: AsyncSession,
        hackathon_id: uuid.UUID,
    ) -> list[ChatMessage]:
        """Get all messages for a hackathon (organizer view).

        Behavior:
        1. Query all ChatMessage rows scoped to the hackathon.
        2. Order by created_at descending.
        3. Return the full list of messages.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models.ChatMessage, sqlalchemy.select.
        Consumers: GET /api/hackathons/{id}/organizer-chat route.
        """
        result = await db.execute(
            select(ChatMessage).where(ChatMessage.hackathon_id == hackathon_id).order_by(desc(ChatMessage.created_at))
        )
        return result.scalars().all()

    async def mark_as_read(
        self,
        db: AsyncSession,
        message_id: uuid.UUID,
        reader_id: str,
    ) -> ChatMessage | None:
        """Mark a chat message as read.

        Behavior:
        1. Load the ChatMessage by ID.
        2. Return None if the message does not exist.
        3. Set ``read_at`` to the current UTC time if not already set.
        4. Commit and refresh.
        5. Return the updated ChatMessage.

        Raises: None
        Side Effects: Updates the ChatMessage row.
        Dependencies: app.models.ChatMessage.
        Consumers: POST /api/chat/{message_id}/read route.
        """
        result = await db.execute(select(ChatMessage).where(ChatMessage.id == message_id))
        message = result.scalar_one_or_none()
        if not message:
            return None

        if message.read_at is None:
            message.read_at = datetime.now(UTC)
            await db.commit()
            await db.refresh(message)

        return message

    async def is_hackathon_participant(
        self,
        db: AsyncSession,
        hackathon_id: uuid.UUID,
        user_id: str,
    ) -> bool:
        """Check whether a user has an accepted or checked-in registration.

        Behavior:
        1. Query Registration for a matching hackathon and user.
        2. Require status to be ``accepted`` or ``checked_in``.
        3. Return True if a matching row exists, otherwise False.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.models.Registration, app.models.RegistrationStatus.
        """
        result = await db.execute(
            select(Registration).where(
                Registration.hackathon_id == hackathon_id,
                Registration.user_id == user_id,
                Registration.status.in_([RegistrationStatus.accepted, RegistrationStatus.checked_in]),
            )
        )
        return result.scalar_one_or_none() is not None
