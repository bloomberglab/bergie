# app/services/__init__.py

from app.services.user_service import (
    get_or_create_user,
    get_user_by_platform_id,
    is_user_blocked,
    block_user,
)
from app.services.conversation_service import (
    get_or_create_conversation,
    get_conversation_history,
    get_history_for_claude,
    save_message,
    close_conversation,
    escalate_conversation,
)
from app.services.ai_service import (
    get_ai_response,
    build_system_prompt,
    AIResponse,
)

__all__ = [
    "get_or_create_user",
    "get_user_by_platform_id",
    "is_user_blocked",
    "block_user",
    "get_or_create_conversation",
    "get_conversation_history",
    "get_history_for_claude",
    "save_message",
    "close_conversation",
    "escalate_conversation",
    "get_ai_response",
    "build_system_prompt",
    "AIResponse",
]