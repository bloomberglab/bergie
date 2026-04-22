from sqlalchemy import String, ForeignKey, UniqueConstraint, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
from app.models.base_model import UUIDMixin, TimestampMixin
import enum
import uuid


class Platform(str, enum.Enum):
    TELEGRAM  = "telegram"
    WHATSAPP  = "whatsapp"
    FACEBOOK  = "facebook"
    INSTAGRAM = "instagram"
    WEB       = "web"


class PlatformIdentity(UUIDMixin, TimestampMixin, Base):
    """
    Maps a platform-specific user ID to our internal User.

    Examples of platform_user_id:
    - Telegram:  "123456789"          (chat_id as string)
    - WhatsApp:  "919876543210"       (phone with country code)
    - Facebook:  "1234567890123456"   (PSID)
    - Instagram: "9876543210987654"   (IGSID)
    - Web:       "session_abc123"     (browser session ID)
    """
    __tablename__ = "platform_identities"

    # Ensure one platform_user_id per platform
    __table_args__ = (
        UniqueConstraint("platform", "platform_user_id", name="uq_platform_identity"),
    )

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

    # The ID this platform gives us for the user
    platform_user_id: Mapped[str] = mapped_column(String(128), nullable=False)

    # Extra platform metadata (username, profile pic URL etc.)
    username: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # ── Relationships ───────────────────────────────────────────────
    user: Mapped["User"] = relationship(back_populates="platform_identities")

    def __repr__(self) -> str:
        return f"<PlatformIdentity {self.platform}:{self.platform_user_id}>"