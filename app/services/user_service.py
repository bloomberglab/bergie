import uuid
import logging
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.user import User, UserStatus
from app.models.platform_identity import PlatformIdentity, Platform
from app.models.conversation import Conversation, ConversationStatus
from app.schemas.user import UserCreate

logger = logging.getLogger("bergie")


# ── User lookup ────────────────────────────────────────────────────────────

def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    """Fetch a user by their internal UUID."""
    return db.get(User, user_id)


def get_user_by_platform_id(
    db: Session,
    platform: Platform,
    platform_user_id: str,
) -> User | None:
    """
    The most common lookup in the entire system.
    Given a platform and its user identifier, return our internal User.
    Returns None if this person has never contacted Bergie before.
    """
    stmt = (
        select(User)
        .join(PlatformIdentity, PlatformIdentity.user_id == User.id)
        .where(
            PlatformIdentity.platform == platform,
            PlatformIdentity.platform_user_id == platform_user_id,
        )
    )
    return db.scalar(stmt)


def get_platform_identity(
    db: Session,
    platform: Platform,
    platform_user_id: str,
) -> PlatformIdentity | None:
    """Fetch the platform identity record directly."""
    stmt = select(PlatformIdentity).where(
        PlatformIdentity.platform == platform,
        PlatformIdentity.platform_user_id == platform_user_id,
    )
    return db.scalar(stmt)


# ── User creation ──────────────────────────────────────────────────────────

def create_user(db: Session, data: "UserCreate") -> User:
    """
    Create a brand new User record.
    Called when get_user_by_platform_id returns None.
    """
    user = User(
        display_name=data.display_name,
        phone_number=data.phone_number,
        language=data.language,
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.flush()   # flush to get the UUID assigned without committing yet
    logger.info(f"Created new user: id={user.id} name={user.display_name!r}")
    return user


def create_platform_identity(
    db: Session,
    user: User,
    platform: Platform,
    platform_user_id: str,
    username: str | None = None,
) -> PlatformIdentity:
    """
    Link a platform identity to an existing User.
    One user can have multiple identities (Telegram + WhatsApp = same person).
    """
    identity = PlatformIdentity(
        user_id=user.id,
        platform=platform,
        platform_user_id=platform_user_id,
        username=username,
    )
    db.add(identity)
    db.flush()
    logger.info(f"Created platform identity: {platform}:{platform_user_id} → user {user.id}")
    return identity


# ── The main entry point used by webhook handlers ──────────────────────────

def get_or_create_user(
    db: Session,
    platform: Platform,
    platform_user_id: str,
    display_name: str | None = None,
    username: str | None = None,
    phone_number: str | None = None,
) -> tuple[User, bool]:
    """
    The single function webhook handlers call when a message arrives.

    Returns (user, created) where:
    - user    → the User object (existing or newly created)
    - created → True if this is a brand new user, False if returning

    All DB writes are flushed but NOT committed here.
    The caller (route handler) is responsible for db.commit().
    This gives us transactional safety — if anything fails after this
    call, the whole transaction rolls back cleanly.
    """
    existing = get_user_by_platform_id(db, platform, platform_user_id)

    if existing:
        # Update display name if the platform gave us a newer one
        if display_name and existing.display_name != display_name:
            existing.display_name = display_name
            logger.debug(f"Updated display name for user {existing.id}")
        return existing, False

    # First time we've seen this person — create everything
    from app.schemas.user import UserCreate
    user = create_user(db, UserCreate(
        display_name=display_name,
        phone_number=phone_number,
        language="en",
    ))
    create_platform_identity(db, user, platform, platform_user_id, username)
    return user, True


# ── User management ────────────────────────────────────────────────────────

def block_user(db: Session, user_id: uuid.UUID) -> User | None:
    """Block a user — Bergie will not respond to blocked users."""
    user = get_user_by_id(db, user_id)
    if user:
        user.status = UserStatus.BLOCKED
        logger.info(f"Blocked user: {user_id}")
    return user


def is_user_blocked(db: Session, platform: Platform, platform_user_id: str) -> bool:
    """Quick check before processing any message."""
    user = get_user_by_platform_id(db, platform, platform_user_id)
    if not user:
        return False
    return user.status == UserStatus.BLOCKED