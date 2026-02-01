from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, constr
from bson import ObjectId

class UserProfile(BaseModel):
    """Extended user profile model for contextual AI assistance."""
    id: Optional[str] = Field(None, alias="_id")
    name: constr(strip_whitespace=True, min_length=1, max_length=100)
    role: Optional[str] = Field(None, max_length=100)
    communication_style: str
    expertise_areas: List[str] = Field(max_items=5, default_factory=list)
    current_projects: Optional[str] = Field(None, max_length=500)
    preferred_tools: List[str] = Field(max_items=10, default_factory=list)
    user_id: str = "default"
    is_active: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str, datetime: lambda dt: dt.isoformat()}

class UserProfileCreatePayload(BaseModel):
    """Payload for creating a new user profile."""
    name: constr(strip_whitespace=True, min_length=1, max_length=100)
    role: Optional[str] = Field(None, max_length=100)
    communication_style: str
    expertise_areas: List[str] = Field(max_items=5, default_factory=list)
    current_projects: Optional[str] = Field(None, max_length=500)
    preferred_tools: List[str] = Field(max_items=10, default_factory=list)

class UserProfileUpdatePayload(BaseModel):
    """Payload for updating an existing user profile."""
    name: Optional[constr(strip_whitespace=True, min_length=1, max_length=100)] = None
    role: Optional[str] = Field(None, max_length=100)
    communication_style: Optional[str] = None
    expertise_areas: Optional[List[str]] = Field(None, max_items=5)
    current_projects: Optional[str] = Field(None, max_length=500)
    preferred_tools: Optional[List[str]] = Field(None, max_items=10)
    is_active: Optional[bool] = None

class ConversationContext(BaseModel):
    """Model for conversation context metadata."""
    conversation_id: str
    title: Optional[str] = None
    summary: Optional[str] = Field(None, max_length=1000)
    key_topics: List[str] = Field(max_items=10, default_factory=list)
    pinned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: str = "default"

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str, datetime: lambda dt: dt.isoformat()}
