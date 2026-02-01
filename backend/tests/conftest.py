import asyncio
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock

import pytest
import mongomock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from bson import ObjectId

# Ensure project root is on sys.path
TESTS_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(TESTS_DIR, "..", ".."))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
for p in (PROJECT_ROOT, BACKEND_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_mongodb():
    """Provide a mock MongoDB collection for testing."""
    client = mongomock.MongoClient()
    db = client.test_db
    return db


@pytest.fixture
def mock_conversations_collection(mock_mongodb):
    """Mock conversations collection with sample data."""
    collection = mock_mongodb.conversations
    
    # Insert sample conversations
    sample_conversations = [
        {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "title": "Test Conversation 1",
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"}
            ],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        },
        {
            "_id": ObjectId("507f1f77bcf86cd799439012"),
            "title": "Test Conversation 2",
            "messages": [
                {"role": "user", "content": "How are you?"},
                {"role": "assistant", "content": "I'm doing well!"}
            ],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
    ]
    
    collection.insert_many(sample_conversations)
    return collection


@pytest.fixture
def mock_mcp_service():
    """Mock MCP service for testing external tool calls."""
    mock = AsyncMock()
    mock.submit_mcp_request = AsyncMock()
    mock.wait_mcp_response = AsyncMock()
    return mock


@pytest.fixture
def mock_ollama_service():
    """Mock Ollama service for testing chat functionality."""
    mock = AsyncMock()
    mock.chat_with_ollama = AsyncMock(return_value="Mocked response")
    mock.stream_chat_with_ollama = AsyncMock()
    return mock


@pytest.fixture
def mock_provider_service():
    """Mock provider service for testing multi-provider functionality."""
    mock = AsyncMock()
    mock.chat_with_provider = AsyncMock(return_value="Mocked provider response")
    mock.stream_chat_with_provider = AsyncMock()
    mock.get_available_models_by_provider = AsyncMock(return_value={
        'ollama': ['llama3.1', 'mistral'],
        'openai': ['gpt-3.5-turbo', 'gpt-4'],
        'anthropic': ['claude-3-haiku-20240307']
    })
    mock.get_provider_status = AsyncMock(return_value={
        'provider_id': 'openai',
        'name': 'OpenAI',
        'available': True,
        'configured': True
    })
    mock.validate_provider_api_key = AsyncMock(return_value={
        'valid': True,
        'message': 'API key validated successfully'
    })
    return mock


@pytest.fixture
def mock_profile_service():
    """Mock profile service for testing AI profile functionality."""
    mock = AsyncMock()
    
    # Sample profile data
    sample_profile = {
        "_id": "507f1f77bcf86cd799439013",
        "name": "Test Assistant",
        "communication_style": "professional",
        "expertise_areas": ["AI", "Technology"],
        "user_id": "default",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    mock.get_profiles_for_user = AsyncMock(return_value=[sample_profile])
    mock.get_profile_by_id_service = AsyncMock(return_value=sample_profile)
    mock.get_active_profile_service = AsyncMock(return_value=sample_profile)
    mock.create_profile_service = AsyncMock(return_value="507f1f77bcf86cd799439013")
    mock.update_profile_service = AsyncMock(return_value=True)
    mock.delete_profile_service = AsyncMock(return_value=True)
    mock.set_active_profile_service = AsyncMock(return_value=True)
    mock.get_system_prompt_for_user = AsyncMock(return_value="You are Test Assistant, an AI assistant with a professional communication style. Your areas of expertise include: AI, Technology. Maintain a formal, business-appropriate tone. Be concise and direct.")
    mock.generate_system_prompt = MagicMock(return_value="Generated system prompt")
    
    return mock


@pytest.fixture
def mock_profiles_collection(mock_mongodb):
    """Mock profiles collection with sample data."""
    collection = mock_mongodb.ai_profiles
    
    # Insert sample profiles
    sample_profiles = [
        {
            "_id": ObjectId("507f1f77bcf86cd799439013"),
            "name": "Professional Assistant",
            "communication_style": "professional",
            "expertise_areas": ["Business", "Technology"],
            "user_id": "default",
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        },
        {
            "_id": ObjectId("507f1f77bcf86cd799439014"),
            "name": "Creative Helper",
            "communication_style": "creative",
            "expertise_areas": ["Art", "Writing"],
            "user_id": "default",
            "is_active": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
    ]
    
    collection.insert_many(sample_profiles)
    return collection


@pytest.fixture
def sample_chat_payload():
    """Sample chat payload for testing."""
    return {
        "message": "Test message",
        "conversation_id": None,
        "model": "llama3.1",
        "tool": None
    }


@pytest.fixture
def sample_chat_messages():
    """Sample chat messages for testing."""
    return [
        {"role": "user", "content": "Hello", "timestamp": datetime.now(timezone.utc)},
        {"role": "assistant", "content": "Hi there!", "timestamp": datetime.now(timezone.utc)}
    ]


class MockFastAPI:
    """Mock FastAPI app for testing."""
    def __init__(self):
        self.dependency_overrides = {}
    
    def include_router(self, router):
        pass


@pytest.fixture
def mock_fastapi_app():
    """Mock FastAPI application for testing."""
    return MockFastAPI()


@pytest.fixture
def test_client(mock_fastapi_app):
    """Test client for FastAPI testing."""
    app = FastAPI()
    return TestClient(app)
