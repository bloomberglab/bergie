"""
Service layer tests.
These run against a real test database — they're integration tests,
not unit tests with mocks. This is intentional: we want to verify
the actual SQL queries work correctly.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.platform_identity import Platform
from app.models.message import MessageRole, MessageType
from app.services.user_service import (
    get_or_create_user,
    get_user_by_platform_id,
    is_user_blocked,
    block_user,
)
from app.services.conversation_service import (
    get_or_create_conversation,
    save_message,
    get_history_for_claude,
)
from app.core.config import settings


# ── Test database setup ────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def db():
    """
    Creates a fresh in-memory SQLite database for each test.
    Each test gets clean tables — no leftover data between tests.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


# ── User service tests ─────────────────────────────────────────────────────

def test_get_or_create_user_creates_new_user(db):
    """First contact from a new Telegram user should create a User record."""
    user, created = get_or_create_user(
        db,
        platform=Platform.TELEGRAM,
        platform_user_id="123456789",
        display_name="Aisha",
        username="aisha_tlgm",
    )
    db.commit()

    assert created is True
    assert user.id is not None
    assert user.display_name == "Aisha"
    assert user.status.value == "active"


def test_get_or_create_user_returns_existing_user(db):
    """Second message from same user should return existing record, not create new."""
    user1, created1 = get_or_create_user(
        db, Platform.TELEGRAM, "123456789", display_name="Aisha"
    )
    db.commit()

    user2, created2 = get_or_create_user(
        db, Platform.TELEGRAM, "123456789", display_name="Aisha"
    )
    db.commit()

    assert created1 is True
    assert created2 is False
    assert user1.id == user2.id


def test_same_person_two_platforms(db):
    """Same person on Telegram and WhatsApp should be two different users for now
    (manual linking is a future feature)."""
    user_tg, _ = get_or_create_user(
        db, Platform.TELEGRAM, "123456789", display_name="Raj"
    )
    user_wa, _ = get_or_create_user(
        db, Platform.WHATSAPP, "919876543210", display_name="Raj"
    )
    db.commit()

    assert user_tg.id != user_wa.id


def test_block_user(db):
    """Blocked users should be detected before processing their messages."""
    user, _ = get_or_create_user(
        db, Platform.TELEGRAM, "999888777", display_name="Spammer"
    )
    db.commit()

    assert is_user_blocked(db, Platform.TELEGRAM, "999888777") is False

    block_user(db, user.id)
    db.commit()

    assert is_user_blocked(db, Platform.TELEGRAM, "999888777") is True


# ── Conversation service tests ─────────────────────────────────────────────

def test_get_or_create_conversation(db):
    """First message should create a new conversation."""
    user, _ = get_or_create_user(
        db, Platform.TELEGRAM, "111222333", display_name="Fatima"
    )
    db.commit()

    conv, created = get_or_create_conversation(
        db,
        user_id=user.id,
        platform=Platform.TELEGRAM,
        platform_thread_id="111222333",
    )
    db.commit()

    assert created is True
    assert conv.status.value == "active"
    assert conv.user_id == user.id


def test_second_message_reuses_conversation(db):
    """Second message in same session should reuse the open conversation."""
    user, _ = get_or_create_user(
        db, Platform.TELEGRAM, "444555666", display_name="Rahul"
    )
    db.commit()

    conv1, created1 = get_or_create_conversation(
        db, user.id, Platform.TELEGRAM, "444555666"
    )
    db.commit()

    conv2, created2 = get_or_create_conversation(
        db, user.id, Platform.TELEGRAM, "444555666"
    )
    db.commit()

    assert created1 is True
    assert created2 is False
    assert conv1.id == conv2.id


def test_save_and_retrieve_messages(db):
    """Messages saved should come back in correct order for Claude context."""
    user, _ = get_or_create_user(
        db, Platform.TELEGRAM, "777888999", display_name="Priya"
    )
    conv, _ = get_or_create_conversation(
        db, user.id, Platform.TELEGRAM, "777888999"
    )
    db.commit()

    save_message(db, conv.id, MessageRole.USER, "What courses do you offer?")
    save_message(
        db, conv.id, MessageRole.ASSISTANT,
        "EduBerg offers Advanced Robotics, Python Programming, and more!",
        input_tokens=45, output_tokens=120,
    )
    save_message(db, conv.id, MessageRole.USER, "Tell me more about robotics.")
    db.commit()

    history = get_history_for_claude(db, conv.id)

    assert len(history) == 3
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "What courses do you offer?"
    assert history[1]["role"] == "assistant"
    assert history[2]["role"] == "user"
    assert history[2]["content"] == "Tell me more about robotics."