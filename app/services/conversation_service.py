import uuid
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.models.conversation import Conversation, ConversationStatus
from app.models.message import Message, MessageRole, MessageType
from app.models.platform_identity import Platform

logger = logging.getLogger("bergie")

# A conversation is considered stale after this much inactivity
CONVERSATION_TIMEOUT_HOURS = 24


# ── Conversation lookup ────────────────────────────────────────────────────

def get_active_conversation(
    db: Session,
    user_id: uuid.UUID,
    platform: Platform,
    platform_thread_id: str,
) -> Conversation | None:
    """
    Find an open conversation for this user on this platform.
    Returns None if no active conversation exists OR if the last
    message was more than CONVERSATION_TIMEOUT_HOURS ago.
    """
    stmt = (
        select(Conversation)
        .where(
            Conversation.user_id == user_id,
            Conversation.platform == platform,
            Conversation.platform_thread_id == platform_thread_id,
            Conversation.status == ConversationStatus.ACTIVE,
        )
        .order_by(desc(Conversation.created_at))
        .limit(1)
    )
    conversation = db.scalar(stmt)

    if not conversation:
        return None

    # Check if the conversation has timed out
    # We normalise both sides to naive UTC to handle SQLite (naive)
    # and PostgreSQL (aware) returning different datetime types
    cutoff = datetime.now(timezone.utc) - timedelta(hours=CONVERSATION_TIMEOUT_HOURS)
    updated = conversation.updated_at
    if updated.tzinfo is None:
        # SQLite returns naive datetimes — compare naive vs naive
        cutoff = cutoff.replace(tzinfo=None)
    if updated < cutoff:
        logger.info(f"Conversation {conversation.id} timed out — closing")
        conversation.status = ConversationStatus.CLOSED
        db.flush()
        return None

    return conversation


def get_or_create_conversation(
    db: Session,
    user_id: uuid.UUID,
    platform: Platform,
    platform_thread_id: str,
) -> tuple[Conversation, bool]:
    """
    Returns the active conversation, or creates a new one.
    Returns (conversation, created).
    """
    existing = get_active_conversation(db, user_id, platform, platform_thread_id)
    if existing:
        return existing, False

    conversation = Conversation(
        user_id=user_id,
        platform=platform,
        platform_thread_id=platform_thread_id,
        status=ConversationStatus.ACTIVE,
    )
    db.add(conversation)
    db.flush()
    logger.info(f"Created new conversation: {conversation.id} for user {user_id} on {platform}")
    return conversation, True


def close_conversation(db: Session, conversation_id: uuid.UUID) -> None:
    """Manually close a conversation."""
    conversation = db.get(Conversation, conversation_id)
    if conversation:
        conversation.status = ConversationStatus.CLOSED
        logger.info(f"Closed conversation: {conversation_id}")


def escalate_conversation(
    db: Session,
    conversation_id: uuid.UUID,
    notes: str | None = None,
) -> None:
    """Mark a conversation as needing a human agent."""
    conversation = db.get(Conversation, conversation_id)
    if conversation:
        conversation.status = ConversationStatus.ESCALATED
        conversation.agent_notes = notes
        logger.info(f"Escalated conversation: {conversation_id}")


# ── Message operations ─────────────────────────────────────────────────────

def save_message(
    db: Session,
    conversation_id: uuid.UUID,
    role: MessageRole,
    content: str,
    message_type: MessageType = MessageType.TEXT,
    ai_metadata: dict | None = None,
    rag_sources: list | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
) -> Message:
    # Compute next sequence number for this conversation
    from sqlalchemy import func
    current_max = db.scalar(
        select(func.max(Message.sequence)).where(
            Message.conversation_id == conversation_id
        )
    )
    next_seq = (current_max or 0) + 1

    message = Message(
        conversation_id=conversation_id,
        sequence=next_seq,
        role=role,
        content=content,
        message_type=message_type,
        ai_metadata=ai_metadata,
        rag_sources=rag_sources,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        delivered=True,
    )
    db.add(message)
    db.flush()
    logger.debug(f"Saved {role} message (seq={next_seq}) to conversation {conversation_id}")
    return message


def get_conversation_history(
    db: Session,
    conversation_id: uuid.UUID,
    limit: int = 20,
) -> list[Message]:
    """
    Retrieve the last N messages in chronological order (oldest first).
    Uses sequence as a stable tiebreaker — guaranteed insertion order
    regardless of timestamp precision (critical for SQLite in tests).
    """
    # Subquery: get the most recent `limit` messages by sequence
    subq = (
        select(Message.id)
        .where(Message.conversation_id == conversation_id)
        .order_by(desc(Message.sequence))
        .limit(limit)
        .subquery()
    )
    # Fetch those messages in correct chronological order
    stmt = (
        select(Message)
        .where(Message.id.in_(select(subq)))
        .order_by(Message.sequence.asc())
    )
    return list(db.scalars(stmt).all())


def get_history_for_claude(
    db: Session,
    conversation_id: uuid.UUID,
    limit: int = 20,
) -> list[dict]:
    """
    Format conversation history as Claude API expects it:
    [
        {"role": "user", "content": "What courses do you offer?"},
        {"role": "assistant", "content": "EduBerg offers..."},
        ...
    ]
    System messages are excluded — Claude gets those separately.
    """
    messages = get_conversation_history(db, conversation_id, limit)
    return [
        {"role": msg.role.value, "content": msg.content}
        for msg in messages
        if msg.role in (MessageRole.USER, MessageRole.ASSISTANT)
    ]