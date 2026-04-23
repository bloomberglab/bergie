from pydantic import BaseModel
from typing import Optional


class UserCreate(BaseModel):
    """Data needed to create a new User record."""
    display_name: Optional[str] = None
    phone_number: Optional[str] = None
    language: str = "en"


class UserResponse(BaseModel):
    """What we return when an API endpoint exposes user info."""
    id: str
    display_name: Optional[str]
    language: str
    status: str

    model_config = {"from_attributes": True}