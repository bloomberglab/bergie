import logging
from anthropic import Anthropic, APIError, APITimeoutError, RateLimitError
from app.core.config import settings

logger = logging.getLogger("bergie")

# Initialise the Anthropic client once — it's thread-safe and reusable
_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)


# ── System prompt ──────────────────────────────────────────────────────────

def build_system_prompt() -> str:
    """
    Bergie's identity, personality, and rules.

    This is sent to Claude on every request as the system message.
    It is never shown to the user directly.

    Design principles:
    - Be warm and helpful, not robotic
    - Stay strictly within EduBerg's domain
    - Escalate gracefully when out of scope
    - Keep responses concise for messaging platforms
    """
    return f"""You are Bergie, the AI assistant for {settings.BERGIE_COMPANY}.

## Who you are
You are a friendly, knowledgeable, and professional educational assistant.
Your name is Bergie. You represent {settings.BERGIE_COMPANY} with warmth and competence.
You speak naturally — not like a corporate chatbot. You are helpful, clear, and concise.

## What you help with
- Information about EduBerg's courses, programmes, and batches
- Fee structures, payment options, and enrollment processes
- Class schedules, timings, and batch availability
- General educational guidance related to EduBerg's offerings
- Answering student support questions
- Directing students to the right person or resource when needed

## How you respond
- Keep responses short and clear — this is a messaging platform, not a webpage
- Use simple language; avoid jargon unless the user uses it first
- Break information into short paragraphs or simple lists when helpful
- Always be polite, even if the user is frustrated
- If you don't know something specific about EduBerg, say so honestly and
  offer to connect them with the right team member
- Never make up course details, fees, or dates you are not certain about

## What you do NOT do
- You do not discuss topics unrelated to education or EduBerg
- You do not provide medical, legal, or financial advice
- You do not engage with inappropriate or offensive messages
- You do not pretend to be a human if sincerely asked
- You do not share information about other students

## When you are unsure
If a user asks something you cannot answer confidently, say:
"I want to make sure you get accurate information on this. Let me connect
you with our team who can help. You can also reach us at [contact details]."

## Language
Respond in the same language the user writes in.
You support English and Malayalam. Default to English if unclear.

## Tone examples
Good: "Hi! I'm Bergie from EduBerg. Happy to help you today."
Good: "Our Python Programming course runs for 3 months, starting every quarter."
Avoid: "Greetings. I am an AI assistant. Please state your query."
Avoid: "I cannot assist with that request at this time."
"""


# ── Response builder ───────────────────────────────────────────────────────

def build_messages(
    history: list[dict],
    user_message: str,
) -> list[dict]:
    """
    Combine conversation history with the new user message
    into the format Claude expects.

    history format (from get_history_for_claude):
        [
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."},
        ]

    We append the current message at the end.
    """
    messages = list(history)  # copy — don't mutate the original
    messages.append({"role": "user", "content": user_message})
    return messages


# ── Main AI call ───────────────────────────────────────────────────────────

class AIResponse:
    """Structured result from the AI service."""

    def __init__(
        self,
        text: str,
        input_tokens: int,
        output_tokens: int,
        model: str,
    ):
        self.text = text
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.model = model

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def to_metadata_dict(self) -> dict:
        """Stored in messages.ai_metadata for cost tracking."""
        return {
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
        }

    def __repr__(self) -> str:
        return (
            f"<AIResponse tokens={self.total_tokens} "
            f"preview={self.text[:50]!r}>"
        )


def get_ai_response(
    history: list[dict],
    user_message: str,
    system_prompt: str | None = None,
) -> AIResponse:
    """
    The single function the rest of the app calls to get a response from Claude.

    Args:
        history:      Previous messages in this conversation (oldest first)
        user_message: The new message from the user
        system_prompt: Override the default system prompt (optional)

    Returns:
        AIResponse with the text and token usage

    Raises:
        RuntimeError: If the API call fails after retries
    """
    prompt = system_prompt or build_system_prompt()
    messages = build_messages(history, user_message)

    logger.info(
        f"Calling Claude | model={settings.ANTHROPIC_MODEL} "
        f"history_turns={len(history)} "
        f"message_len={len(user_message)}"
    )

    try:
        response = _client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=settings.ANTHROPIC_MAX_TOKENS,
            system=prompt,
            messages=messages,
        )

        text = response.content[0].text
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        logger.info(
            f"Claude responded | "
            f"input_tokens={input_tokens} "
            f"output_tokens={output_tokens} "
            f"preview={text[:60]!r}"
        )

        return AIResponse(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=settings.ANTHROPIC_MODEL,
        )

    except RateLimitError:
        logger.error("Claude API rate limit hit")
        raise RuntimeError(
            "Bergie is receiving a lot of messages right now. "
            "Please try again in a moment."
        )

    except APITimeoutError:
        logger.error("Claude API timed out")
        raise RuntimeError(
            "Bergie took too long to respond. Please try again."
        )

    except APIError as e:
        logger.error(f"Claude API error: {e.status_code} — {e.message}")
        raise RuntimeError(
            "Bergie is having trouble right now. Please try again shortly."
        )