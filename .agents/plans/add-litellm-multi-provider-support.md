# Feature: Add LiteLLM Multi-Provider Support with Secure API Key Management

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Transform the current Ollama-only LiteLLM integration into a comprehensive multi-provider system supporting Ollama, OpenRouter, OpenAI, Anthropic, Google, Groq, and Sambanova. Add secure API key management through a new settings interface, enabling users to configure and switch between different LLM providers seamlessly while maintaining conversation-scoped model selection.

## User Story

As a user of the MCP chat application
I want to configure and use multiple LLM providers (OpenAI, Anthropic, etc.) beyond just local Ollama models
So that I can access more powerful cloud-based models, compare responses across providers, and have fallback options when one provider is unavailable

## Problem Statement

The current implementation only supports local Ollama models through LiteLLM, limiting users to locally available models. Users cannot access cloud-based LLMs like GPT-4, Claude, or Gemini without significant code changes. There's no secure way to configure API keys for different providers, and the model selection is hardcoded to the `ollama/` prefix format.

## Solution Statement

Extend the existing LiteLLM integration to support multiple providers by adding a provider configuration system with secure API key storage, updating the model selection UI to show provider-grouped models, and implementing a settings interface for API key management. Maintain backward compatibility with existing Ollama functionality while enabling seamless provider switching.

## Feature Metadata

**Feature Type**: Enhancement
**Estimated Complexity**: High
**Primary Systems Affected**: LLM Service Layer, Configuration Management, Frontend UI, API Layer, Database Schema
**Dependencies**: litellm (already installed), secure storage for API keys

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `backend/services/ollama_service.py` (entire file) - Why: Core LiteLLM service to be extended for multi-provider support
- `backend/core/config.py` (lines 39-40) - Why: Configuration patterns and environment variable handling
- `backend/core/models.py` (lines 27, 33, 41, 78, 104) - Why: Data models for chat payloads and responses
- `backend/api/status.py` (lines 3, 7, 14-18, 44-47) - Why: Model listing endpoint patterns to extend
- `backend/api/chat.py` (entire file) - Why: Chat endpoints that use model selection
- `frontend/src/App.jsx` (lines 580-610) - Why: Current model selection UI patterns
- `frontend/src/services/api.js` (lines 1-50) - Why: API client patterns for new endpoints
- `backend/tests/conftest.py` (lines 82-86) - Why: Testing patterns for service mocking
- `backend/db/mongodb.py` (entire file) - Why: Database connection patterns for settings storage

### New Files to Create

- `backend/services/provider_service.py` - Multi-provider management and API key handling
- `backend/core/providers.py` - Provider configurations and model mappings
- `backend/api/providers.py` - Provider and settings API endpoints
- `backend/db/settings_crud.py` - Database operations for user settings
- `frontend/src/components/SettingsModal.jsx` - Settings UI for API key configuration
- `frontend/src/components/ProviderModelSelector.jsx` - Enhanced model selector with provider grouping
- `tests/test_provider_service.py` - Unit tests for provider service

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [LiteLLM Multi-Provider Setup](https://docs.litellm.ai/docs/providers)
  - Specific section: Provider-specific configuration and model naming
  - Why: Required for implementing correct provider configurations
- [LiteLLM OpenAI Provider](https://docs.litellm.ai/docs/providers/openai)
  - Specific section: API key setup and model formats
  - Why: OpenAI integration patterns
- [LiteLLM Anthropic Provider](https://docs.litellm.ai/docs/providers/anthropic)
  - Specific section: Claude model configuration and max_tokens requirement
  - Why: Anthropic-specific implementation details
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
  - Specific section: API key handling and secure storage
  - Why: Secure API key management patterns

### Patterns to Follow

**Service Layer Pattern** (from `ollama_service.py`):
```python
async def chat_with_provider(messages: List[Dict[str, str]], model_name: str, 
                           provider_config: Dict[str, Any]) -> Optional[str]:
    try:
        response = await litellm.acompletion(
            model=model_name,  # Already includes provider prefix
            messages=messages,
            **provider_config
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"[LLM] Error with model '{model_name}': {e}")
        return None
```

**Configuration Pattern** (from `config.py`):
```python
# Environment-based with defaults
PROVIDER_CONFIGS = {
    'openai': {
        'api_key_env': 'OPENAI_API_KEY',
        'default_model': 'gpt-3.5-turbo'
    }
}
```

**API Endpoint Pattern** (from `status.py`):
```python
@router.get("/providers")
async def list_providers():
    try:
        providers = await provider_service.get_available_providers()
        return {"providers": providers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Frontend State Pattern** (from `App.jsx`):
```javascript
const [selectedProvider, setSelectedProvider] = useState('ollama');
const [availableModels, setAvailableModels] = useState({});
const [providerSettings, setProviderSettings] = useState({});
```

**Error Handling Pattern** (from `ollama_service.py`):
```python
except APIConnectionError as e:
    logger.error(f"Provider API ConnectionError: {e}")
    raise HTTPException(status_code=503, detail=f"Could not connect to {provider}")
```

---

## IMPLEMENTATION PLAN

### Phase 1: Backend Foundation

Establish the multi-provider architecture and secure configuration management.

**Tasks:**
- Create provider configuration system with secure API key handling
- Extend LiteLLM service to support multiple providers
- Add database schema for user settings storage
- Implement provider validation and health checking

### Phase 2: API Layer Extension

Extend existing APIs and create new endpoints for provider management.

**Tasks:**
- Update model listing to include provider information
- Create provider configuration endpoints
- Add settings management API
- Extend chat endpoints for provider-specific parameters

### Phase 3: Frontend Integration

Update the UI to support provider selection and settings management.

**Tasks:**
- Create settings modal for API key configuration
- Update model selector to group by provider
- Add provider status indicators
- Implement secure API key input handling

### Phase 4: Testing & Validation

Comprehensive testing across all providers and edge cases.

**Tasks:**
- Unit tests for provider service
- Integration tests for multi-provider chat
- Frontend component tests
- End-to-end provider switching tests

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### CREATE backend/core/providers.py

- **IMPLEMENT**: Provider configuration constants and model mappings
- **PATTERN**: Configuration pattern from `config.py` with environment variables
- **IMPORTS**: `os`, `typing.Dict`, `typing.List`, `typing.Optional`
- **GOTCHA**: Anthropic requires `max_tokens` parameter, Google has different auth methods
- **VALIDATE**: `python -c "from backend.core.providers import PROVIDER_CONFIGS; print(len(PROVIDER_CONFIGS))"`

### CREATE backend/db/settings_crud.py

- **IMPLEMENT**: Database operations for user settings and API keys
- **PATTERN**: CRUD pattern from `crud.py` with MongoDB operations
- **IMPORTS**: `pymongo`, `bson.ObjectId`, `typing.Dict`, `typing.Optional`
- **GOTCHA**: API keys must be encrypted at rest, use environment-based encryption key
- **VALIDATE**: `python -c "from backend.db.settings_crud import get_user_settings; print('Settings CRUD loaded')"`

### UPDATE backend/db/mongodb.py

- **IMPLEMENT**: Add settings collection getter function
- **PATTERN**: Collection getter pattern from existing functions
- **IMPORTS**: No new imports needed
- **GOTCHA**: Follow existing naming convention `get_*_collection`
- **VALIDATE**: `python -c "from backend.db.mongodb import get_settings_collection; print('Settings collection available')"`

### CREATE backend/services/provider_service.py

- **IMPLEMENT**: Multi-provider LiteLLM service with secure API key management
- **PATTERN**: Service pattern from `ollama_service.py` with async functions
- **IMPORTS**: `litellm`, `asyncio`, `os`, `typing`, `cryptography.fernet`, `backend.core.providers`
- **GOTCHA**: Each provider has different model naming conventions and required parameters
- **VALIDATE**: `python -c "from backend.services.provider_service import get_available_providers; print('Provider service loaded')"`

### UPDATE backend/services/ollama_service.py

- **IMPLEMENT**: Rename to `llm_service.py` and refactor to use provider_service
- **PATTERN**: Keep existing function signatures for backward compatibility
- **IMPORTS**: Update imports to use `provider_service`
- **GOTCHA**: Maintain existing `ollama/` prefix behavior for backward compatibility
- **VALIDATE**: `python -c "from backend.services.llm_service import chat_with_ollama; print('LLM service updated')"`

### UPDATE backend/core/models.py

- **IMPLEMENT**: Add provider-related fields to ChatPayload and ChatResponse
- **PATTERN**: Existing Pydantic model patterns with Optional fields
- **IMPORTS**: No new imports needed
- **GOTCHA**: Keep `model_name` field for backward compatibility, add `provider` field
- **VALIDATE**: `python -c "from backend.core.models import ChatPayload; print(ChatPayload.__fields__.keys())"`

### CREATE backend/api/providers.py

- **IMPLEMENT**: API endpoints for provider management and settings
- **PATTERN**: Router pattern from `status.py` with error handling
- **IMPORTS**: `fastapi`, `backend.services.provider_service`, `backend.db.settings_crud`
- **GOTCHA**: API keys should never be returned in responses, only validation status
- **VALIDATE**: `python -c "from backend.api.providers import router; print('Provider API loaded')"`

### UPDATE backend/api/status.py

- **IMPLEMENT**: Update model listing to include provider information
- **PATTERN**: Existing endpoint pattern with enhanced response format
- **IMPORTS**: Add `backend.services.provider_service`
- **GOTCHA**: Maintain backward compatibility with existing `/api/ollama-models` endpoint
- **VALIDATE**: `curl http://localhost:8000/api/providers/models | jq .`

### UPDATE backend/main.py

- **IMPLEMENT**: Register new provider router
- **PATTERN**: Existing router registration pattern
- **IMPORTS**: Add `backend.api.providers`
- **GOTCHA**: Import order matters for proper initialization
- **VALIDATE**: `python -c "from backend.main import app; print([route.path for route in app.routes])"`

### UPDATE backend/services/chat_service.py

- **IMPLEMENT**: Update to use new llm_service with provider support
- **PATTERN**: Existing service integration pattern
- **IMPORTS**: Update import from `ollama_service` to `llm_service`
- **GOTCHA**: Model resolution logic needs to handle provider prefixes
- **VALIDATE**: `python -c "from backend.services.chat_service import ChatProcessor; print('Chat service updated')"`

### CREATE frontend/src/components/SettingsModal.jsx

- **IMPLEMENT**: Modal component for API key configuration
- **PATTERN**: Modal pattern from existing components with form handling
- **IMPORTS**: `react`, `lucide-react` for icons
- **GOTCHA**: Never store API keys in localStorage, always mask input values
- **VALIDATE**: `npm run build` (should compile without errors)

### CREATE frontend/src/components/ProviderModelSelector.jsx

- **IMPLEMENT**: Enhanced model selector with provider grouping
- **PATTERN**: Select component pattern from `App.jsx` with grouped options
- **IMPORTS**: `react`, `lucide-react`
- **GOTCHA**: Handle provider availability and model loading states
- **VALIDATE**: `npm run build` (should compile without errors)

### UPDATE frontend/src/services/api.js

- **IMPLEMENT**: Add API functions for provider management
- **PATTERN**: Existing API function patterns with axios
- **IMPORTS**: No new imports needed
- **GOTCHA**: Handle API key validation responses properly
- **VALIDATE**: `npm run build` (should compile without errors)

### UPDATE frontend/src/App.jsx

- **IMPLEMENT**: Integrate new provider selector and settings modal
- **PATTERN**: Existing state management and component integration patterns
- **IMPORTS**: Add new components
- **GOTCHA**: Maintain existing model selection behavior for backward compatibility
- **VALIDATE**: `npm run dev` (should start without errors)

### CREATE backend/tests/test_provider_service.py

- **IMPLEMENT**: Unit tests for provider service functionality
- **PATTERN**: Test class pattern from `test_chat_service.py` with async tests
- **IMPORTS**: `pytest`, `unittest.mock`, `backend.services.provider_service`
- **GOTCHA**: Mock external API calls to avoid hitting real provider APIs
- **VALIDATE**: `python -m pytest backend/tests/test_provider_service.py -v`

### UPDATE backend/tests/conftest.py

- **IMPLEMENT**: Add mock fixtures for provider service
- **PATTERN**: Existing mock fixture patterns
- **IMPORTS**: Add provider service mocks
- **GOTCHA**: Mock both successful and error responses for comprehensive testing
- **VALIDATE**: `python -m pytest backend/tests/ -k "provider" -v`

---

## TESTING STRATEGY

### Unit Tests

**Provider Service Tests** (`test_provider_service.py`):
- Provider configuration validation
- API key encryption/decryption
- Model listing for each provider
- Error handling for invalid API keys
- Provider health checking

**Settings CRUD Tests** (`test_settings_crud.py`):
- User settings creation and retrieval
- API key secure storage
- Settings validation and sanitization

### Integration Tests

**Multi-Provider Chat Tests**:
- Chat completion with different providers
- Streaming responses across providers
- Provider fallback mechanisms
- Model parameter handling per provider

**API Endpoint Tests**:
- Provider listing endpoint
- Settings management endpoints
- Model listing with provider information
- Error responses for invalid configurations

### Frontend Component Tests

**Settings Modal Tests**:
- API key input and validation
- Provider configuration saving
- Error message display
- Modal open/close behavior

**Provider Model Selector Tests**:
- Provider grouping display
- Model selection across providers
- Loading states and error handling

### Edge Cases

- Invalid API keys for each provider
- Network timeouts and connection errors
- Provider service unavailability
- Malformed provider responses
- API key rotation scenarios
- Mixed provider conversations

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
# Python syntax and imports
python -m py_compile backend/services/provider_service.py
python -m py_compile backend/core/providers.py
python -m py_compile backend/api/providers.py

# Frontend syntax
cd frontend && npm run build
```

### Level 2: Unit Tests

```bash
# Provider service tests
python -m pytest backend/tests/test_provider_service.py -v

# Settings CRUD tests
python -m pytest backend/tests/test_settings_crud.py -v

# All backend tests
python -m pytest backend/tests/ -v
```

### Level 3: Integration Tests

```bash
# Start backend server
cd backend && uvicorn main:app --reload --port 8000 &

# Test provider endpoints
curl -X GET http://localhost:8000/api/providers
curl -X GET http://localhost:8000/api/providers/models
curl -X POST http://localhost:8000/api/providers/settings -H "Content-Type: application/json" -d '{"provider": "openai", "api_key": "test-key"}'

# Test chat with provider
curl -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{"messages": [{"role": "user", "content": "Hello"}], "model_name": "openai/gpt-3.5-turbo"}'
```

### Level 4: Manual Validation

```bash
# Start full application
cd backend && uvicorn main:app --reload --port 8000 &
cd frontend && npm run dev &

# Manual testing checklist:
# 1. Open settings modal and configure API keys
# 2. Select different providers in model selector
# 3. Send chat messages with different providers
# 4. Verify provider status indicators
# 5. Test error handling with invalid API keys
# 6. Verify backward compatibility with existing Ollama models
```

### Level 5: Additional Validation (Optional)

```bash
# Security validation
python -c "from backend.services.provider_service import encrypt_api_key, decrypt_api_key; key='test'; encrypted=encrypt_api_key(key); assert decrypt_api_key(encrypted)==key; print('Encryption working')"

# Performance validation
python -c "import time; from backend.services.provider_service import get_available_providers; start=time.time(); providers=get_available_providers(); print(f'Provider loading: {time.time()-start:.2f}s')"
```

---

## ACCEPTANCE CRITERIA

- [ ] Users can configure API keys for OpenRouter, OpenAI, Anthropic, Google, Groq, and Sambanova
- [ ] Model selector groups models by provider with clear visual distinction
- [ ] API keys are stored securely with encryption at rest
- [ ] Chat functionality works with all configured providers
- [ ] Streaming responses work across all providers
- [ ] Provider status indicators show availability and configuration status
- [ ] Settings modal provides clear feedback for API key validation
- [ ] Backward compatibility maintained for existing Ollama functionality
- [ ] Error handling gracefully manages provider failures and invalid keys
- [ ] All validation commands pass with zero errors
- [ ] Unit test coverage ≥80% for new provider functionality
- [ ] Integration tests verify end-to-end multi-provider workflows
- [ ] Frontend components handle loading states and errors appropriately
- [ ] No API keys are logged or exposed in responses
- [ ] Provider switching works seamlessly within conversations

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in dependency order
- [ ] Each task validation passed immediately after implementation
- [ ] All validation commands executed successfully
- [ ] Full test suite passes (unit + integration)
- [ ] No linting or type checking errors
- [ ] Manual testing confirms all providers work
- [ ] Settings modal functions correctly
- [ ] Provider model selector displays properly
- [ ] API key security verified
- [ ] Backward compatibility with Ollama confirmed
- [ ] Performance acceptable for provider operations
- [ ] Error handling tested for all failure scenarios
- [ ] Documentation updated for new provider configuration

---

## NOTES

### Design Decisions

1. **Provider Configuration**: Using environment variables for default API keys with database override for user-specific keys
2. **Security**: API keys encrypted at rest using Fernet symmetric encryption with environment-based key
3. **Backward Compatibility**: Maintaining existing `ollama/` prefix and function names to avoid breaking changes
4. **UI/UX**: Provider grouping in model selector for better organization, settings modal for secure key management
5. **Error Handling**: Graceful degradation when providers are unavailable, clear user feedback for configuration issues

### Trade-offs

1. **Complexity vs Flexibility**: Added complexity for comprehensive multi-provider support vs simple single-provider approach
2. **Security vs Convenience**: Encrypted storage requires additional setup vs plain text storage
3. **UI Complexity**: Provider grouping adds visual complexity vs simple model list
4. **Performance**: Provider health checking adds latency vs immediate model selection

### Future Enhancements

1. **Provider Fallback**: Automatic fallback to alternative providers when primary fails
2. **Cost Optimization**: Provider selection based on cost per token
3. **Model Comparison**: Side-by-side responses from multiple providers
4. **Usage Analytics**: Track usage and costs per provider
5. **Advanced Settings**: Provider-specific parameters (temperature, max_tokens, etc.)
