import pytest
from unittest.mock import patch, MagicMock
from app.services.ai_service import (
    get_ai_response,
    build_system_prompt,
    build_messages,
    AIResponse,
)


# ── Helper to build a mock Anthropic response ──────────────────────────────

def make_mock_response(text: str, input_tokens: int = 50, output_tokens: int = 100):
    """Creates a mock that looks like anthropic.types.Message."""
    mock = MagicMock()
    mock.content = [MagicMock(text=text)]
    mock.usage.input_tokens = input_tokens
    mock.usage.output_tokens = output_tokens
    return mock


# ── System prompt tests ────────────────────────────────────────────────────

def test_system_prompt_contains_bergie():
    prompt = build_system_prompt()
    assert "Bergie" in prompt


def test_system_prompt_contains_eduberg():
    prompt = build_system_prompt()
    assert "EduBerg" in prompt


def test_system_prompt_is_non_empty():
    prompt = build_system_prompt()
    assert len(prompt) > 100


# ── Message builder tests ──────────────────────────────────────────────────

def test_build_messages_no_history():
    messages = build_messages([], "Hello!")
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello!"


def test_build_messages_with_history():
    history = [
        {"role": "user",      "content": "Hi"},
        {"role": "assistant", "content": "Hello!"},
    ]
    messages = build_messages(history, "What courses do you have?")
    assert len(messages) == 3
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == "What courses do you have?"


def test_build_messages_does_not_mutate_history():
    """Verify we don't modify the caller's history list."""
    history = [{"role": "user", "content": "Hi"}]
    original_length = len(history)
    build_messages(history, "New message")
    assert len(history) == original_length


# ── AI response tests ──────────────────────────────────────────────────────

@patch("app.services.ai_service._client")
def test_get_ai_response_returns_text(mock_client):
    mock_client.messages.create.return_value = make_mock_response(
        "Hello! I'm Bergie from EduBerg."
    )
    response = get_ai_response([], "Hi!")
    assert isinstance(response, AIResponse)
    assert "Bergie" in response.text


@patch("app.services.ai_service._client")
def test_get_ai_response_tracks_tokens(mock_client):
    mock_client.messages.create.return_value = make_mock_response(
        "Hello!", input_tokens=42, output_tokens=88
    )
    response = get_ai_response([], "Hi!")
    assert response.input_tokens == 42
    assert response.output_tokens == 88
    assert response.total_tokens == 130


@patch("app.services.ai_service._client")
def test_get_ai_response_passes_history(mock_client):
    """Verify that history is included in the API call."""
    mock_client.messages.create.return_value = make_mock_response("Sure!")

    history = [
        {"role": "user",      "content": "What courses do you have?"},
        {"role": "assistant", "content": "We have many courses."},
    ]
    get_ai_response(history, "Tell me more.")

    call_args = mock_client.messages.create.call_args
    messages_sent = call_args.kwargs["messages"]

    # Should be history (2) + new message (1) = 3 total
    assert len(messages_sent) == 3
    assert messages_sent[-1]["content"] == "Tell me more."


@patch("app.services.ai_service._client")
def test_get_ai_response_uses_correct_model(mock_client):
    mock_client.messages.create.return_value = make_mock_response("Hi!")
    response = get_ai_response([], "Hello")
    from app.core.config import settings
    call_args = mock_client.messages.create.call_args
    assert call_args.kwargs["model"] == settings.ANTHROPIC_MODEL
    assert response.model == settings.ANTHROPIC_MODEL


@patch("app.services.ai_service._client")
def test_rate_limit_raises_runtime_error(mock_client):
    from anthropic import RateLimitError
    mock_client.messages.create.side_effect = RateLimitError(
        message="rate limit", response=MagicMock(status_code=429), body={}
    )
    with pytest.raises(RuntimeError, match="lot of messages"):
        get_ai_response([], "Hi")


@patch("app.services.ai_service._client")
def test_timeout_raises_runtime_error(mock_client):
    from anthropic import APITimeoutError
    mock_client.messages.create.side_effect = APITimeoutError(request=MagicMock())
    with pytest.raises(RuntimeError, match="too long"):
        get_ai_response([], "Hi")


# ── AIResponse tests ───────────────────────────────────────────────────────

def test_ai_response_metadata_dict():
    r = AIResponse(
        text="Hello!",
        input_tokens=10,
        output_tokens=20,
        model="claude-haiku-4-5-20251001",
    )
    meta = r.to_metadata_dict()
    assert meta["total_tokens"] == 30
    assert meta["model"] == "claude-haiku-4-5-20251001"
    assert "input_tokens" in meta
    assert "output_tokens" in meta