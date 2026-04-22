from sqlalchemy import String, Boolean, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.base_model import UUIDMixin, TimestampMixin
import enum


class UserStatus(str, enum.Enum):
    ACTIVE   = "active"
    BLOCKED  = "blocked"    # admin manually blocked this user
    INACTIVE = "inactive"   # hasn't messaged in 90+ days


class User(UUIDMixin, TimestampMixin, Base):
    """
    A real person who interacts with Bergie.
    Platform-agnostic — the same User record is referenced
    whether they message from Telegram, WhatsApp, or the web UI.
    """
    __tablename__ = "users"

    # The display name we learn from the platform (e.g. Telegram first name)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Phone number — primarily populated from WhatsApp
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Preferred language for Bergie's responses
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)

    # Whether this user has given opt-in consent (required for WhatsApp outbound)
    whatsapp_opted_in: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    status: Mapped[UserStatus] = mapped_column(
        SAEnum(UserStatus, name="user_status"),
        default=UserStatus.ACTIVE,
        nullable=False,
    )

    # ── Relationships ───────────────────────────────────────────────
    platform_identities: Mapped[list["PlatformIdentity"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} name={self.display_name!r} status={self.status}>"