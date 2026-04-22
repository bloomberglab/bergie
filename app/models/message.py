# app/models/message.py

from sqlalchemy import String, ForeignKey, Enum as SAEnum, Text, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base
from app.models.base_model import UUIDMixin, TimestampMixin
import enum
import uuid


class MessageRole(str, enum.Enum):
    USER      = "user"       # message from the human
    ASSISTANT = "assistant"  # message from Bergie (Claude)
    SYSTEM    = "system"     # internal system messages


class MessageType(str, enum.Enum):
    TEXT     = "text"
    IMAGE    = "image"
    DOCUMENT = "document"
    AUDIO    = "audio"
    BUTTON   = "button"    # quick reply or button tap
    SYSTEM   = "system"    # e.g. "conversation started"


class Message(UUIDMixin, TimestampMixin, Base):
    """
    A single turn in a conversation.
    We store both the user's messages and Bergie's replies.
    This gives us:
    - Full conversation history to feed back to Claude as context
    - Audit trail for debugging and quality improvement
    - Data for future analytics
    """
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[MessageRole] = mapped_column(
        SAEnum(MessageRole, name="message_role"),
        nullable=False,
    )
    message_type: Mapped[MessageType] = mapped_column(
        SAEnum(MessageType, name="message_type"),
        default=MessageType.TEXT,
        nullable=False,
    )

    # The actual text content
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # For media messages — URL or file_id from the platform
    media_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Claude API usage for this response (tokens used, model name etc.)
    # Stored as JSONB so we can query it later for cost analysis
    ai_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Which RAG chunks were used to answer (for quality tracking)
    rag_sources: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Tokens used — pulled out of ai_metadata for easy querying
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Did the user rate this response? (future thumbs up/down feature)
    user_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1 or -1

    # Was this message delivered successfully to the platform?
    delivered: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── Relationships ───────────────────────────────────────────────
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

    def __repr__(self) -> str:
        preview = self.content[:40] + "..." if len(self.content) > 40 else self.content
        return f"<Message role={self.role} type={self.message_type} content={preview!r}>"