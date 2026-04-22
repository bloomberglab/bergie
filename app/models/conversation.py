from sqlalchemy import String, ForeignKey, Enum as SAEnum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
from app.models.base_model import UUIDMixin, TimestampMixin
from app.models.platform_identity import Platform
import enum
import uuid


class ConversationStatus(str, enum.Enum):
    ACTIVE    = "active"     # currently in progress
    CLOSED    = "closed"     # ended naturally or by timeout
    ESCALATED = "escalated"  # handed off to human agent


class Conversation(UUIDMixin, TimestampMixin, Base):
    """
    A conversation session between a User and Bergie on a specific platform.

    One user can have many conversations over time —
    each new "session" (e.g. after 24hrs of inactivity) creates a new one.
    Messages belong to a conversation, not directly to a user.
    """
    __tablename__ = "conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform: Mapped[Platform] = mapped_column(
        SAEnum(Platform, name="platform_type"),
        nullable=False,
    )

    # Platform-specific conversation thread ID
    # Telegram: chat_id | WhatsApp: phone number | Web: session ID
    platform_thread_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    status: Mapped[ConversationStatus] = mapped_column(
        SAEnum(ConversationStatus, name="conversation_status"),
        default=ConversationStatus.ACTIVE,
        nullable=False,
    )

    # What topic/intent the conversation is about (populated by AI layer later)
    topic: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Human agent notes if escalated
    agent_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ───────────────────────────────────────────────
    user: Mapped["User"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} platform={self.platform} status={self.status}>"