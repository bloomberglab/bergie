from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class MessageResponse(BaseModel):
    """Represents a single message turn in an API response."""
    id: str
    role: str
    content: str
    message_type: str
    created_at: datetime
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None

    model_config = {"from_attributes": True}