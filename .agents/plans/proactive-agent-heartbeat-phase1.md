# Feature: Proactive Agent Heartbeat System (Phase 1: Hybrid Approach)

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Implement a proactive AI heartbeat system that periodically reviews user activity (conversations, tasks, goals) and surfaces actionable insights without being intrusive. This Phase 1 implementation combines a user-editable Goals document with a non-intrusive notification system, serving as a stepping stone toward a fully autonomous proactive agent.

The heartbeat runs at configurable intervals (default: 2 hours), respects active hours (timezone-aware), uses a cost-effective model (Haiku), and creates dismissible insight notifications rather than cluttering conversations.

## User Story

As a user of OhSee
I want the AI to proactively review my goals and recent activity
So that I receive timely suggestions to advance my objectives without being overwhelmed by notifications

## Problem Statement

Users often lose track of:
- Follow-up actions from previous conversations
- Progress toward stated goals
- Opportunities to leverage completed work
- Tasks that have stalled or need attention

Current system is purely reactive - the AI only responds when explicitly prompted. Users must remember to check back on previous discussions and manually track their own progress.

## Solution Statement

Implement a background heartbeat service that:
1. Periodically reviews user context (goals, recent conversations, active tasks)
2. Uses LLM to identify 1-2 actionable next steps
3. Creates insight notifications (not conversation messages)
4. Respects user preferences (enabled/disabled, active hours, frequency)
5. Uses cost-effective models to minimize token usage

This provides proactive value while maintaining user control and avoiding notification fatigue.

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: Medium
**Primary Systems Affected**: 
- Backend services (new heartbeat service)
- User profile system (goals document, heartbeat config)
- Database (new insights collection)
- Frontend (notification UI, goals editor)

**Dependencies**: 
- APScheduler (AsyncIOScheduler for background tasks)
- Existing LLM service (provider_service)
- Existing user profile system
- MongoDB (new collection for insights)

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

**Scheduler Pattern:**
- `backend/services/task_scheduler.py` (lines 13-173) - Why: Existing AsyncIOScheduler pattern for background tasks
- `backend/main.py` (lines 20-50) - Why: Lifespan manager pattern for starting/stopping services
- `backend/services/schedule_utils.py` - Why: Timezone-aware scheduling utilities (compute_next_run)

**User Profile System:**
- `backend/core/user_context_models.py` (lines 6-22) - Why: UserProfile model structure to extend
- `backend/db/user_profiles_crud.py` - Why: CRUD operations pattern for user profiles
- `backend/api/user_profile.py` - Why: API endpoint patterns for profile management
- `backend/services/context_service.py` (lines 1-100) - Why: Context gathering patterns (profile + conversations)

**LLM Integration:**
- `backend/services/llm_service.py` - Why: LLM calling patterns (chat_with_provider)
- `backend/services/provider_service.py` - Why: Multi-provider LLM routing

**Database Patterns:**
- `backend/db/mongodb.py` (lines 68-91) - Why: Collection getter patterns
- `backend/db/crud.py` - Why: Standard CRUD patterns with ObjectId handling
- `backend/db/tasks_crud.py` - Why: Task querying patterns to mirror

**Testing Patterns:**
- `backend/tests/test_chat_service.py` (lines 1-80) - Why: AsyncMock and pytest patterns
- `backend/tests/test_user_profile_api.py` - Why: User profile testing patterns
- `backend/tests/conftest.py` - Why: Test fixtures and MongoDB mocking

### New Files to Create

**Backend:**
- `backend/services/heartbeat_service.py` - Core heartbeat logic and scheduler
- `backend/core/heartbeat_models.py` - Pydantic models for heartbeat config and insights
- `backend/db/heartbeat_crud.py` - CRUD operations for insights
- `backend/api/heartbeat.py` - API endpoints for heartbeat management
- `backend/tests/test_heartbeat_service.py` - Unit tests for heartbeat service
- `backend/tests/test_heartbeat_api.py` - Integration tests for API endpoints

**Frontend:**
- `frontend/src/components/ProactiveInsightsPanel.jsx` - Notification panel UI
- `frontend/src/components/GoalsEditor.jsx` - Goals document editor
- `frontend/src/services/heartbeatApi.js` - API client for heartbeat endpoints

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [APScheduler AsyncIOScheduler](https://apscheduler.readthedocs.io/en/3.x/modules/schedulers/asyncio.html)
  - Specific section: AsyncIOScheduler usage with FastAPI
  - Why: Background task scheduling pattern
  
- [FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/events/#lifespan)
  - Specific section: Lifespan context manager
  - Why: Proper startup/shutdown of background services

- [Croniter Documentation](https://github.com/kiorky/croniter)
  - Specific section: Timezone-aware cron expressions
  - Why: Already used in project for scheduling

- [LiteLLM Provider Routing](https://docs.litellm.ai/docs/providers)
  - Specific section: Model naming conventions
  - Why: Proper model selection for heartbeat (anthropic/claude-haiku-4-5)

### Patterns to Follow

**Naming Conventions:**
```python
# Services: {domain}_service.py
# Models: {domain}_models.py  
# CRUD: {domain}_crud.py
# API: {domain}.py (in api/)
# Tests: test_{module_name}.py

# Functions: snake_case
# Classes: PascalCase
# Constants: UPPER_SNAKE_CASE
```

**Error Handling:**
```python
# Pattern from services/context_service.py
try:
    # operation
    logger.info(f"Success message with context")
except Exception as e:
    logger.error(f"Error context: {e}")
    return default_value  # Graceful degradation
```

**Logging Pattern:**
```python
# Pattern from all services
from core.config import get_logger
logger = get_logger("heartbeat_service")

logger.info(f"Heartbeat started for user {user_id}")
logger.warning(f"Skipping heartbeat: {reason}")
logger.error(f"Heartbeat failed: {e}", exc_info=True)
```

**Pydantic Models:**
```python
# Pattern from core/models.py and core/user_context_models.py
from pydantic import BaseModel, Field
from datetime import datetime, timezone

class MyModel(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str, datetime: lambda dt: dt.isoformat()}
```

**MongoDB Collection Getters:**
```python
# Pattern from db/mongodb.py
def get_heartbeat_insights_collection():
    """Get the heartbeat insights collection."""
    db = get_database()
    return db["heartbeat_insights"]
```

**API Router Pattern:**
```python
# Pattern from api/user_profile.py
from fastapi import APIRouter, HTTPException
router = APIRouter(prefix="/api/heartbeat", tags=["heartbeat"])

@router.get("/insights")
async def get_insights_endpoint(user_id: str = "default"):
    # implementation
```

**AsyncIOScheduler Pattern:**
```python
# Pattern from services/task_scheduler.py
class MyScheduler:
    def __init__(self):
        self.running = False
        self._task = None
    
    async def start(self):
        if self.running:
            return
        self.running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Scheduler started")
    
    async def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
```

---

## IMPLEMENTATION PLAN

### Phase 1: Data Models & Database

Create foundational data structures for heartbeat configuration and insights.

**Tasks:**
- Define HeartbeatConfig model (interval, active hours, enabled flag)
- Define ProactiveInsight model (type, title, description, action data)
- Create MongoDB collection getter
- Add goals_document field to UserProfile model

### Phase 2: Core Heartbeat Service

Implement the background service that runs periodic heartbeats.

**Tasks:**
- Create HeartbeatService class with AsyncIOScheduler
- Implement context gathering (goals, conversations, tasks)
- Implement LLM prompt generation
- Implement insight creation logic
- Add HEARTBEAT_OK detection pattern

### Phase 3: CRUD & API Layer

Build database operations and REST API endpoints.

**Tasks:**
- Implement heartbeat_crud.py (create/get/list/dismiss insights)
- Create API router with endpoints
- Integrate heartbeat service into main.py lifespan
- Add user profile endpoints for goals document

### Phase 4: Frontend Integration

Build UI components for goals editing and insight notifications.

**Tasks:**
- Create GoalsEditor component in Settings
- Create ProactiveInsightsPanel notification UI
- Add API client functions
- Integrate notification bell icon in header
- Wire up dismiss/archive functionality

### Phase 5: Testing & Validation

Comprehensive testing of all components.

**Tasks:**
- Unit tests for heartbeat service
- Integration tests for API endpoints
- Test timezone-aware scheduling
- Test HEARTBEAT_OK detection
- Manual validation of end-to-end flow

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.


### CREATE backend/core/heartbeat_models.py

- **IMPLEMENT**: Pydantic models for heartbeat configuration and insights
- **PATTERN**: Mirror `backend/core/user_context_models.py` and `backend/core/models.py`
- **IMPORTS**: 
  ```python
  from pydantic import BaseModel, Field, constr
  from typing import Optional, Dict, Any, List
  from datetime import datetime, timezone
  from bson import ObjectId
  ```
- **MODELS**:
  - `ActiveHours`: start/end times (HH:MM format), timezone (optional)
  - `HeartbeatConfig`: enabled, interval (str, e.g. "2h"), active_hours, model_name, max_insights_per_day
  - `ProactiveInsight`: id, user_id, insight_type, title, description, action_data, dismissed, created_at
  - `InsightCreatePayload`: Fields for creating new insight
  - `HeartbeatConfigUpdate`: Fields for updating config
- **GOTCHA**: Use `Field(default_factory=lambda: datetime.now(timezone.utc))` for timestamps
- **GOTCHA**: Add `class Config` with `populate_by_name = True` and json_encoders for ObjectId/datetime
- **VALIDATE**: `python -c "from backend.core.heartbeat_models import HeartbeatConfig, ProactiveInsight; print('Models loaded')"`

### UPDATE backend/core/user_context_models.py

- **ADD**: `goals_document` field to UserProfile model
- **PATTERN**: Follow existing optional string fields like `current_projects`
- **IMPLEMENTATION**:
  ```python
  goals_document: Optional[str] = Field(None, max_length=2000)
  ```
- **GOTCHA**: Add to both UserProfile and UserProfileUpdatePayload classes
- **VALIDATE**: `python -c "from backend.core.user_context_models import UserProfile; u = UserProfile(name='test', communication_style='pro', goals_document='test'); print('Field added')"`

### CREATE backend/db/heartbeat_crud.py

- **IMPLEMENT**: CRUD operations for heartbeat insights
- **PATTERN**: Mirror `backend/db/user_profiles_crud.py` structure
- **IMPORTS**:
  ```python
  from datetime import datetime, timezone
  from typing import Dict, Optional, Any, List
  from bson import ObjectId
  from db.mongodb import get_database
  from core.config import get_logger
  ```
- **FUNCTIONS**:
  - `get_heartbeat_insights_collection()`: Return db["heartbeat_insights"]
  - `_serialize(doc)`: Convert ObjectId to string (pattern from user_profiles_crud)
  - `create_insight(insight_data, user_id)`: Insert and return serialized doc
  - `get_insights(user_id, limit, dismissed)`: Query with filters, sort by created_at desc
  - `dismiss_insight(insight_id, user_id)`: Set dismissed=True
  - `count_insights_today(user_id)`: Count non-dismissed insights created today
- **GOTCHA**: Always filter by user_id for security
- **GOTCHA**: Use `datetime.now(timezone.utc)` for timezone-aware timestamps
- **VALIDATE**: `python -c "from backend.db.heartbeat_crud import get_heartbeat_insights_collection; print(get_heartbeat_insights_collection())"`

### CREATE backend/services/heartbeat_service.py

- **IMPLEMENT**: Core heartbeat scheduler and logic
- **PATTERN**: Mirror `backend/services/task_scheduler.py` AsyncIOScheduler pattern
- **IMPORTS**:
  ```python
  import asyncio
  from datetime import datetime, timezone, time as dt_time
  from typing import Optional, Dict, Any
  from services.provider_service import chat_with_provider
  from services.context_service import get_user_context
  from db.heartbeat_crud import create_insight, count_insights_today, get_heartbeat_insights_collection
  from db.user_profiles_crud import get_user_profile
  from db.crud import get_all_conversations
  from db.tasks_crud import list_tasks
  from core.config import get_logger
  ```
- **CLASS**: HeartbeatService with __init__, start(), stop(), _heartbeat_loop()
- **IMPLEMENTATION**:
  - `__init__`: Initialize running=False, _task=None, check_interval=300 (5 min)
  - `start()`: Set running=True, create asyncio task for _heartbeat_loop()
  - `stop()`: Cancel task, set running=False
  - `_heartbeat_loop()`: While running, check if heartbeat due, run if yes, sleep check_interval
  - `_is_heartbeat_due(user_id)`: Check last run time + interval vs now, check active hours
  - `_in_active_hours(config, now)`: Parse active_hours, check if now is within window
  - `run_heartbeat(user_id)`: Main heartbeat logic
    - Get user profile and config
    - Check if enabled and within max_insights_per_day
    - Gather context (goals, recent convos, active tasks)
    - Build prompt
    - Call LLM
    - Parse response for HEARTBEAT_OK
    - Create insight if not OK
- **GOTCHA**: Parse interval string ("2h" -> 7200 seconds) using regex
- **GOTCHA**: Handle timezone conversion for active_hours (use pytz or zoneinfo)
- **GOTCHA**: Strip HEARTBEAT_OK from start/end of response (case-insensitive)
- **VALIDATE**: `python -c "from backend.services.heartbeat_service import HeartbeatService; s = HeartbeatService(); print('Service created')"`

### UPDATE backend/db/mongodb.py

- **ADD**: Collection getter for heartbeat insights
- **PATTERN**: Follow existing collection getters (lines 68-91)
- **IMPLEMENTATION**:
  ```python
  def get_heartbeat_insights_collection():
      """Get the heartbeat insights collection."""
      db = get_database()
      return db["heartbeat_insights"]
  ```
- **LOCATION**: Add after `get_settings_collection()` function
- **VALIDATE**: `python -c "from backend.db.mongodb import get_heartbeat_insights_collection; print(get_heartbeat_insights_collection())"`

### CREATE backend/api/heartbeat.py

- **IMPLEMENT**: REST API endpoints for heartbeat management
- **PATTERN**: Mirror `backend/api/user_profile.py` structure
- **IMPORTS**:
  ```python
  from fastapi import APIRouter, HTTPException
  from typing import List
  from core.heartbeat_models import ProactiveInsight, HeartbeatConfigUpdate
  from db.heartbeat_crud import get_insights, dismiss_insight, create_insight
  from db.user_profiles_crud import get_user_profile, upsert_user_profile
  from services.heartbeat_service import heartbeat_service
  ```
- **ROUTER**: `router = APIRouter(prefix="/api/heartbeat", tags=["heartbeat"])`
- **ENDPOINTS**:
  - `GET /insights`: List insights (query params: user_id, limit, dismissed)
  - `POST /insights/{insight_id}/dismiss`: Dismiss an insight
  - `GET /config`: Get heartbeat config from user profile
  - `PUT /config`: Update heartbeat config in user profile
  - `POST /trigger`: Manually trigger heartbeat (for testing)
- **GOTCHA**: Return 404 if user_id not found
- **GOTCHA**: Validate insight_id belongs to user_id before dismissing
- **VALIDATE**: `python -c "from backend.api.heartbeat import router; print(router.routes)"`

### UPDATE backend/main.py

- **ADD**: Import and start heartbeat service in lifespan
- **PATTERN**: Follow task_scheduler pattern (lines 20-50)
- **IMPORTS**:
  ```python
  from services.heartbeat_service import HeartbeatService
  ```
- **IMPLEMENTATION**:
  - Create global `heartbeat_service = HeartbeatService()` instance
  - In lifespan startup: `await heartbeat_service.start()`
  - In lifespan shutdown: `await heartbeat_service.stop()`
  - Include heartbeat router: `app.include_router(heartbeat.router)`
- **LOCATION**: Add after task_scheduler initialization
- **VALIDATE**: Start server and check logs for "Heartbeat service started"

### UPDATE backend/db/user_profiles_crud.py

- **ADD**: Helper function to get/set heartbeat config
- **PATTERN**: Follow existing upsert_user_profile pattern
- **IMPLEMENTATION**:
  ```python
  def get_heartbeat_config(user_id: str = "default") -> Optional[Dict[str, Any]]:
      profile = get_user_profile(user_id)
      return profile.get("heartbeat_config") if profile else None
  
  def update_heartbeat_config(user_id: str, config: Dict[str, Any]) -> bool:
      try:
          collection = get_user_profiles_collection()
          result = collection.update_one(
              {"user_id": user_id},
              {"$set": {"heartbeat_config": config, "updated_at": datetime.now(timezone.utc)}}
          )
          return result.modified_count > 0
      except Exception as e:
          logger.error(f"Error updating heartbeat config: {e}")
          return False
  ```
- **VALIDATE**: `python -c "from backend.db.user_profiles_crud import get_heartbeat_config; print('Functions added')"`

### CREATE backend/tests/test_heartbeat_service.py

- **IMPLEMENT**: Unit tests for heartbeat service
- **PATTERN**: Mirror `backend/tests/test_chat_service.py` structure
- **IMPORTS**:
  ```python
  import pytest
  from unittest.mock import AsyncMock, MagicMock, patch
  from datetime import datetime, timezone
  from services.heartbeat_service import HeartbeatService
  ```
- **TEST CASES**:
  - `test_parse_interval`: Test "1h", "30m", "2h" parsing
  - `test_in_active_hours`: Test timezone-aware active hours checking
  - `test_heartbeat_ok_detection`: Test HEARTBEAT_OK stripping
  - `test_context_gathering`: Mock and verify context assembly
  - `test_max_insights_per_day`: Verify daily limit enforcement
  - `test_disabled_heartbeat`: Verify skipping when disabled
- **GOTCHA**: Use `@pytest.mark.asyncio` for async tests
- **GOTCHA**: Mock MongoDB collections and LLM calls
- **VALIDATE**: `cd backend && pytest tests/test_heartbeat_service.py -v`

### CREATE backend/tests/test_heartbeat_api.py

- **IMPLEMENT**: Integration tests for API endpoints
- **PATTERN**: Mirror `backend/tests/test_user_profile_api.py`
- **IMPORTS**:
  ```python
  import pytest
  from fastapi.testclient import TestClient
  from unittest.mock import patch, MagicMock
  from main import app
  ```
- **TEST CASES**:
  - `test_get_insights`: Test listing insights
  - `test_dismiss_insight`: Test dismissing an insight
  - `test_get_config`: Test retrieving config
  - `test_update_config`: Test updating config
  - `test_trigger_heartbeat`: Test manual trigger
- **GOTCHA**: Mock MongoDB operations in conftest.py
- **VALIDATE**: `cd backend && pytest tests/test_heartbeat_api.py -v`


### CREATE frontend/src/services/heartbeatApi.js

- **IMPLEMENT**: API client for heartbeat endpoints
- **PATTERN**: Mirror existing API service files in frontend/src/services/
- **IMPORTS**:
  ```javascript
  import axios from 'axios';
  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
  ```
- **FUNCTIONS**:
  - `getInsights(userId, dismissed)`: GET /heartbeat/insights
  - `dismissInsight(insightId, userId)`: POST /heartbeat/insights/{id}/dismiss
  - `getHeartbeatConfig(userId)`: GET /heartbeat/config
  - `updateHeartbeatConfig(userId, config)`: PUT /heartbeat/config
  - `triggerHeartbeat(userId)`: POST /heartbeat/trigger
- **GOTCHA**: Handle axios errors with try/catch
- **GOTCHA**: Return data.insights or data.config from responses
- **VALIDATE**: `cd frontend && npm run build` (check for syntax errors)

### CREATE frontend/src/components/GoalsEditor.jsx

- **IMPLEMENT**: Markdown editor for user goals document
- **PATTERN**: Follow existing form components in frontend/src/components/
- **IMPORTS**:
  ```javascript
  import React, { useState, useEffect } from 'react';
  import axios from 'axios';
  ```
- **COMPONENT**: Functional component with textarea for goals
- **STATE**: goals (string), loading (bool), saved (bool)
- **FUNCTIONS**:
  - `useEffect`: Load goals from user profile on mount
  - `handleSave`: PUT to /api/user-profile with goals_document
  - `handleChange`: Update local state
- **UI ELEMENTS**:
  - Textarea (rows=10, placeholder="Enter your goals and priorities...")
  - Save button (disabled while loading)
  - Success message (show briefly after save)
- **STYLING**: Use Tailwind classes matching existing components
- **GOTCHA**: Debounce save to avoid excessive API calls
- **VALIDATE**: Import in Settings page and verify rendering

### CREATE frontend/src/components/ProactiveInsightsPanel.jsx

- **IMPLEMENT**: Notification panel for proactive insights
- **PATTERN**: Follow sidebar/panel patterns from existing components
- **IMPORTS**:
  ```javascript
  import React, { useState, useEffect } from 'react';
  import { Bell, X, CheckCircle } from 'lucide-react';
  import { getInsights, dismissInsight } from '../services/heartbeatApi';
  ```
- **COMPONENT**: Dropdown panel triggered by bell icon
- **STATE**: insights (array), isOpen (bool), loading (bool)
- **FUNCTIONS**:
  - `useEffect`: Poll for insights every 60 seconds when open
  - `handleDismiss(insightId)`: Call dismissInsight API, remove from local state
  - `togglePanel()`: Toggle isOpen state
- **UI ELEMENTS**:
  - Bell icon with badge (count of undismissed insights)
  - Dropdown panel (absolute positioned)
  - Insight cards (title, description, dismiss button)
  - Empty state ("No insights right now")
- **STYLING**: Match existing modal/dropdown styles
- **GOTCHA**: Click outside to close (use ref and event listener)
- **GOTCHA**: Stop polling when panel closed
- **VALIDATE**: Add to App.jsx header and verify rendering

### UPDATE frontend/src/App.jsx

- **ADD**: ProactiveInsightsPanel to header
- **PATTERN**: Follow existing header component structure
- **IMPLEMENTATION**:
  - Import ProactiveInsightsPanel
  - Add component next to existing header icons
  - Position with flexbox (ml-auto for right alignment)
- **LOCATION**: In header div, after model picker
- **VALIDATE**: `npm run dev` and check header renders correctly

### UPDATE frontend/src/pages/SettingsPage.jsx

- **ADD**: Goals tab with GoalsEditor component
- **PATTERN**: Follow existing tab structure in SettingsPage
- **IMPLEMENTATION**:
  - Add "Goals & Priorities" tab
  - Render GoalsEditor when tab active
  - Add heartbeat config section (enable/disable, interval, active hours)
- **LOCATION**: After User Profile tab
- **VALIDATE**: Navigate to Settings and verify Goals tab appears

---

## TESTING STRATEGY

### Unit Tests

**Backend (pytest):**
- Test heartbeat service logic in isolation
- Mock MongoDB collections using fixtures from conftest.py
- Mock LLM calls with AsyncMock
- Test edge cases: disabled config, outside active hours, max insights reached
- Test interval parsing and timezone conversions

**Pattern from existing tests:**
```python
@pytest.mark.asyncio
async def test_function():
    with patch('module.function') as mock_func:
        mock_func.return_value = expected_value
        result = await function_under_test()
        assert result == expected_value
```

### Integration Tests

**API Endpoints (pytest + TestClient):**
- Test full request/response cycle for each endpoint
- Verify authentication and authorization
- Test error cases (404, 400, 500)
- Verify MongoDB operations execute correctly

**Pattern:**
```python
def test_endpoint(client):
    response = client.get("/api/heartbeat/insights?user_id=test")
    assert response.status_code == 200
    assert "insights" in response.json()
```

### Edge Cases

**Timezone Handling:**
- Test active hours across timezone boundaries
- Test DST transitions
- Test invalid timezone strings

**Rate Limiting:**
- Test max_insights_per_day enforcement
- Test daily counter reset at midnight

**HEARTBEAT_OK Detection:**
- Test "HEARTBEAT_OK" at start of response
- Test "HEARTBEAT_OK" at end of response
- Test "HEARTBEAT_OK" in middle (should not strip)
- Test case-insensitive matching

**Context Gathering:**
- Test with no goals document
- Test with no recent conversations
- Test with no active tasks
- Test with all context present

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
# Python linting (if configured)
cd backend
python -m flake8 services/heartbeat_service.py core/heartbeat_models.py db/heartbeat_crud.py api/heartbeat.py

# Import validation
python -c "from services.heartbeat_service import HeartbeatService; print('✓ Imports valid')"
python -c "from core.heartbeat_models import HeartbeatConfig, ProactiveInsight; print('✓ Models valid')"
python -c "from db.heartbeat_crud import create_insight, get_insights; print('✓ CRUD valid')"
python -c "from api.heartbeat import router; print('✓ API valid')"
```

### Level 2: Unit Tests

```bash
cd backend

# Run heartbeat service tests
pytest tests/test_heartbeat_service.py -v

# Run heartbeat API tests
pytest tests/test_heartbeat_api.py -v

# Run all tests to check for regressions
pytest tests/ -v
```

### Level 3: Integration Tests

```bash
# Start backend server
cd backend
uvicorn main:app --reload --port 8000 &
SERVER_PID=$!

# Wait for server to start
sleep 5

# Test API endpoints
curl -X GET "http://localhost:8000/api/heartbeat/insights?user_id=default"
curl -X GET "http://localhost:8000/api/heartbeat/config?user_id=default"
curl -X POST "http://localhost:8000/api/heartbeat/trigger?user_id=default"

# Stop server
kill $SERVER_PID
```

### Level 4: Manual Validation

**Backend:**
1. Start server: `uvicorn main:app --reload --port 8000`
2. Check logs for "Heartbeat service started"
3. Create user profile with goals document via API
4. Enable heartbeat in config
5. Trigger manual heartbeat: `curl -X POST http://localhost:8000/api/heartbeat/trigger?user_id=default`
6. Verify insight created: `curl http://localhost:8000/api/heartbeat/insights?user_id=default`

**Frontend:**
1. Start dev server: `npm run dev`
2. Navigate to Settings → Goals & Priorities
3. Enter goals document and save
4. Enable heartbeat in config
5. Check header for bell icon
6. Click bell icon to open insights panel
7. Verify insights appear (may need to wait for heartbeat interval)
8. Dismiss an insight and verify it disappears

**End-to-End:**
1. Set heartbeat interval to "5m" for testing
2. Set active hours to current time window
3. Wait 5 minutes
4. Verify insight appears in panel
5. Verify insight is relevant to goals and recent activity

### Level 5: Additional Validation

**MongoDB Verification:**
```bash
# Connect to MongoDB
mongosh

# Check collections exist
use mcp_chat_db
show collections  # Should include heartbeat_insights

# Check insight documents
db.heartbeat_insights.find().pretty()

# Check user profile has goals_document
db.user_profiles.find({"user_id": "default"}).pretty()
```

**Timezone Testing:**
```python
# Test active hours with different timezones
python -c "
from services.heartbeat_service import HeartbeatService
from datetime import datetime, timezone
import pytz

service = HeartbeatService()
config = {
    'active_hours': {
        'start': '09:00',
        'end': '17:00',
        'timezone': 'America/New_York'
    }
}

# Test at 10 AM EST (should be active)
now = datetime(2026, 2, 20, 15, 0, tzinfo=timezone.utc)  # 10 AM EST
print('10 AM EST:', service._in_active_hours(config, now))

# Test at 6 PM EST (should be inactive)
now = datetime(2026, 2, 20, 23, 0, tzinfo=timezone.utc)  # 6 PM EST
print('6 PM EST:', service._in_active_hours(config, now))
"
```

---

## ACCEPTANCE CRITERIA

- [ ] Heartbeat service starts/stops with FastAPI lifespan
- [ ] Heartbeat runs at configured intervals (default 2h)
- [ ] Active hours are respected (timezone-aware)
- [ ] Goals document can be edited in Settings UI
- [ ] Insights are created when LLM returns non-OK response
- [ ] HEARTBEAT_OK responses are properly detected and suppressed
- [ ] Insights appear in notification panel with bell icon
- [ ] Insights can be dismissed via UI
- [ ] Max insights per day limit is enforced
- [ ] Disabled heartbeat config prevents execution
- [ ] Manual trigger endpoint works for testing
- [ ] All unit tests pass (100% of new code)
- [ ] All integration tests pass
- [ ] No regressions in existing functionality
- [ ] MongoDB collections created correctly
- [ ] API endpoints return proper status codes
- [ ] Frontend components render without errors
- [ ] Timezone conversions work correctly
- [ ] Context gathering includes goals, conversations, tasks
- [ ] LLM prompts are well-formed and cost-effective

---

## COMPLETION CHECKLIST

- [ ] All backend models created and validated
- [ ] All CRUD operations implemented and tested
- [ ] Heartbeat service implemented with scheduler
- [ ] API endpoints created and tested
- [ ] Service integrated into main.py lifespan
- [ ] All backend unit tests pass
- [ ] All backend integration tests pass
- [ ] Frontend API client created
- [ ] GoalsEditor component created and functional
- [ ] ProactiveInsightsPanel component created and functional
- [ ] Components integrated into App.jsx and SettingsPage
- [ ] Frontend builds without errors
- [ ] Manual end-to-end testing completed
- [ ] MongoDB collections verified
- [ ] Timezone handling tested
- [ ] Documentation updated (if applicable)
- [ ] Code reviewed for quality and maintainability

---

## NOTES

### Design Decisions

**Why AsyncIOScheduler over APScheduler BackgroundScheduler?**
- AsyncIOScheduler integrates better with FastAPI's async architecture
- Avoids thread safety issues with async database operations
- Matches existing pattern in task_scheduler.py

**Why notification panel instead of conversation messages?**
- Avoids cluttering conversation history
- User can dismiss insights without affecting chat context
- Familiar UX pattern (like GitHub notifications)
- Easier to implement batching/grouping in future

**Why HEARTBEAT_OK pattern?**
- Reduces noise when nothing needs attention
- Saves frontend rendering and database storage
- Mirrors OpenClaw's proven approach
- Allows LLM to self-regulate output

**Why goals document instead of structured fields?**
- More flexible for users (free-form text)
- Easier to edit and maintain
- Can include context that doesn't fit structured fields
- Natural language works better with LLM prompts

### Trade-offs

**Polling vs WebSocket for insights:**
- Chose polling (60s interval) for simplicity
- WebSocket would be more real-time but adds complexity
- Insights are not time-critical (2h heartbeat interval)
- Can upgrade to WebSocket in Phase 2 if needed

**In-memory scheduler vs database-backed:**
- Chose in-memory for Phase 1 (simpler)
- Scheduled heartbeats lost on restart (acceptable for Phase 1)
- Phase 2 can add persistence if needed

**Single global heartbeat vs per-user:**
- Chose single service that iterates users
- Simpler implementation and resource management
- Can scale to per-user workers in Phase 2

### Future Enhancements (Phase 2+)

**Action Buttons:**
- Add "Create Task" button to insights
- Add "Run Search" button to insights
- Track which actions users accept/dismiss

**Approval Queue:**
- Add approval workflow for sensitive actions
- Show pending actions in separate panel
- One-click approve/reject

**Autonomous Actions (Phase 3):**
- Auto-execute approved action types
- Add permissions system (can_create_tasks, can_run_searches)
- Add audit log for autonomous actions

**Advanced Context:**
- Include pinned conversation summaries
- Include recent MCP tool usage
- Include calendar/schedule data (if integrated)

**Smarter Prompts:**
- Use few-shot examples for better insight quality
- Add domain-specific prompts (marketing, sales, dev)
- Personalize based on user interaction patterns

### Cost Considerations

**Token Usage per Heartbeat:**
- Context: ~500 tokens (goals + recent activity)
- Prompt: ~200 tokens
- Response: ~100 tokens (avg)
- **Total: ~800 tokens per heartbeat**

**Daily Cost (2h interval, Haiku):**
- 12 heartbeats/day × 800 tokens = 9,600 tokens/day
- Haiku: $0.25 per 1M input tokens, $1.25 per 1M output tokens
- **Cost: ~$0.01 per user per day**

**Optimization Strategies:**
- Use cheaper models (Haiku vs Sonnet)
- Increase interval during low-activity periods
- Skip heartbeat if no recent activity
- Cache context when possible

---

## CONFIDENCE SCORE

**8/10** - High confidence for one-pass implementation success

**Strengths:**
- Clear patterns from existing codebase (task_scheduler, user_profiles)
- Well-defined data models and API contracts
- Comprehensive testing strategy
- Detailed validation commands

**Risks:**
- Timezone handling complexity (mitigated by using existing schedule_utils)
- LLM prompt quality (requires iteration, but framework is solid)
- Frontend polling performance (acceptable for Phase 1, can optimize later)

**Mitigation:**
- Start with manual trigger endpoint for testing
- Use existing timezone utilities from schedule_utils.py
- Test with multiple timezones before deploying
- Monitor token costs and adjust intervals if needed


---

## BRAND STANDARDS COMPLIANCE

All frontend components MUST follow the OhSee Brand Standards Guide (`BRAND_STANDARDS_GUIDE.md`).

### Color Palette Usage

**Primary Colors:**
- Brand Purple (`#A78BFA`): Primary buttons, bell icon, active states
- Brand Blue (`#60A5FA`): Secondary accents, links
- Brand Accent (`#FCD34D`): Highlights (use sparingly)

**Backgrounds:**
- Main Background (`#121212`): Application background
- Surface Background (`#1E1E1E`): Cards, panels, modals
- Border Gray (`#374151`): Borders and dividers

**Text Colors:**
- Primary Text (`#FFFFFF`): Main content
- Secondary Text (`#D1D5DB`): Labels, descriptions
- Accent Text (`#A78BFA`): Brand elements

**Status Colors:**
- Success Green (`#10B981`): Success states
- Alert Red (`#EF4444`): Error states, dismiss actions
- Stat Blue (`#3B82F6`): Interactive elements

### Component-Specific Standards

**GoalsEditor Component:**
```jsx
// Container
<div className="bg-brand-surface-bg rounded-lg shadow border border-gray-700 p-6">
  
  // Textarea
  <textarea 
    className="w-full bg-brand-main-bg text-brand-text-primary border border-gray-600 
               focus:outline-none focus:ring-2 focus:ring-brand-purple rounded p-3"
    rows={10}
    placeholder="Enter your goals and priorities..."
  />
  
  // Save Button
  <button className="bg-brand-purple text-white rounded-md px-4 py-2 
                     hover:bg-brand-button-grad-to transition-colors duration-200
                     focus:outline-none focus:ring-2 focus:ring-brand-blue">
    Save Goals
  </button>
  
  // Success Message
  <div className="text-brand-success-green text-sm">
    ✓ Goals saved successfully
  </div>
</div>
```

**ProactiveInsightsPanel Component:**
```jsx
// Bell Icon Button
<button className="relative p-2 rounded-md hover:bg-gray-700 
                   focus:outline-none focus:ring-2 focus:ring-brand-purple">
  <Bell className="w-5 h-5 text-brand-purple" />
  
  // Badge (insight count)
  {count > 0 && (
    <span className="absolute -top-1 -right-1 bg-brand-alert-red text-white 
                     text-xs rounded-full w-5 h-5 flex items-center justify-center">
      {count}
    </span>
  )}
</button>

// Dropdown Panel
<div className="absolute right-0 mt-2 w-80 bg-brand-surface-bg rounded-lg shadow-lg 
                border border-gray-700 max-h-96 overflow-y-auto">
  
  // Header
  <div className="p-4 border-b border-gray-700">
    <h3 className="text-lg font-semibold text-brand-text-primary">
      Proactive Insights
    </h3>
  </div>
  
  // Insight Card
  <div className="p-4 border-b border-gray-700 hover:bg-gray-700 transition-colors">
    <div className="flex justify-between items-start">
      <div className="flex-1">
        <h4 className="text-sm font-semibold text-brand-text-primary mb-1">
          {insight.title}
        </h4>
        <p className="text-sm text-brand-text-secondary">
          {insight.description}
        </p>
      </div>
      
      // Dismiss Button
      <button className="ml-2 p-1 rounded hover:bg-gray-600 
                         focus:outline-none focus:ring-2 focus:ring-brand-purple">
        <X className="w-4 h-4 text-brand-text-secondary hover:text-brand-alert-red" />
      </button>
    </div>
    
    // Timestamp
    <div className="text-xs text-brand-text-secondary mt-2">
      {formatTimestamp(insight.created_at)}
    </div>
  </div>
  
  // Empty State
  <div className="p-8 text-center text-brand-text-secondary">
    No insights right now
  </div>
</div>
```

**Settings Page Integration:**
```jsx
// Goals Tab Button
<button className={`px-4 py-2 rounded-t-lg transition-colors ${
  activeTab === 'goals' 
    ? 'bg-brand-purple text-white' 
    : 'bg-gray-700 text-brand-text-secondary hover:bg-gray-600'
}`}>
  Goals & Priorities
</button>

// Heartbeat Config Section
<div className="bg-brand-surface-bg rounded-lg shadow border border-gray-700 p-6 space-y-4">
  <h3 className="text-lg font-semibold text-brand-text-primary">
    Heartbeat Settings
  </h3>
  
  // Toggle Switch
  <label className="flex items-center space-x-3">
    <input 
      type="checkbox" 
      className="w-5 h-5 text-brand-purple bg-brand-main-bg border-gray-600 
                 rounded focus:ring-2 focus:ring-brand-purple"
    />
    <span className="text-brand-text-primary">Enable proactive insights</span>
  </label>
  
  // Interval Select
  <div>
    <label className="block text-sm text-brand-text-secondary mb-2">
      Check interval
    </label>
    <select className="w-full bg-brand-main-bg text-brand-text-primary 
                       border border-gray-600 rounded p-2
                       focus:outline-none focus:ring-2 focus:ring-brand-purple">
      <option value="1h">Every hour</option>
      <option value="2h">Every 2 hours</option>
      <option value="4h">Every 4 hours</option>
    </select>
  </div>
</div>
```

### Typography Standards

**Font Sizes:**
- Insight titles: `text-sm font-semibold` (14px, 600 weight)
- Insight descriptions: `text-sm` (14px, 400 weight)
- Panel headers: `text-lg font-semibold` (18px, 600 weight)
- Timestamps: `text-xs` (12px, 400 weight)
- Button text: `text-base` (16px, 400 weight)

**Font Family:**
```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
```

### Spacing Standards

**Component Spacing:**
- Panel padding: `p-4` (16px)
- Card padding: `p-4` (16px)
- Section spacing: `space-y-4` (16px between elements)
- Button padding: `px-4 py-2` (16px horizontal, 8px vertical)
- Icon button padding: `p-2` (8px)

**Layout Spacing:**
- Between insights: `border-b border-gray-700` (separator)
- Panel margins: `mt-2` (8px from trigger)
- Modal spacing: `p-6` (24px for major sections)

### Interactive States

**Hover Effects:**
```css
hover:bg-gray-700          // Cards, list items
hover:bg-brand-button-grad-to  // Primary buttons
hover:text-brand-alert-red     // Dismiss icons
transition-colors duration-200  // All interactive elements
```

**Focus States:**
```css
focus:outline-none
focus:ring-2 focus:ring-brand-purple  // All focusable elements
```

**Loading States:**
```jsx
// Loading spinner
<div className="animate-spin rounded-full h-5 w-5 border-2 
                border-brand-purple border-t-transparent" />

// Loading text
<span className="text-brand-text-secondary animate-pulse">
  Loading insights...
</span>
```

### Accessibility Requirements

**Minimum Touch Targets:**
- All buttons: minimum 44px × 44px
- Icon buttons: `p-2` with icon size `w-5 h-5` = 44px total

**Keyboard Navigation:**
- All interactive elements must have visible focus rings
- Tab order must be logical (bell → insights → dismiss buttons)
- Escape key closes panel

**ARIA Labels:**
```jsx
<button aria-label="View proactive insights" aria-expanded={isOpen}>
  <Bell aria-hidden="true" />
</button>

<button aria-label={`Dismiss insight: ${insight.title}`}>
  <X aria-hidden="true" />
</button>
```

**Color Contrast:**
- All text meets WCAG AA standards (4.5:1 minimum)
- Status indicators use sufficient contrast
- Focus rings are clearly visible

### Responsive Design

**Mobile Adaptations:**
```jsx
// Panel width adjusts for mobile
<div className="w-80 sm:w-96 md:w-[400px]">

// Text sizing
<h3 className="text-base sm:text-lg">

// Button sizing
<button className="px-3 py-1.5 sm:px-4 sm:py-2">
```

**Breakpoints:**
- Mobile: Default (< 640px)
- Small: `sm:` (≥ 640px)
- Medium: `md:` (≥ 768px)

### Custom Scrollbar (for insights panel)

```css
/* Add to component or global styles */
.insights-panel::-webkit-scrollbar {
  width: 8px;
}
.insights-panel::-webkit-scrollbar-track {
  background: #1E1E1E;
}
.insights-panel::-webkit-scrollbar-thumb {
  background: #A78BFA;
  border-radius: 4px;
}
.insights-panel::-webkit-scrollbar-thumb:hover {
  background: #8B5CF6;
}
```

### Animation Standards

**Transitions:**
- Color changes: `transition-colors duration-200`
- All properties: `transition-all duration-300 ease-in-out`
- Panel open/close: `transition-opacity duration-200`

**Animations:**
- Fade in: 0.5s ease-out
- Slide down: 0.3s ease-out
- Spin (loading): continuous rotation

### Implementation Checklist

Frontend components MUST include:
- [ ] Correct color classes from brand palette
- [ ] Proper spacing using defined scale
- [ ] Hover and focus states on all interactive elements
- [ ] Accessible ARIA labels and keyboard navigation
- [ ] Responsive design with mobile breakpoints
- [ ] Loading and empty states
- [ ] Consistent typography (sizes, weights, family)
- [ ] Proper transition/animation timing
- [ ] Custom scrollbar styling (where applicable)
- [ ] Minimum 44px touch targets

### Validation Commands

**Visual Inspection:**
```bash
# Start frontend dev server
cd frontend && npm run dev

# Check components match brand standards:
# 1. Verify colors match palette (use browser DevTools)
# 2. Test hover/focus states on all interactive elements
# 3. Verify spacing matches defined scale
# 4. Test responsive behavior at different breakpoints
# 5. Verify accessibility (keyboard navigation, ARIA labels)
```

**Automated Checks:**
```bash
# Check for non-brand color usage
cd frontend/src
grep -r "bg-blue-" components/  # Should use bg-brand-blue instead
grep -r "text-purple-" components/  # Should use text-brand-purple instead
grep -r "#[0-9A-Fa-f]{6}" components/  # Should use Tailwind classes

# Verify Tailwind config includes brand colors
grep "brand-purple" ../tailwind.config.js
```

