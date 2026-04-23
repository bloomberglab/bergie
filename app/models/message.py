from sqlalchemy import String, ForeignKey, Enum as SAEnum, Text, Integer, Boolean, Sequence as SASequence
from sqlalchemy.orm import Mapped, mapped_column, relationship, column_property
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
from app.models.base_model import UUIDMixin, TimestampMixin
from sqlalchemy import JSON
import enum
import uuid


class MessageRole(str, enum.Enum):
    USER      = "user"
    ASSISTANT = "assistant"
    SYSTEM    = "system"


class MessageType(str, enum.Enum):
    TEXT     = "text"
    IMAGE    = "image"
    DOCUMENT = "document"
    AUDIO    = "audio"
    BUTTON   = "button"
    SYSTEM   = "system"


class Message(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Sequence object ensures cross-database autoincrement on a non-PK column
    sequence: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
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
    content: Mapped[str] = mapped_column(Text, nullable=False)
    media_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ai_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rag_sources: Mapped[list | None] = mapped_column(JSON, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delivered: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

    def __repr__(self) -> str:
        preview = self.content[:40] + "..." if len(self.content) > 40 else self.content
        return f"<Message seq={self.sequence} role={self.role} content={preview!r}>"