# FastAPI Testing Best Practices Research

## 1. FastAPI Testing Fundamentals

### Test Client Setup
```python
from fastapi.testclient import TestClient
from httpx import AsyncClient
import pytest

# Sync testing
def test_sync_endpoint():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200

# Async testing
@pytest.mark.asyncio
async def test_async_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/health")
    assert response.status_code == 200
```

### Dependency Overrides
```python
from fastapi import Depends

def override_dependency():
    return "test_value"

app.dependency_overrides[get_database] = override_dependency
```

## 2. Pytest Async Patterns

### Basic Async Test Setup
```python
import pytest
import asyncio

# Configure async event loop
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Async fixtures
@pytest.fixture
async def async_client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.mark.asyncio
async def test_async_function(async_client):
    response = await async_client.get("/api/endpoint")
    assert response.status_code == 200
```

### Async Context Managers
```python
@pytest.fixture
async def db_session():
    async with async_session() as session:
        yield session
        await session.rollback()
```

## 3. MongoDB Testing with In-Memory Databases

### MongoMock for Unit Tests
```python
import mongomock
import pytest
from motor.motor_asyncio import AsyncIOMotorClient

@pytest.fixture
async def mock_db():
    client = AsyncIOMotorClient("mongodb://localhost", mongo_client_class=mongomock.MongoClient)
    db = client.test_db
    yield db
    await client.drop_database("test_db")

@pytest.mark.asyncio
async def test_mongodb_operation(mock_db):
    collection = mock_db.conversations
    doc = {"message": "test"}
    result = await collection.insert_one(doc)
    assert result.inserted_id
```

### Testcontainers for Integration Tests
```python
from testcontainers.mongodb import MongoDbContainer
import pytest

@pytest.fixture(scope="session")
def mongodb_container():
    with MongoDbContainer() as mongo:
        yield mongo

@pytest.fixture
async def real_db(mongodb_container):
    client = AsyncIOMotorClient(mongodb_container.get_connection_url())
    db = client.test_db
    yield db
    await client.drop_database("test_db")
```

## 4. Mocking External Services

### HTTP Service Mocking
```python
import httpx
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
@patch('httpx.AsyncClient.get')
async def test_external_api_call(mock_get):
    mock_response = AsyncMock()
    mock_response.json.return_value = {"result": "success"}
    mock_response.status_code = 200
    mock_get.return_value = mock_response
    
    # Test your function that makes HTTP calls
    result = await your_api_function()
    assert result["result"] == "success"
```

### MCP Service Mocking
```python
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_mcp_client():
    client = AsyncMock()
    client.call_tool.return_value = {"content": [{"type": "text", "text": "mocked result"}]}
    return client

@pytest.mark.asyncio
async def test_mcp_integration(mock_mcp_client):
    # Inject mock into your service
    service = YourService(mcp_client=mock_mcp_client)
    result = await service.process_request("test")
    assert "mocked result" in result
```

## 5. Testing Streaming Responses

### Server-Sent Events Testing
```python
@pytest.mark.asyncio
async def test_sse_stream():
    async with AsyncClient(app=app, base_url="http://test") as client:
        async with client.stream("GET", "/api/stream") as response:
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream"
            
            chunks = []
            async for chunk in response.aiter_text():
                chunks.append(chunk)
                if len(chunks) >= 3:  # Test first few chunks
                    break
            
            assert len(chunks) > 0
            assert "data:" in chunks[0]
```

### Chat Streaming Testing
```python
import json

@pytest.mark.asyncio
async def test_chat_stream():
    async with AsyncClient(app=app, base_url="http://test") as client:
        request_data = {"message": "test", "conversation_id": "123"}
        
        async with client.stream("POST", "/api/chat/stream", json=request_data) as response:
            messages = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    messages.append(data)
                    if data.get("type") == "done":
                        break
            
            assert len(messages) > 0
            assert any(msg.get("type") == "token" for msg in messages)
```

## 6. Test Organization Patterns

### Conftest.py Structure
```python
# conftest.py
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

@pytest.fixture(scope="session")
def app():
    from main import app
    return app

@pytest.fixture
def client(app):
    return TestClient(app)

@pytest.fixture
async def async_client(app):
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture(autouse=True)
def reset_dependency_overrides(app):
    yield
    app.dependency_overrides.clear()
```

### Test Categories
```python
# test_unit.py - Fast unit tests
@pytest.mark.unit
def test_pure_function():
    pass

# test_integration.py - Database/external service tests  
@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_integration():
    pass

# test_e2e.py - End-to-end tests
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_workflow():
    pass
```

## 7. Performance and Load Testing

### Basic Load Testing
```python
import asyncio
import time

@pytest.mark.asyncio
async def test_concurrent_requests():
    async with AsyncClient(app=app, base_url="http://test") as client:
        start_time = time.time()
        
        tasks = [client.get("/api/health") for _ in range(100)]
        responses = await asyncio.gather(*tasks)
        
        end_time = time.time()
        
        assert all(r.status_code == 200 for r in responses)
        assert end_time - start_time < 5.0  # Should complete within 5 seconds
```

## 8. Error Handling Testing

### Exception Testing
```python
@pytest.mark.asyncio
async def test_error_handling():
    with patch('your_service.external_call', side_effect=Exception("API Error")):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/endpoint")
            assert response.status_code == 500
            assert "error" in response.json()
```

## 9. Minimal Test Examples for OhSee Project

### Chat Endpoint Test
```python
@pytest.mark.asyncio
async def test_chat_endpoint(async_client, mock_db, mock_mcp_client):
    response = await async_client.post("/api/chat", json={
        "message": "test message",
        "conversation_id": "test-123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
```

### Conversation Management Test
```python
@pytest.mark.asyncio
async def test_create_conversation(async_client, mock_db):
    response = await async_client.post("/api/conversations", json={
        "title": "Test Conversation"
    })
    assert response.status_code == 201
    assert response.json()["title"] == "Test Conversation"
```

### MCP Tool Integration Test
```python
@pytest.mark.asyncio
async def test_web_search_tool(mock_mcp_client):
    mock_mcp_client.call_tool.return_value = {
        "content": [{"type": "text", "text": "Search results"}]
    }
    
    # Test your web search integration
    result = await search_web("test query", mock_mcp_client)
    assert "Search results" in result
```