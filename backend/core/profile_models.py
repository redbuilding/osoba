from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field, constr
from bson import ObjectId

class AIProfile(BaseModel):
    """AI Profile model for personalized assistant configurations."""
    id: Optional[str] = Field(None, alias="_id")
    name: constr(strip_whitespace=True, min_length=1, max_length=100)
    communication_style: str
    expertise_areas: List[str] = Field(max_items=5, default_factory=list)
    backstory: Optional[str] = Field(None, max_length=1000)
    user_id: str = "default"
    is_active: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str, datetime: lambda dt: dt.isoformat()}

class ProfileCreatePayload(BaseModel):
    """Payload for creating a new AI profile."""
    name: constr(strip_whitespace=True, min_length=1, max_length=100)
    communication_style: str
    expertise_areas: List[str] = Field(max_items=5, default_factory=list)
    backstory: Optional[str] = Field(None, max_length=1000)

class ProfileUpdatePayload(BaseModel):
    """Payload for updating an existing AI profile."""
    name: Optional[constr(strip_whitespace=True, min_length=1, max_length=100)] = None
    communication_style: Optional[str] = None
    expertise_areas: Optional[List[str]] = Field(None, max_items=5)
    backstory: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None

class ProfileResponse(BaseModel):
    """Response model for profile operations."""
    success: bool
    message: str
    profile_id: Optional[str] = None
    profile: Optional[AIProfile] = None
