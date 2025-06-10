from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, constr
from bson import ObjectId

class ChatMessage(BaseModel):
    role: str
    content: str
    is_html: Optional[bool] = False
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ChatPayload(BaseModel):
    user_message: str
    chat_history: List[ChatMessage]
    use_search: bool
    use_database: bool = False
    use_hubspot: bool = False
    use_youtube: bool = False
    conversation_id: Optional[str] = None
    ollama_model_name: Optional[str] = None
    repeat_penalty: Optional[float] = None

class ChatResponse(BaseModel):
    conversation_id: str
    chat_history: List[ChatMessage]
    ollama_model_name: Optional[str] = None

class ConversationListItem(BaseModel):
    id: str = Field(alias="_id")
    title: Optional[str] = "New Chat"
    created_at: datetime
    updated_at: datetime
    message_count: int
    ollama_model_name: Optional[str] = None

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str, datetime: lambda dt: dt.isoformat()}

class RenamePayload(BaseModel):
    new_title: constr(strip_whitespace=True, min_length=1, max_length=100)
