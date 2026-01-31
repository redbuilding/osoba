# Feature: Replace Ollama Library with LiteLLM

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Replace the direct Ollama library integration with LiteLLM to provide a unified interface for multiple LLM providers while maintaining backward compatibility. This migration will enable future support for cloud providers (OpenAI, Anthropic, etc.) while keeping existing Ollama functionality intact through the `ollama/` model prefix.

## User Story

As a developer maintaining the MCP chat application
I want to replace the direct Ollama integration with LiteLLM
So that I can support multiple LLM providers through a unified interface while maintaining existing functionality

## Problem Statement

The current implementation directly uses the Ollama library, which limits the application to only local Ollama models. Users cannot access cloud-based LLMs or switch between providers without significant code changes. The tight coupling to Ollama makes it difficult to add support for other providers.

## Solution Statement

Replace the Ollama library with LiteLLM, which provides an OpenAI-compatible interface for 100+ LLM providers including Ollama. Use the `ollama/` prefix for existing models to maintain backward compatibility while enabling future multi-provider support.

## Feature Metadata

**Feature Type**: Refactor
**Estimated Complexity**: Medium
**Primary Systems Affected**: LLM Service Layer, Chat Service, Task System, API Layer
**Dependencies**: litellm library

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `backend/services/ollama_service.py` (entire file) - Why: Core service to be replaced with LiteLLM implementation
- `backend/services/chat_service.py` (lines 17, 142, 213) - Why: Primary consumer of Ollama service functions
- `backend/services/task_runner.py` (lines 27, 149-152, 306) - Why: Uses Ollama for task execution and verification
- `backend/services/task_planner.py` (lines 6, 78, 83) - Why: Uses Ollama for plan generation
- `backend/api/status.py` (lines 3, 7, 14-18, 44-47) - Why: Exposes Ollama model listing and health checks
- `backend/core/models.py` (lines 27, 33, 41, 78, 104) - Why: Contains ollama_model_name fields to be updated
- `backend/core/config.py` (lines 39-40) - Why: Ollama-specific configuration constants
- `backend/tests/conftest.py` (lines 82-86) - Why: Mock Ollama service for testing
- `backend/test_server_python.py` (lines 133, 138, 149, 172, 176) - Why: Test references to ollama_model_name

### New Files to Create

- None (refactoring existing files only)

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [LiteLLM Async Completion Documentation](https://docs.litellm.ai/docs/completion/stream)
  - Specific section: acompletion() and async streaming
  - Why: Required for implementing async LLM calls
- [LiteLLM Ollama Provider Documentation](https://docs.litellm.ai/docs/providers/ollama)
  - Specific section: Model naming with ollama/ prefix and api_base configuration
  - Why: Shows proper Ollama integration through LiteLLM
- [LiteLLM Error Handling Documentation](https://docs.litellm.ai/docs/exception_mapping)
  - Specific section: OpenAI-compatible exception mapping
  - Why: Required for proper error handling migration

### Patterns to Follow

**Async Function Pattern:**
```python
# Current pattern in ollama_service.py
async def chat_with_ollama(messages: List[Dict[str, str]], model_name: str, repeat_penalty: float = DEFAULT_REPEAT_PENALTY) -> Optional[str]:
    response = await asyncio.to_thread(ollama.chat, model=model_name, messages=valid_messages, options={"repeat_penalty": repeat_penalty})

# New LiteLLM pattern
async def chat_with_llm(messages: List[Dict[str, str]], model_name: str, repeat_penalty: float = DEFAULT_REPEAT_PENALTY) -> Optional[str]:
    response = await litellm.acompletion(model=f"ollama/{model_name}", messages=valid_messages, api_base="http://localhost:11434")
```

**Error Handling Pattern:**
```python
# Current pattern
except ollama.ResponseError as e:
    logger.error(f"Ollama API ResponseError: {e.status_code} - {e.error}")
    raise HTTPException(status_code=e.status_code or 500, detail=f"Ollama API error: {e.error}")

# New LiteLLM pattern (uses OpenAI exceptions)
except BadRequestError as e:
    logger.error(f"LLM API BadRequestError: {e.status_code} - {e}")
    raise HTTPException(status_code=e.status_code or 400, detail=f"LLM API error: {e}")
```

**Streaming Pattern:**
```python
# Current pattern
for chunk in ollama.chat(model=model_name, messages=messages, stream=True):
    if chunk and "message" in chunk and "content" in chunk["message"]:
        token = chunk["message"]["content"]
        payload = json.dumps({"type": "token", "content": token})
        yield f"data: {payload}\n\n"

# New LiteLLM pattern
response = await litellm.acompletion(model=f"ollama/{model_name}", messages=messages, stream=True, api_base="http://localhost:11434")
async for chunk in response:
    if chunk.choices[0].delta.content:
        token = chunk.choices[0].delta.content
        payload = json.dumps({"type": "token", "content": token})
        yield f"data: {payload}\n\n"
```

**Model Name Handling:**
```python
# Current: Direct model name
model_name = "llama3.1"

# New: Prefix with ollama/
model_name = f"ollama/{model_name}"
```

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation

Install LiteLLM dependency and update core service layer to use LiteLLM instead of direct Ollama library calls.

**Tasks:**
- Install litellm package
- Replace ollama imports with litellm imports
- Update core service functions to use acompletion()
- Maintain existing function signatures for backward compatibility

### Phase 2: Core Implementation

Replace all Ollama-specific function calls with LiteLLM equivalents while preserving existing behavior and error handling patterns.

**Tasks:**
- Update chat_with_ollama() to use litellm.acompletion()
- Update stream_chat_with_ollama() to use async streaming
- Update model listing functions to work with LiteLLM
- Update error handling to use OpenAI-compatible exceptions

### Phase 3: Integration

Update all consumers of the Ollama service to work with the new LiteLLM-based implementation.

**Tasks:**
- Update chat service integration
- Update task system integration
- Update API endpoints
- Update configuration and model management

### Phase 4: Testing & Validation

Ensure all existing functionality works with the new LiteLLM implementation and update tests accordingly.

**Tasks:**
- Update test mocks to use LiteLLM
- Validate streaming functionality
- Test error handling scenarios
- Verify model selection and management

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### INSTALL litellm dependency

- **IMPLEMENT**: Add litellm to requirements.txt and install
- **PATTERN**: Follow existing dependency management in requirements.txt
- **IMPORTS**: `pip install litellm`
- **GOTCHA**: Ensure version compatibility with existing async libraries
- **VALIDATE**: `pip list | grep litellm`

### UPDATE backend/services/ollama_service.py

- **IMPLEMENT**: Replace ollama imports with litellm and OpenAI exceptions
- **PATTERN**: Import pattern from existing service files
- **IMPORTS**: 
  ```python
  import litellm
  from openai import APITimeoutError, BadRequestError, AuthenticationError, NotFoundError, RateLimitError, APIConnectionError, InternalServerError
  ```
- **GOTCHA**: Remove asyncio.to_thread wrapper as litellm.acompletion is native async
- **VALIDATE**: `python -c "import backend.services.ollama_service; print('Import successful')"`

### REFACTOR chat_with_ollama function

- **IMPLEMENT**: Replace ollama.chat with litellm.acompletion using ollama/ prefix
- **PATTERN**: Async function pattern from services/chat_service.py:213
- **IMPORTS**: Use existing message validation and logging patterns
- **GOTCHA**: Add api_base="http://localhost:11434" for Ollama connection
- **VALIDATE**: `python -c "import asyncio; from backend.services.ollama_service import chat_with_ollama; print('Function updated')"`

### REFACTOR stream_chat_with_ollama function

- **IMPLEMENT**: Replace ollama streaming with litellm async streaming
- **PATTERN**: Async generator pattern from existing streaming implementation
- **IMPORTS**: Maintain existing SSE format and error handling
- **GOTCHA**: Use async for chunk in response instead of sync iteration
- **VALIDATE**: `python -c "import asyncio; from backend.services.ollama_service import stream_chat_with_ollama; print('Streaming updated')"`

### REFACTOR list_ollama_models_info function

- **IMPLEMENT**: Update to use LiteLLM model listing (may need to call Ollama API directly for model info)
- **PATTERN**: HTTP client pattern from existing MCP service calls
- **IMPORTS**: Use existing error handling and response formatting
- **GOTCHA**: LiteLLM may not provide detailed model info, might need direct Ollama API call
- **VALIDATE**: `python -c "import asyncio; from backend.services.ollama_service import list_ollama_models_info; print('Model listing updated')"`

### UPDATE error handling throughout ollama_service.py

- **IMPLEMENT**: Replace ollama.ResponseError and ollama.RequestError with OpenAI exceptions
- **PATTERN**: Error handling pattern from services/chat_service.py error handling
- **IMPORTS**: Use OpenAI exception hierarchy (BadRequestError, APIConnectionError, etc.)
- **GOTCHA**: Map Ollama-specific errors to appropriate OpenAI exception types
- **VALIDATE**: `python -c "from backend.services.ollama_service import *; print('Error handling updated')"`

### UPDATE backend/core/models.py

- **IMPLEMENT**: Rename ollama_model_name fields to model_name for provider neutrality
- **PATTERN**: Existing Pydantic model patterns in same file
- **IMPORTS**: No new imports needed
- **GOTCHA**: Update all references consistently across ChatPayload, TaskCreatePayload, etc.
- **VALIDATE**: `python -c "from backend.core.models import ChatPayload; print(ChatPayload.__fields__.keys())"`

### UPDATE backend/core/config.py

- **IMPLEMENT**: Rename DEFAULT_OLLAMA_MODEL to DEFAULT_MODEL and update related constants
- **PATTERN**: Existing environment variable pattern in same file
- **IMPORTS**: No new imports needed
- **GOTCHA**: Maintain backward compatibility by checking both old and new env var names
- **VALIDATE**: `python -c "from backend.core.config import DEFAULT_MODEL; print(f'Default model: {DEFAULT_MODEL}')"`

### UPDATE backend/services/chat_service.py

- **IMPLEMENT**: Update imports and function calls to use new service names
- **PATTERN**: Existing service import pattern at top of file
- **IMPORTS**: Update from ollama_service import to use new function names
- **GOTCHA**: Update model_name handling to add ollama/ prefix when calling LLM service
- **VALIDATE**: `python -c "from backend.services.chat_service import ChatProcessor; print('Chat service updated')"`

### UPDATE backend/services/task_runner.py

- **IMPLEMENT**: Update Ollama service imports and function calls
- **PATTERN**: Existing service integration pattern in same file
- **IMPORTS**: Update import statements and function references
- **GOTCHA**: Ensure model name prefixing is handled correctly in task context
- **VALIDATE**: `python -c "from backend.services.task_runner import RunnerState; print('Task runner updated')"`

### UPDATE backend/services/task_planner.py

- **IMPLEMENT**: Update Ollama service imports and function calls
- **PATTERN**: Existing service integration pattern in same file
- **IMPORTS**: Update import statements and function references
- **GOTCHA**: Maintain existing prompt engineering and response parsing
- **VALIDATE**: `python -c "from backend.services.task_planner import plan_task; print('Task planner updated')"`

### UPDATE backend/api/status.py

- **IMPLEMENT**: Update Ollama-specific endpoints to work with LiteLLM
- **PATTERN**: Existing API endpoint pattern in same file
- **IMPORTS**: Update service imports and function calls
- **GOTCHA**: Endpoint names may need to change from ollama-specific to generic
- **VALIDATE**: `python -c "from backend.api.status import get_status; print('Status API updated')"`

### UPDATE backend/tests/conftest.py

- **IMPLEMENT**: Update mock Ollama service to mock LiteLLM functions
- **PATTERN**: Existing mock pattern in same file
- **IMPORTS**: Update mock function names and return values
- **GOTCHA**: Ensure mock responses match LiteLLM response format
- **VALIDATE**: `python -c "from backend.tests.conftest import mock_ollama_service; print('Test mocks updated')"`

### UPDATE test files with ollama_model_name references

- **IMPLEMENT**: Update test files to use new model_name field
- **PATTERN**: Existing test data patterns in test files
- **IMPORTS**: No new imports needed
- **GOTCHA**: Update both field names and test assertions
- **VALIDATE**: `python -m pytest backend/tests/ -k "test_chat" --collect-only`

### ADD environment variable for Ollama API base

- **IMPLEMENT**: Add OLLAMA_API_BASE environment variable with default
- **PATTERN**: Existing environment variable pattern in core/config.py
- **IMPORTS**: Use os.getenv pattern from existing config
- **GOTCHA**: Default to http://localhost:11434 for local Ollama instances
- **VALIDATE**: `python -c "from backend.core.config import *; print('Config updated')"`

---

## TESTING STRATEGY

### Unit Tests

Update existing unit tests to work with LiteLLM mocks instead of Ollama mocks. Focus on:
- Service function behavior with new LiteLLM calls
- Error handling with OpenAI exception types
- Model name prefixing logic
- Streaming response format consistency

### Integration Tests

Test the complete flow from API endpoints through to LiteLLM calls:
- Chat endpoint streaming and non-streaming
- Task execution with LLM calls
- Model listing and selection
- Error propagation through the stack

### Edge Cases

- Network connectivity issues to Ollama
- Invalid model names with ollama/ prefix
- Streaming interruption and recovery
- Large response handling
- Concurrent request handling

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
cd backend && python -m py_compile services/ollama_service.py
cd backend && python -m py_compile services/chat_service.py
cd backend && python -m py_compile services/task_runner.py
cd backend && python -m py_compile services/task_planner.py
cd backend && python -m py_compile api/status.py
cd backend && python -m py_compile core/models.py
cd backend && python -m py_compile core/config.py
```

### Level 2: Import Validation

```bash
cd backend && python -c "from services.ollama_service import *; print('Ollama service imports OK')"
cd backend && python -c "from services.chat_service import ChatProcessor; print('Chat service imports OK')"
cd backend && python -c "from services.task_runner import RunnerState; print('Task runner imports OK')"
cd backend && python -c "from services.task_planner import plan_task; print('Task planner imports OK')"
cd backend && python -c "from api.status import get_status; print('Status API imports OK')"
cd backend && python -c "from core.models import ChatPayload; print('Models imports OK')"
cd backend && python -c "from core.config import DEFAULT_MODEL; print('Config imports OK')"
```

### Level 3: Unit Tests

```bash
cd backend && python -m pytest tests/test_chat_service.py -v
cd backend && python -m pytest tests/test_streaming.py -v
cd backend && python -m pytest tests/test_tasks.py -v
```

### Level 4: Integration Tests

```bash
cd backend && python -c "
import asyncio
from services.ollama_service import chat_with_ollama, stream_chat_with_ollama
async def test():
    # Test basic chat (will fail if Ollama not running, but should not crash)
    try:
        result = await chat_with_ollama([{'role': 'user', 'content': 'test'}], 'llama3.1')
        print('Chat function callable')
    except Exception as e:
        print(f'Chat function error (expected if Ollama not running): {type(e).__name__}')
    
    # Test streaming (will fail if Ollama not running, but should not crash)
    try:
        async for chunk in stream_chat_with_ollama([{'role': 'user', 'content': 'test'}], 'llama3.1'):
            print('Streaming function callable')
            break
    except Exception as e:
        print(f'Streaming function error (expected if Ollama not running): {type(e).__name__}')

asyncio.run(test())
"
```

### Level 5: API Endpoint Validation

```bash
cd backend && python -c "
from fastapi.testclient import TestClient
from main import app
client = TestClient(app)
response = client.get('/api/status')
print(f'Status endpoint: {response.status_code}')
"
```

---

## ACCEPTANCE CRITERIA

- [ ] LiteLLM library successfully replaces direct Ollama library usage
- [ ] All existing Ollama functionality works through LiteLLM with ollama/ prefix
- [ ] Streaming chat responses maintain existing SSE format
- [ ] Error handling uses OpenAI-compatible exceptions
- [ ] Model listing and selection continues to work
- [ ] All validation commands pass with zero errors
- [ ] Unit test coverage maintained at current levels
- [ ] Integration tests verify end-to-end LiteLLM functionality
- [ ] No regressions in chat, task, or API functionality
- [ ] Configuration supports both old and new environment variable names
- [ ] Test mocks updated to reflect LiteLLM usage

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully
- [ ] Full test suite passes (unit + integration)
- [ ] No linting or type checking errors
- [ ] Manual testing confirms LiteLLM integration works
- [ ] Acceptance criteria all met
- [ ] Code reviewed for quality and maintainability
- [ ] Backward compatibility maintained for existing model selection

---

## NOTES

**Design Decisions:**
- Maintain existing function signatures to minimize breaking changes
- Use ollama/ prefix for all model names to ensure proper LiteLLM routing
- Keep existing error handling patterns but map to OpenAI exception hierarchy
- Preserve SSE streaming format for frontend compatibility

**Trade-offs:**
- Slightly more complex model name handling (ollama/ prefix) for future multi-provider support
- Dependency on LiteLLM library adds abstraction layer but enables provider flexibility
- OpenAI exception hierarchy may require mapping some Ollama-specific errors

**Future Considerations:**
- This refactor enables easy addition of other providers (OpenAI, Anthropic, etc.)
- Model selection UI can be enhanced to show provider + model combinations
- Configuration can be extended to support multiple provider API keys
