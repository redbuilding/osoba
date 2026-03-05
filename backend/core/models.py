from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, constr, field_validator
from bson import ObjectId
from typing import Any

############################
# Existing chat models stay
############################

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
    use_python: bool = False
    csv_data_b64: Optional[str] = None
    conversation_id: Optional[str] = None
    model_name: Optional[str] = None
    provider: Optional[str] = None  # New field for provider selection
    profile_id: Optional[str] = None  # New field for AI profile selection
    repeat_penalty: Optional[float] = None
    inject_docs: Optional[bool] = False  # New field for documentation injection
    remove_docs: Optional[bool] = False  # New field for documentation removal

class ChatResponse(BaseModel):
    conversation_id: str
    chat_history: List[ChatMessage]
    model_name: Optional[str] = None
    provider: Optional[str] = None  # New field for provider information
    profile_id: Optional[str] = None  # New field for AI profile information

class ConversationListItem(BaseModel):
    id: str = Field(alias="_id")
    title: Optional[str] = "New Chat"
    created_at: datetime
    updated_at: datetime
    message_count: int
    model_name: Optional[str] = None
    provider: Optional[str] = None  # New field for provider information
    profile_id: Optional[str] = None  # New field for AI profile information
    pinned_for_context: Optional[bool] = False  # New field for conversation pinning
    summary: Optional[str] = None  # New field for conversation summary
    docs_injected: Optional[bool] = False  # New field for documentation injection status

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str, datetime: lambda dt: dt.isoformat()}

class RenamePayload(BaseModel):
    new_title: constr(strip_whitespace=True, min_length=1, max_length=100)

############################
# Long-running Tasks models
############################

class PlanStep(BaseModel):
    id: str
    title: str
    instruction: str
    tool: str
    params: dict | None = None
    success_criteria: str
    max_retries: int = 1
    # runtime fields
    status: str = "PENDING"  # PENDING|RUNNING|COMPLETED|FAILED|SKIPPED
    retries: int = 0
    outputs: dict[str, Any] | None = None
    error: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None

class Plan(BaseModel):
    constraints: list[str] = []
    resources: list[str] = []
    steps: list[PlanStep]

class TaskCreatePayload(BaseModel):
    goal: str
    conversation_id: str | None = None
    model_name: str | None = None
    budget: dict | None = None  # { max_seconds?: int, max_tool_calls?: int }
    dry_run: bool = False
    priority: int = 2  # 1=scheduled, 2=user, 3=low
    kb_doc_ids: Optional[List[str]] = None  # up to 2 indexed KB doc IDs

class TaskSummary(BaseModel):
    id: str = Field(alias="_id")
    title: str
    goal: str
    status: str
    created_at: datetime
    updated_at: datetime
    model_name: str | None = None
    priority: int = 2  # 1=scheduled, 2=user, 3=low

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str, datetime: lambda dt: dt.isoformat()}

class TaskDetail(BaseModel):
    id: str = Field(alias="_id")
    title: str
    goal: str
    status: str
    created_at: datetime
    updated_at: datetime
    conversation_id: str | None = None
    model_name: str | None = None
    budget: dict | None = None
    usage: dict | None = None
    plan: Plan | None = None
    current_step_index: int = -1
    summary: str | None = None
    error: str | None = None
    priority: int = 2  # 1=scheduled, 2=user, 3=low
    kb_docs: Optional[List[dict]] = None  # [{id, title}] — KB docs attached at creation

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str, datetime: lambda dt: dt.isoformat()}

############################
# Task Scheduling models
############################

class TaskSchedule(BaseModel):
    # type: 'recurring' | 'once'. Default to 'recurring' for backward compatibility.
    type: str = "recurring"
    cron_expression: Optional[str] = None
    once_at: Optional[str] = None  # ISO 8601, interpreted in 'timezone' if naive
    timezone: str = "UTC"
    enabled: bool = True
    next_run: Optional[datetime] = None

class ScheduledTaskPayload(BaseModel):
    name: str
    goal: str
    schedule: TaskSchedule
    template_id: Optional[str] = None
    model_name: Optional[str] = None
    budget: Optional[dict] = None
    # Optional planner hints produced by the AI improver
    # Expected keys: { manifest?: dict, step_plan?: list }
    planner_hints: Optional[Dict[str, Any]] = None
    kb_doc_ids: Optional[List[str]] = None  # up to 2 indexed KB doc IDs

class ScheduledTaskSummary(BaseModel):
    id: str = Field(alias="_id")
    name: str
    goal: str
    schedule: TaskSchedule
    model_name: Optional[str] = None
    created_at: datetime
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0

    @field_validator('id', mode='before')
    @classmethod
    def convert_objectid_to_str(cls, v):
        if hasattr(v, '__str__'):
            return str(v)
        return v

    model_config = {
        "populate_by_name": True,
        "json_encoders": {ObjectId: str, datetime: lambda dt: dt.isoformat()},
        "by_alias": True
    }

############################
# Task Templates models
############################

class TaskTemplate(BaseModel):
    id: str = Field(alias="_id")
    name: str
    description: str
    goal_template: str  # Template with placeholders like {project_name}
    default_parameters: Dict[str, Any] = {}
    category: str = "general"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str, datetime: lambda dt: dt.isoformat()}

class TaskFromTemplatePayload(BaseModel):
    template_id: str
    parameters: Dict[str, str]  # Values for placeholders
    conversation_id: Optional[str] = None
    model_name: Optional[str] = None

############################
# Prompt Improver models
############################

class PromptImprovePayload(BaseModel):
    draft_text: str
    task_type: str = "scheduled"
    model_name: Optional[str] = None
    mode: Optional[str] = None  # Clarify | Expand | Tighten | Translate
    language: Optional[str] = None
    context_hints: Optional[Dict[str, Any]] = None

class PromptImproveResponse(BaseModel):
    improved_text: str
    manifest: Dict[str, Any] = {}
    step_plan: List[Dict[str, Any]] = []
    warnings: Optional[List[str]] = None
