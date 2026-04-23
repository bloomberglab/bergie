from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.schemas.message import MessageResponse


class ConversationResponse(BaseModel):
    """Summary of a conversation for API responses."""
    id: str
    platform: str
    status: str
    topic: Optional[str]
    created_at: datetime
    messages: list[MessageResponse] = []

    model_config = {"from_attributes": True}