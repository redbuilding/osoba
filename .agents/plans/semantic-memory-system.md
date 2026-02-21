# Feature: Semantic Memory System with nomic-embed-text

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils, types, and models. Import from the right files etc.

## Feature Description

Implement a comprehensive semantic memory system that replaces the limited 5-conversation pinning system with unlimited vector-based conversation storage and retrieval. The system uses ChromaDB for vector storage and nomic-embed-text (via Ollama) for local embeddings, enabling intelligent semantic search across all past conversations. Conversations are automatically indexed after 5+ messages and 10 minutes of inactivity, with manual save options available. The system integrates seamlessly into the existing chat context pipeline, injecting relevant past conversations based on semantic similarity.

## User Story

As an OhSee user
I want unlimited conversation memory with intelligent semantic search
So that the AI can reference any relevant past conversation without manual pinning limits

## Problem Statement

The current conversation pinning system has critical limitations:
- **Hard limit of 5 pinned conversations** - Users must manually manage which conversations to keep in context
- **No semantic search** - Cannot find relevant past conversations by meaning
- **Manual management overhead** - Users must remember to pin/unpin conversations
- **Context inefficiency** - All 5 pinned summaries are included even if irrelevant to current query
- **Scalability issues** - System doesn't scale beyond a handful of conversations

## Solution Statement

Implement a hybrid semantic memory system that:
1. **Stores unlimited conversations** in ChromaDB vector database with embeddings
2. **Auto-indexes conversations** after 5+ messages and 10 minutes idle (non-blocking)
3. **Semantic search** retrieves only relevant past conversations (similarity score > 0.6)
4. **Intelligent chunking** splits long conversations into 512-token chunks with 50-token overlap
5. **Local embeddings** via nomic-embed-text through Ollama (no external API required)
6. **Retention policies** with auto-cleanup (30/90 days/forever options)
7. **Memory Browser UI** for search, preview, and management
8. **Seamless integration** into existing chat context pipeline

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: High
**Primary Systems Affected**: 
- Chat context service (context injection)
- Database layer (new vector DB)
- API routes (new memory endpoints)
- Frontend (Memory Browser, settings, indicators)

**Dependencies**: 
- ChromaDB (v0.4+)
- Ollama (nomic-embed-text model)
- tiktoken (token counting)

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

**Context Service (Existing Pattern to Follow)**
- `backend/services/context_service.py` (lines 1-100) - Why: Shows how context is assembled and injected into chat
- `backend/services/context_service.py` (lines 50-80) - Why: Profile context pattern to mirror for memory context
- `backend/services/chat_service.py` (lines 1-50) - Why: Chat service integration point for memory context

**Database Patterns**
- `backend/db/crud.py` (all) - Why: MongoDB CRUD patterns to follow for conversation operations
- `backend/db/mongodb.py` (all) - Why: Database connection and collection accessor patterns
- `backend/db/heartbeat_crud.py` (all) - Why: Recent example of adding new collection CRUD operations

**API Patterns**
- `backend/api/conversations.py` (all) - Why: Conversation API patterns to extend
- `backend/api/heartbeat.py` (all) - Why: Recent example of new API endpoint structure
- `backend/main.py` (lines 1-50) - Why: Router registration pattern

**Model Patterns**
- `backend/core/models.py` (all) - Why: Pydantic model patterns with ConfigDict
- `backend/core/heartbeat_models.py` (all) - Why: Recent example of new model definitions

**Testing Patterns**
- `backend/tests/test_heartbeat_service.py` (all) - Why: Recent service test example
- `backend/tests/test_heartbeat_api.py` (all) - Why: Recent API test example
- `backend/tests/conftest.py` (all) - Why: Test fixtures and setup patterns

### New Files to Create

**Phase 1: Core Infrastructure**
- `backend/services/embedder.py` - Embedding service (Ollama nomic-embed-text)
- `backend/db/vector_memory.py` - ChromaDB vector storage operations
- `backend/tests/test_semantic_memory_phase1.py` - Phase 1 validation tests

**Phase 2: Conversation Indexing**
- `backend/services/conversation_indexing.py` - Index conversations to vector memory
- `backend/services/memory_tasks.py` - Background auto-indexing task
- `backend/db/crud.py` - Add indexing status methods (UPDATE existing file)
- `backend/api/memory.py` - Memory API endpoints
- `backend/tests/test_semantic_memory_phase2.py` - Phase 2 validation tests

**Phase 3: Chat Integration**
- `backend/services/semantic_memory_context.py` - Build hybrid context (pins + semantic)
- `backend/services/chat_service.py` - Inject memory context (UPDATE existing file)
- `backend/tests/test_semantic_memory_phase3.py` - Phase 3 validation tests

**Phase 4: Frontend UI**
- `frontend/src/components/memory/SaveToMemoryButton.jsx` - Manual save button
- `frontend/src/components/memory/MemoryIndicator.jsx` - Memory status badge
- `frontend/src/components/memory/MemoryBrowser.jsx` - Search and browse UI
- `frontend/src/components/memory/MemorySettings.jsx` - Settings panel
- `frontend/src/components/memory/MemoryStyles.css` - Component styles
- `frontend/src/components/memory/index.js` - Component exports
- `frontend/src/api.js` - Add memory API functions (UPDATE existing file)
- `frontend/src/App.jsx` - Integrate memory components (UPDATE existing file)

**Phase 5: Optimization**
- `backend/services/conversation_summarization.py` - Summarize long conversations before indexing
- `backend/api/memory.py` - Add cleanup and storage endpoints (UPDATE existing file)

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

**Ollama Embeddings API**
- https://github.com/ollama/ollama/blob/main/docs/api.md#generate-embeddings
  - Specific section: Generate Embeddings
  - Why: Required for nomic-embed-text integration via Ollama

**Ollama Python Client**
- https://github.com/ollama/ollama-python#embeddings
  - Specific section: Embeddings usage
  - Why: Shows proper async client usage for embeddings

**ChromaDB Persistent Client**
- https://docs.trychroma.com/usage-guide#persistent-client
  - Specific section: Persistent Client setup
  - Why: Required for persistent vector storage

**ChromaDB Collections API**
- https://docs.trychroma.com/usage-guide#collections
  - Specific section: Creating and managing collections
  - Why: Shows how to create, query, and manage vector collections

**ChromaDB Querying**
- https://docs.trychroma.com/usage-guide#querying-a-collection
  - Specific section: Query with embeddings and filters
  - Why: Required for semantic search implementation

**nomic-embed-text Model**
- https://ollama.com/library/nomic-embed-text
  - Why: Model specifications and usage guidelines

### Patterns to Follow

**Naming Conventions:**
```python
# Services: {domain}_service.py
# CRUD: {domain}_crud.py  
# Models: {domain}_models.py
# API: {domain}.py (in api/)
# Tests: test_{domain}_{type}.py

# Functions: snake_case
# Classes: PascalCase
# Constants: UPPER_SNAKE_CASE
```

**Error Handling:**
```python
# Pattern from heartbeat_service.py
try:
    # Operation
    result = await some_operation()
    return result
except Exception as e:
    logger.error(f"Error in operation: {e}", exc_info=True)
    return default_value
```

**Logging Pattern:**
```python
# Pattern from context_service.py
from core.config import get_logger

logger = get_logger("service_name")

logger.info("Operation started")
logger.error(f"Error: {e}", exc_info=True)
```

**Pydantic Models (v2):**
```python
# Pattern from heartbeat_models.py
from pydantic import BaseModel, Field, ConfigDict

class MyModel(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {...}}
    )
    
    field_name: str = Field(..., description="Field description")
    optional_field: Optional[str] = None
```

**MongoDB CRUD:**
```python
# Pattern from crud.py
from bson import ObjectId
from db import mongodb

def get_collection():
    return mongodb.get_my_collection()

def get_by_id(doc_id: str) -> Optional[Dict[str, Any]]:
    if not ObjectId.is_valid(doc_id):
        return None
    collection = get_collection()
    return collection.find_one({"_id": ObjectId(doc_id)})
```

**API Endpoints:**
```python
# Pattern from heartbeat.py
from fastapi import APIRouter, HTTPException, Query
from typing import List

router = APIRouter(prefix="/api/memory", tags=["memory"])

@router.get("/status")
async def get_memory_status(user_id: str = "default"):
    """Get memory system status."""
    try:
        # Implementation
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Async Patterns:**
```python
# Pattern from chat_service.py
async def async_operation():
    result = await some_async_call()
    return result

# Background tasks (non-blocking)
asyncio.create_task(background_operation())
```

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation (Core Infrastructure)

**Goal**: Set up embedding service and vector storage infrastructure

**Tasks:**
- Create embedding service with Ollama nomic-embed-text integration
- Implement ChromaDB vector storage with persistent client
- Add document chunking with token counting
- Create validation tests for embeddings and vector operations

### Phase 2: Conversation Indexing

**Goal**: Auto-index conversations to vector memory

**Tasks:**
- Implement conversation indexing service
- Add background auto-indexing task (5+ messages, 10 min idle)
- Extend MongoDB CRUD with indexing status tracking
- Create memory API endpoints (manual save, status, stats)
- Add validation tests for indexing workflow

### Phase 3: Chat Context Integration

**Goal**: Inject semantic memory into chat context pipeline

**Tasks:**
- Create semantic memory context builder
- Integrate into chat service context assembly
- Add auto-index trigger after chat completion
- Create validation tests for context injection

### Phase 4: Frontend UI

**Goal**: Build user interface for memory management

**Tasks:**
- Create SaveToMemoryButton component (manual save)
- Create MemoryIndicator component (status badge)
- Create MemoryBrowser component (search and browse)
- Create MemorySettings component (settings panel)
- Integrate components into App.jsx
- Add memory API functions to api.js

### Phase 5: Optimization & Polish

**Goal**: Optimize performance and add cleanup features

**Tasks:**
- Add conversation summarization for long chats
- Implement retention policies (30/90 days/forever)
- Add cleanup endpoint and auto-cleanup task
- Add storage stats endpoint

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### Phase 1: Core Infrastructure

#### Task 1.1: CREATE backend/services/embedder.py

- **IMPLEMENT**: Embedding service with Ollama nomic-embed-text model
- **PATTERN**: Async service pattern from `heartbeat_service.py:18-50`
- **IMPORTS**: `import ollama`, `from ollama import AsyncClient`, `from core.config import get_logger`
- **KEY FEATURES**:
  - `async def embed_text(text: str) -> List[float]` - Single text embedding
  - `async def embed_batch(texts: List[str]) -> List[List[float]]` - Batch embeddings
  - Use `nomic-embed-text` model via Ollama
  - Error handling with fallback to empty embeddings
  - Logging for debugging
- **GOTCHA**: Ollama must be running with nomic-embed-text model pulled (`ollama pull nomic-embed-text`)
- **VALIDATE**: `python -c "from services.embedder import embed_text; import asyncio; print(asyncio.run(embed_text('test')))"`

#### Task 1.2: CREATE backend/db/vector_memory.py

- **IMPLEMENT**: ChromaDB vector storage with persistent client
- **PATTERN**: Database accessor pattern from `mongodb.py:1-50`
- **IMPORTS**: `import chromadb`, `from chromadb import PersistentClient`, `import tiktoken`
- **KEY FEATURES**:
  - `class VectorMemory` with persistent ChromaDB client
  - `add_conversation(conv_id, chunks, embeddings, metadata)` - Store conversation
  - `search_similar(query_embedding, limit, score_threshold)` - Semantic search
  - `delete_conversation(conv_id)` - Remove from memory
  - `get_stats()` - Collection statistics
  - Document chunking with 512 tokens, 50 token overlap
- **GOTCHA**: Use ChromaDB v0.4+ API (`PersistentClient` not deprecated `Settings`)
- **VALIDATE**: `python -c "from db.vector_memory import VectorMemory; vm = VectorMemory(); print(vm.get_stats())"`

#### Task 1.3: UPDATE backend/requirements.txt

- **ADD**: New dependencies for semantic memory
- **LINES TO ADD**:
  ```
  chromadb>=0.4.0
  tiktoken>=0.5.0
  ```
- **GOTCHA**: nomic-embed-text runs via Ollama, no separate Python package needed
- **VALIDATE**: `pip install -r backend/requirements.txt`

#### Task 1.4: CREATE backend/tests/test_semantic_memory_phase1.py

- **IMPLEMENT**: Validation tests for Phase 1 infrastructure
- **PATTERN**: Test structure from `test_heartbeat_service.py:1-50`
- **IMPORTS**: `import pytest`, `from services.embedder import embed_text`, `from db.vector_memory import VectorMemory`
- **TEST CASES**:
  - `test_embedder_imports()` - Module loads correctly
  - `test_embed_single_text()` - Single embedding returns 768-dim vector (nomic-embed-text dimension)
  - `test_vector_memory_operations()` - Add, search, delete work
  - `test_document_chunking()` - Long text splits into multiple chunks
- **GOTCHA**: Tests require Ollama running with nomic-embed-text model
- **VALIDATE**: `cd backend && python -m pytest tests/test_semantic_memory_phase1.py -v`

---

### Phase 2: Conversation Indexing

#### Task 2.1: CREATE backend/services/conversation_indexing.py

- **IMPLEMENT**: Service to index conversations to vector memory
- **PATTERN**: Service pattern from `heartbeat_service.py:160-211`
- **IMPORTS**: `from services.embedder import embed_batch`, `from db.vector_memory import VectorMemory`, `from db.crud import get_conversation_by_id`
- **KEY FEATURES**:
  - `async def index_conversation(conv_id: str)` - Index single conversation
  - `async def find_conversations_to_index()` - Find conversations needing indexing
  - Extract conversation text (user + assistant messages)
  - Chunk long conversations
  - Generate embeddings via embedder service
  - Store in vector memory with metadata
  - Mark conversation as indexed in MongoDB
- **GOTCHA**: Skip conversations with <5 messages
- **VALIDATE**: `python -c "from services.conversation_indexing import index_conversation; import asyncio; asyncio.run(index_conversation('test_id'))"`

#### Task 2.2: CREATE backend/services/memory_tasks.py

- **IMPLEMENT**: Background task for auto-indexing
- **PATTERN**: Background task pattern from `heartbeat_service.py:47-59`
- **IMPORTS**: `import asyncio`, `from services.conversation_indexing import find_conversations_to_index, index_conversation`
- **KEY FEATURES**:
  - `class MemoryTaskService` with start/stop methods
  - Background loop checking every 5 minutes
  - Find conversations with 5+ messages, 10+ min idle, not indexed
  - Index conversations in background (non-blocking)
  - Error handling with retry logic
- **GOTCHA**: Must be started in main.py lifespan
- **VALIDATE**: Service starts without errors

#### Task 2.3: UPDATE backend/db/crud.py

- **ADD**: Indexing status tracking methods
- **PATTERN**: CRUD methods from `crud.py:40-80`
- **NEW FUNCTIONS**:
  - `mark_conversation_indexed(conv_id: str, indexed: bool = True) -> bool`
  - `get_conversation_indexing_status(conv_id: str) -> Dict[str, Any]`
  - `find_conversations_for_auto_indexing(limit: int = 10) -> List[Dict[str, Any]]`
- **IMPLEMENTATION**:
  - Add `indexed_to_memory` field to conversations
  - Add `indexed_at` timestamp field
  - Query for conversations: 5+ messages, 10+ min since last update, not indexed
- **VALIDATE**: `python -c "from db.crud import mark_conversation_indexed; print(mark_conversation_indexed('test'))"`

#### Task 2.4: CREATE backend/api/memory.py

- **IMPLEMENT**: Memory API endpoints
- **PATTERN**: API router from `heartbeat.py:1-95`
- **IMPORTS**: `from fastapi import APIRouter, HTTPException`, `from services.conversation_indexing import index_conversation`
- **ENDPOINTS**:
  - `POST /api/memory/conversations/{id}/save` - Manual save to memory
  - `GET /api/memory/conversations/{id}/status` - Check indexing status
  - `POST /api/memory/auto-index` - Trigger auto-index check
  - `GET /api/memory/stats` - Get memory statistics
- **GOTCHA**: All endpoints need error handling with HTTPException
- **VALIDATE**: `curl http://localhost:8000/api/memory/stats`

#### Task 2.5: UPDATE backend/main.py

- **ADD**: Register memory router and start memory tasks
- **PATTERN**: Router registration from `main.py:30-50`
- **CHANGES**:
  - Import memory router: `from api import memory`
  - Register router: `app.include_router(memory.router)`
  - Start MemoryTaskService in lifespan startup
  - Stop MemoryTaskService in lifespan shutdown
- **VALIDATE**: `curl http://localhost:8000/api/memory/stats` returns valid response

#### Task 2.6: CREATE backend/tests/test_semantic_memory_phase2.py

- **IMPLEMENT**: Validation tests for Phase 2
- **PATTERN**: API tests from `test_heartbeat_api.py:1-133`
- **TEST CASES**:
  - `test_index_conversation()` - Conversation indexes successfully
  - `test_find_conversations_to_index()` - Query finds eligible conversations
  - `test_mark_indexed()` - Status tracking works
  - `test_memory_api_endpoints()` - All API endpoints respond
  - `test_auto_index_task()` - Background task runs
- **VALIDATE**: `cd backend && python -m pytest tests/test_semantic_memory_phase2.py -v`

---

### Phase 3: Chat Context Integration

#### Task 3.1: CREATE backend/services/semantic_memory_context.py

- **IMPLEMENT**: Build hybrid context (pins + semantic memory)
- **PATTERN**: Context building from `context_service.py:50-100`
- **IMPORTS**: `from services.embedder import embed_text`, `from db.vector_memory import VectorMemory`, `from services.context_service import get_conversation_context`
- **KEY FEATURES**:
  - `async def build_memory_context(query: str, user_id: str, current_conv_id: str) -> str`
  - Embed user query
  - Search vector memory for similar conversations (score > 0.6)
  - Exclude current conversation
  - Format results as context string
  - Combine with pinned conversation context
- **GOTCHA**: Limit total context to 2500 chars to avoid token overflow
- **VALIDATE**: `python -c "from services.semantic_memory_context import build_memory_context; import asyncio; print(asyncio.run(build_memory_context('test', 'default', 'conv123')))"`

#### Task 3.2: UPDATE backend/services/chat_service.py

- **ADD**: Inject semantic memory context into chat pipeline
- **PATTERN**: Context injection from `chat_service.py:100-150`
- **CHANGES**:
  - Import: `from services.semantic_memory_context import build_memory_context`
  - In `_build_system_prompt()` or similar, add memory context after profile context
  - Trigger auto-index check after conversation completes (5+ messages)
  - Use `asyncio.create_task()` for non-blocking index trigger
- **GOTCHA**: Memory context should come after profile but before tool results
- **VALIDATE**: Start chat, verify memory context appears in system prompt

#### Task 3.3: CREATE backend/tests/test_semantic_memory_phase3.py

- **IMPLEMENT**: Validation tests for Phase 3
- **PATTERN**: Service tests from `test_chat_service.py:1-100`
- **TEST CASES**:
  - `test_build_memory_context()` - Context builds correctly
  - `test_semantic_search_relevance()` - Only relevant conversations returned
  - `test_chat_integration()` - Memory context injected into chat
  - `test_auto_index_trigger()` - Index triggered after 5+ messages
  - `test_context_size_limit()` - Context stays under 2500 chars
- **VALIDATE**: `cd backend && python -m pytest tests/test_semantic_memory_phase3.py -v`


---

### Phase 4: Frontend UI

#### Task 4.1: CREATE frontend/src/components/memory/SaveToMemoryButton.jsx

- **IMPLEMENT**: Manual save button for conversations
- **PATTERN**: Button component pattern from existing frontend components
- **IMPORTS**: `import React, { useState } from 'react'`, `import { saveConversationToMemory } from '../../api'`
- **KEY FEATURES**:
  - Appears in chat header when conversation has 5+ messages
  - Click triggers manual save to memory
  - Shows spinner during save
  - Shows "Saved" confirmation
  - Tooltip explains auto-save behavior
- **STYLING**: Use existing OhSee button styles
- **VALIDATE**: Button appears and triggers save API call

#### Task 4.2: CREATE frontend/src/components/memory/MemoryIndicator.jsx

- **IMPLEMENT**: Status badge showing memory indexing status
- **PATTERN**: Badge component pattern from existing UI
- **IMPORTS**: `import React, { useState, useEffect } from 'react'`, `import { getMemoryStatus } from '../../api'`
- **KEY FEATURES**:
  - Shows "🧠 In Memory" badge for indexed conversations
  - Hover popup shows indexed date, message count
  - Auto-refreshes every 30 seconds
  - Appears in conversation header
- **STYLING**: Use existing badge styles
- **VALIDATE**: Badge appears for indexed conversations

#### Task 4.3: CREATE frontend/src/components/memory/MemoryBrowser.jsx

- **IMPLEMENT**: Search and browse past conversations
- **PATTERN**: Modal/panel pattern from existing settings components
- **IMPORTS**: `import React, { useState, useEffect } from 'react'`, `import { searchMemory, removeFromMemory } from '../../api'`
- **KEY FEATURES**:
  - Semantic search input
  - Results list with relevance scores (e.g., "87% match")
  - Preview text from conversation
  - View and Remove actions per result
  - Keyboard shortcut (Ctrl+Shift+M)
  - Escape key closes browser
- **STYLING**: Use existing modal/panel styles
- **VALIDATE**: Search returns results, actions work

#### Task 4.4: CREATE frontend/src/components/memory/MemorySettings.jsx

- **IMPLEMENT**: Settings panel for memory configuration
- **PATTERN**: Settings panel from `SettingsPage.jsx`
- **IMPORTS**: `import React, { useState, useEffect } from 'react'`, `import { getMemoryStats, triggerAutoIndex, clearMemory } from '../../api'`
- **KEY FEATURES**:
  - Memory stats (indexed conversations, chunks, storage size)
  - Auto-save toggle
  - Retention period selector (30/90 days/forever)
  - Manual "Trigger Auto-Index" button
  - Clear all memory with confirmation modal
- **STYLING**: Use existing settings panel styles
- **VALIDATE**: All controls work, stats display correctly

#### Task 4.5: CREATE frontend/src/components/memory/MemoryStyles.css

- **IMPLEMENT**: Component-specific styles
- **PATTERN**: Existing component CSS files
- **STYLES**:
  - Memory button styles
  - Memory indicator badge styles
  - Memory browser modal styles
  - Memory settings panel styles
- **VALIDATE**: Components render correctly with styles

#### Task 4.6: CREATE frontend/src/components/memory/index.js

- **IMPLEMENT**: Component exports
- **PATTERN**: Standard index.js export pattern
- **EXPORTS**:
  ```javascript
  export { default as SaveToMemoryButton } from './SaveToMemoryButton';
  export { default as MemoryIndicator } from './MemoryIndicator';
  export { default as MemoryBrowser } from './MemoryBrowser';
  export { default as MemorySettings } from './MemorySettings';
  ```
- **VALIDATE**: Components can be imported from `components/memory`

#### Task 4.7: UPDATE frontend/src/api.js

- **ADD**: Memory API functions
- **PATTERN**: Existing API functions in `api.js`
- **NEW FUNCTIONS**:
  - `saveConversationToMemory(conversationId)` - POST to save endpoint
  - `getMemoryStatus(conversationId)` - GET status endpoint
  - `searchMemory(query, limit)` - GET search endpoint
  - `getMemoryStats()` - GET stats endpoint
  - `triggerAutoIndex()` - POST auto-index endpoint
  - `removeFromMemory(conversationId)` - DELETE conversation from memory
  - `clearMemory()` - DELETE all memory endpoint
- **VALIDATE**: All functions make correct API calls

#### Task 4.8: UPDATE frontend/src/App.jsx

- **ADD**: Integrate memory components
- **PATTERN**: Component integration from existing App.jsx
- **CHANGES**:
  - Import memory components
  - Add SaveToMemoryButton to chat header
  - Add MemoryIndicator to conversation header
  - Add MemoryBrowser with keyboard shortcut handler
  - Add "Memory" tab to settings sidebar
- **VALIDATE**: Components appear in UI, keyboard shortcuts work

---

### Phase 5: Optimization & Polish

#### Task 5.1: CREATE backend/services/conversation_summarization.py

- **IMPLEMENT**: Summarize long conversations before indexing
- **PATTERN**: Summarization logic from existing summary service
- **IMPORTS**: `from services.provider_service import chat_with_provider`, `from db.crud import get_conversation_by_id`
- **KEY FEATURES**:
  - `async def summarize_for_indexing(conv_id: str) -> str`
  - Summarize conversations with 20+ messages or 10k+ chars
  - Use heuristics: first query, message counts, last exchanges
  - Reduce token count by ~50-70%
  - Truncate very long individual messages (>2000 chars)
- **GOTCHA**: Use fast model (e.g., Haiku) for summarization to avoid delays
- **VALIDATE**: `python -c "from services.conversation_summarization import summarize_for_indexing; import asyncio; print(asyncio.run(summarize_for_indexing('test_id')))"`

#### Task 5.2: UPDATE backend/services/conversation_indexing.py

- **ADD**: Use summarization for long conversations
- **PATTERN**: Conditional logic from existing services
- **CHANGES**:
  - Import: `from services.conversation_summarization import summarize_for_indexing`
  - Before indexing, check conversation length
  - If 20+ messages or 10k+ chars, summarize first
  - Index summary instead of full conversation
  - Store original message count in metadata
- **VALIDATE**: Long conversations get summarized before indexing

#### Task 5.3: UPDATE backend/api/memory.py

- **ADD**: Cleanup and storage endpoints
- **PATTERN**: API endpoint pattern from existing memory.py
- **NEW ENDPOINTS**:
  - `POST /api/memory/cleanup` - Remove expired memories based on retention policy
  - `GET /api/memory/storage` - Get storage statistics (total size, conversation count)
  - `DELETE /api/memory/conversations/{id}` - Remove specific conversation from memory
  - `DELETE /api/memory/clear` - Clear all memory (with confirmation)
- **VALIDATE**: All endpoints work correctly

#### Task 5.4: UPDATE backend/services/memory_tasks.py

- **ADD**: Auto-cleanup task for expired memories
- **PATTERN**: Background task pattern from existing memory_tasks.py
- **CHANGES**:
  - Add cleanup check to background loop (runs daily)
  - Query for conversations older than retention period
  - Remove from vector memory
  - Update MongoDB indexing status
  - Log cleanup statistics
- **VALIDATE**: Cleanup task runs and removes expired memories

#### Task 5.5: UPDATE frontend/src/components/memory/MemorySettings.jsx

- **ADD**: Retention policy controls
- **PATTERN**: Settings control pattern from existing MemorySettings.jsx
- **CHANGES**:
  - Add retention period dropdown (30 days, 90 days, Forever)
  - Add "Run Cleanup Now" button
  - Show last cleanup timestamp
  - Show storage statistics
- **VALIDATE**: Retention controls work, cleanup triggers correctly

---

## TESTING STRATEGY

### Unit Tests

**Scope**: Test individual components in isolation

**Framework**: pytest (backend), Jest (frontend)

**Coverage Requirements**: 80%+ for new code

**Key Test Files**:
- `test_semantic_memory_phase1.py` - Embedder and vector storage
- `test_semantic_memory_phase2.py` - Conversation indexing
- `test_semantic_memory_phase3.py` - Chat integration

**Test Fixtures**:
- Mock Ollama embeddings for fast tests
- In-memory ChromaDB for test isolation
- Mock conversations with known content

### Integration Tests

**Scope**: Test end-to-end workflows

**Test Scenarios**:
1. **Auto-indexing workflow**: Create conversation → Wait 10 min → Verify indexed
2. **Manual save workflow**: Create conversation → Click save button → Verify indexed
3. **Semantic search workflow**: Index conversations → Search → Verify relevant results
4. **Chat integration workflow**: Index conversations → Start new chat → Verify memory context injected
5. **Cleanup workflow**: Set retention → Wait → Verify old memories removed

### Edge Cases

**Critical Edge Cases to Test**:
1. **Empty conversations** - Should not be indexed
2. **Very long conversations** (100+ messages) - Should be summarized
3. **Duplicate indexing** - Should not create duplicate entries
4. **Concurrent indexing** - Multiple conversations indexing simultaneously
5. **Ollama unavailable** - Should gracefully degrade
6. **ChromaDB unavailable** - Should log error and continue
7. **Invalid conversation IDs** - Should handle gracefully
8. **Search with no results** - Should return empty array
9. **Memory full** - Should handle storage limits
10. **Retention policy changes** - Should apply to existing memories

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

**Python Linting**:
```bash
cd backend
python -m flake8 services/embedder.py services/conversation_indexing.py services/semantic_memory_context.py db/vector_memory.py api/memory.py --max-line-length=120
```

**Python Type Checking** (if using mypy):
```bash
cd backend
python -m mypy services/embedder.py services/conversation_indexing.py --ignore-missing-imports
```

**JavaScript Linting**:
```bash
cd frontend
npm run lint
```

### Level 2: Unit Tests

**Backend Unit Tests**:
```bash
cd backend
python -m pytest tests/test_semantic_memory_phase1.py -v
python -m pytest tests/test_semantic_memory_phase2.py -v
python -m pytest tests/test_semantic_memory_phase3.py -v
```

**All Backend Tests**:
```bash
cd backend
python -m pytest tests/ -v --tb=short
```

**Frontend Unit Tests** (if applicable):
```bash
cd frontend
npm test
```

### Level 3: Integration Tests

**Backend Integration**:
```bash
cd backend
python -m pytest tests/test_semantic_memory_phase2.py::test_auto_index_workflow -v
python -m pytest tests/test_semantic_memory_phase3.py::test_chat_integration -v
```

**API Endpoint Tests**:
```bash
# Start backend first: uvicorn main:app --reload
curl http://localhost:8000/api/memory/stats
curl -X POST http://localhost:8000/api/memory/auto-index
curl http://localhost:8000/api/memory/conversations/test_id/status
```

### Level 4: Manual Validation

**Backend Manual Tests**:
1. Start backend: `cd backend && uvicorn main:app --reload`
2. Verify Ollama running: `ollama list` (should show nomic-embed-text)
3. Create test conversation via UI
4. Wait 10 minutes or trigger manual save
5. Check logs for indexing activity
6. Verify ChromaDB storage: `ls backend/.chroma/` (should have data)

**Frontend Manual Tests**:
1. Start frontend: `cd frontend && npm run dev`
2. Create conversation with 5+ messages
3. Verify SaveToMemoryButton appears
4. Click save, verify "Saved" confirmation
5. Open MemoryBrowser (Ctrl+Shift+M)
6. Search for conversation, verify results
7. Open Settings → Memory, verify stats display
8. Test retention controls

**End-to-End Manual Test**:
1. Create conversation about "Python pandas"
2. Save to memory (manual or wait for auto-index)
3. Create new conversation
4. Ask "How do I use pandas?"
5. Verify memory context injected (check system prompt in logs)
6. Verify relevant past conversation referenced in response

### Level 5: Performance Validation

**Embedding Performance**:
```bash
cd backend
python -c "
from services.embedder import embed_batch
import asyncio
import time

texts = ['test'] * 100
start = time.time()
asyncio.run(embed_batch(texts))
print(f'100 embeddings in {time.time() - start:.2f}s')
"
```

**Search Performance**:
```bash
cd backend
python -c "
from db.vector_memory import VectorMemory
import time

vm = VectorMemory()
start = time.time()
results = vm.search_similar([0.1] * 768, limit=10)
print(f'Search in {time.time() - start:.2f}s')
"
```

---

## ACCEPTANCE CRITERIA

- [ ] **Phase 1 Complete**: Embedder and vector storage working, tests passing
- [ ] **Phase 2 Complete**: Auto-indexing working, API endpoints functional
- [ ] **Phase 3 Complete**: Memory context injected into chat, tests passing
- [ ] **Phase 4 Complete**: Frontend UI functional, all components working
- [ ] **Phase 5 Complete**: Optimization and cleanup features working
- [ ] **All validation commands pass** with zero errors
- [ ] **Unit test coverage** meets 80%+ requirement
- [ ] **Integration tests** verify end-to-end workflows
- [ ] **Manual testing** confirms feature works as expected
- [ ] **Performance** meets requirements (embeddings <5s for 100 texts, search <100ms)
- [ ] **No regressions** in existing functionality (all existing tests still pass)
- [ ] **Documentation** updated (README mentions semantic memory)
- [ ] **Ollama dependency** documented (nomic-embed-text model required)

---

## COMPLETION CHECKLIST

- [ ] All Phase 1 tasks completed and validated
- [ ] All Phase 2 tasks completed and validated
- [ ] All Phase 3 tasks completed and validated
- [ ] All Phase 4 tasks completed and validated
- [ ] All Phase 5 tasks completed and validated
- [ ] All validation commands executed successfully
- [ ] Full test suite passes (unit + integration)
- [ ] No linting or type checking errors
- [ ] Manual testing confirms feature works end-to-end
- [ ] Performance benchmarks meet requirements
- [ ] Acceptance criteria all met
- [ ] Code reviewed for quality and maintainability
- [ ] README.md updated with semantic memory documentation
- [ ] Migration guide created (if needed for existing users)

---

## NOTES

### Design Decisions

**Why nomic-embed-text via Ollama?**
- Local embeddings (no external API costs)
- 768-dimensional embeddings (good balance of quality and performance)
- Runs on same infrastructure as LLMs
- No additional API keys or services required

**Why ChromaDB?**
- Lightweight, embeddable vector database
- Persistent storage with simple API
- Good performance for <100k documents
- No separate server required

**Why 512-token chunks with 50-token overlap?**
- Balances context preservation with search granularity
- Overlap ensures no information lost at chunk boundaries
- Standard practice for semantic search systems

**Why auto-index after 5+ messages and 10 min idle?**
- 5 messages ensures conversation has substance
- 10 min idle prevents indexing mid-conversation
- Non-blocking ensures no UX impact

**Why score threshold of 0.6?**
- Filters out low-relevance results
- Prevents context pollution with irrelevant conversations
- Can be tuned based on user feedback

### Trade-offs

**Summarization vs Full Text**:
- **Pro**: Reduces token count, faster search
- **Con**: May lose some detail
- **Decision**: Summarize only conversations >20 messages

**Local vs Cloud Embeddings**:
- **Pro (Local)**: No API costs, privacy, no rate limits
- **Con (Local)**: Requires Ollama running, slower than cloud
- **Decision**: Local for privacy and cost, acceptable performance

**Auto-index vs Manual Only**:
- **Pro (Auto)**: Zero user effort, always up-to-date
- **Con (Auto)**: Background resource usage
- **Decision**: Auto-index with manual override option

### Known Limitations

1. **Ollama Dependency**: Requires Ollama running with nomic-embed-text model
2. **Storage Growth**: Vector DB grows with conversation count (mitigated by retention policies)
3. **Search Quality**: Depends on embedding model quality (nomic-embed-text is good but not SOTA)
4. **Performance**: Embedding generation adds latency (mitigated by async/background processing)
5. **Context Window**: Still limited by LLM context window (semantic search helps prioritize)

### Future Enhancements

1. **Hybrid Search**: Combine semantic search with keyword search for better results
2. **Conversation Clustering**: Group similar conversations for better organization
3. **Temporal Weighting**: Prioritize recent conversations in search results
4. **User Feedback**: Allow users to mark conversations as important/unimportant
5. **Multi-modal**: Support images, code snippets, etc. in memory
6. **Export/Import**: Allow users to export/import their memory database
7. **Shared Memory**: Team workspaces with shared conversation memory
8. **Advanced Analytics**: Insights into conversation patterns, topics, etc.

### Migration Notes

**For Existing Users**:
- Existing pinned conversations remain functional
- Semantic memory is additive (doesn't replace pinning)
- First-time indexing may take time for large conversation histories
- Recommend running manual "Trigger Auto-Index" after installation

**Database Changes**:
- Adds `indexed_to_memory` field to conversations collection
- Adds `indexed_at` timestamp field
- Creates new ChromaDB collection for vector storage
- No breaking changes to existing schema

### Troubleshooting

**Ollama Not Running**:
- Error: "Connection refused" when embedding
- Solution: Start Ollama (`ollama serve`) and pull model (`ollama pull nomic-embed-text`)

**ChromaDB Errors**:
- Error: "Collection not found"
- Solution: Delete `.chroma/` directory and restart backend

**Slow Indexing**:
- Issue: Auto-indexing takes too long
- Solution: Reduce batch size in conversation_indexing.py or increase check interval

**Memory Not Appearing in Chat**:
- Issue: Semantic memory not injected into context
- Solution: Check logs for errors, verify conversations are indexed, check score threshold

**Storage Growing Too Fast**:
- Issue: ChromaDB storage size growing rapidly
- Solution: Reduce retention period, enable auto-cleanup, or increase cleanup frequency

