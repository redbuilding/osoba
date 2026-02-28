import pytest
from unittest.mock import Mock, patch, AsyncMock
from services.context_service import (
    get_user_context, get_profile_context, get_conversation_context,
    get_pinned_conversations, generate_conversation_summary, format_context_for_system_prompt
)
from db.crud import pin_conversation_for_context, get_pinned_conversations as get_pinned_from_db, update_conversation_summary
from api.user_context import router
from fastapi.testclient import TestClient
from fastapi import FastAPI

class TestContextService:
    
    @pytest.mark.asyncio
    async def test_get_user_context_success(self):
        """Test successful user context retrieval."""
        with patch('services.context_service.get_profile_context') as mock_profile, \
             patch('services.context_service.get_conversation_context') as mock_conv:
            
            mock_profile.return_value = "User role: Developer | Expertise: Python"
            mock_conv.return_value = "Previous chat: Discussed API design"
            
            result = await get_user_context("test_user")
            
            assert result["profile_context"] == "User role: Developer | Expertise: Python"
            assert result["conversation_context"] == "Previous chat: Discussed API design"
            assert result["total_chars"] > 0

    @pytest.mark.asyncio
    async def test_get_user_context_empty(self):
        """Test user context with no data."""
        with patch('services.context_service.get_profile_context') as mock_profile, \
             patch('services.context_service.get_conversation_context') as mock_conv:
            
            mock_profile.return_value = ""
            mock_conv.return_value = ""
            
            result = await get_user_context("test_user")
            
            assert result["profile_context"] == ""
            assert result["conversation_context"] == ""
            assert result["total_chars"] == 0

    @pytest.mark.asyncio
    async def test_get_profile_context_with_data(self):
        """Test profile context generation with full profile data."""
        mock_profile = {
            "role": "Software Developer",
            "expertise_areas": ["Python", "JavaScript"],
            "current_projects": "Building a chat application",
            "communication_style": "technical"
        }
        
        with patch('services.context_service.user_profiles_crud.get_user_profile', return_value=mock_profile):
            result = await get_profile_context("test_user")
            
            assert "Software Developer" in result
            assert "Python, JavaScript" in result
            assert "Building a chat application" in result
            assert "technical" in result

    @pytest.mark.asyncio
    async def test_get_profile_context_no_profile(self):
        """Test profile context with no active profile."""
        with patch('db.profiles_crud.get_active_profile', return_value=None):
            result = await get_profile_context("test_user")
            assert result == ""

    @pytest.mark.asyncio
    async def test_get_conversation_context_with_pinned(self):
        """Test conversation context with pinned conversations."""
        mock_conversations = [
            {"title": "API Design", "summary": "Discussed REST API patterns"},
            {"title": "Database Schema", "summary": "Planned user table structure"}
        ]
        
        with patch('services.context_service.get_pinned_conversations', return_value=mock_conversations):
            result = await get_conversation_context("test_user")
            
            assert "API Design: Discussed REST API patterns" in result
            assert "Database Schema: Planned user table structure" in result

    @pytest.mark.asyncio
    async def test_get_conversation_context_no_pinned(self):
        """Test conversation context with no pinned conversations."""
        with patch('services.context_service.get_pinned_conversations', return_value=[]):
            result = await get_conversation_context("test_user")
            assert result == ""

    def test_generate_conversation_summary_success(self):
        """Test conversation summary generation."""
        conversation_data = {
            "messages": [
                {"role": "user", "content": "How do I implement authentication?"},
                {"role": "assistant", "content": "You can use JWT tokens..."},
                {"role": "user", "content": "What about password hashing?"},
                {"role": "assistant", "content": "Use bcrypt for secure hashing..."}
            ]
        }
        
        result = generate_conversation_summary(conversation_data)
        
        assert "authentication" in result.lower() or "password hashing" in result.lower()
        assert len(result) <= 500  # Respects length limit (code targets 500)

    def test_generate_conversation_summary_empty(self):
        """Test conversation summary with no messages."""
        conversation_data = {"messages": []}
        
        result = generate_conversation_summary(conversation_data)
        assert result == ""

    def test_format_context_for_system_prompt_full(self):
        """Test system prompt formatting with full context."""
        context = {
            "profile_context": "User role: Developer",
            "conversation_context": "Previous: API discussion"
        }
        
        result = format_context_for_system_prompt(context)
        
        assert "=== Human User ===" in result
        assert "User role: Developer" in result
        assert "Previous: API discussion" in result

    def test_format_context_for_system_prompt_empty(self):
        """Test system prompt formatting with empty context."""
        context = {"profile_context": "", "conversation_context": ""}
        
        result = format_context_for_system_prompt(context)
        assert result == ""

class TestConversationCRUD:
    
    def test_pin_conversation_success(self):
        """Test successful conversation pinning."""
        with patch('db.mongodb.get_conversations_collection') as mock_collection:
            mock_collection.return_value.update_one.return_value.matched_count = 1
            
            result = pin_conversation_for_context("valid_id", "test_user", True)
            assert result is True

    def test_pin_conversation_invalid_id(self):
        """Test pinning with invalid conversation ID."""
        result = pin_conversation_for_context("invalid_id", "test_user", True)
        assert result is False

    def test_get_pinned_conversations_success(self):
        """Test retrieving pinned conversations."""
        mock_conversations = [
            {"_id": "conv1", "title": "Chat 1", "pinned_for_context": True},
            {"_id": "conv2", "title": "Chat 2", "pinned_for_context": True}
        ]
        
        with patch('db.mongodb.get_conversations_collection') as mock_collection:
            mock_collection.return_value.find.return_value.sort.return_value.limit.return_value = mock_conversations
            
            result = get_pinned_from_db("test_user", 5)
            assert len(result) == 2
            assert result[0]["title"] == "Chat 1"

    def test_update_conversation_summary_success(self):
        """Test successful conversation summary update."""
        with patch('db.mongodb.get_conversations_collection') as mock_collection:
            mock_collection.return_value.update_one.return_value.matched_count = 1
            
            result = update_conversation_summary("valid_id", "Test summary")
            assert result is True

class TestUserContextAPI:
    
    def setup_method(self):
        """Set up test client."""
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    @patch('services.context_service.get_user_context')
    @patch('services.context_service.format_context_for_system_prompt')
    def test_get_user_profile_context_success(self, mock_format, mock_get_context):
        """Test successful user context API call."""
        mock_get_context.return_value = {"profile_context": "test", "conversation_context": "test"}
        mock_format.return_value = "Formatted context"
        
        response = self.client.get("/api/user-context/profile")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "context" in data["data"]

    @patch('db.crud.pin_conversation_for_context')
    def test_pin_conversation_success(self, mock_pin):
        """Test successful conversation pinning API call."""
        mock_pin.return_value = True
        
        response = self.client.post("/api/user-context/pin-conversation", json={
            "conversation_id": "test_id",
            "pinned": True
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "pinned successfully" in data["message"]

    @patch('db.crud.pin_conversation_for_context')
    def test_pin_conversation_failure(self, mock_pin):
        """Test failed conversation pinning API call."""
        mock_pin.return_value = False
        
        response = self.client.post("/api/user-context/pin-conversation", json={
            "conversation_id": "invalid_id",
            "pinned": True
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    @patch('db.crud.get_pinned_conversations')
    def test_get_pinned_conversations_success(self, mock_get_pinned):
        """Test successful pinned conversations retrieval."""
        mock_get_pinned.return_value = [{"id": "conv1", "title": "Test Chat"}]
        
        response = self.client.get("/api/user-context/pinned-conversations")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["conversations"]) == 1

    @patch('db.crud.update_conversation_summary')
    def test_update_conversation_summary_success(self, mock_update):
        """Test successful conversation summary update."""
        mock_update.return_value = True
        
        response = self.client.post("/api/user-context/conversation-summary", json={
            "conversation_id": "test_id",
            "summary": "Test summary"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

class TestContextSizeLimits:
    
    @pytest.mark.asyncio
    async def test_context_size_limits_respected(self):
        """Test that context size limits are properly enforced."""
        # Create oversized context
        large_profile = "x" * 300  # Exceeds MAX_PROFILE_CHARS (200)
        large_conversation = "y" * 3000  # Exceeds MAX_CONVERSATION_CONTEXT_CHARS (2500)
        
        with patch('services.context_service.get_profile_context', return_value=large_profile), \
             patch('services.context_service.get_conversation_context', return_value=large_conversation):
            
            result = await get_user_context("test_user")
            
            # Check that context is truncated to limits
            assert len(result["profile_context"]) <= 200
            assert len(result["conversation_context"]) <= 2500
            assert result["total_chars"] <= 2700

    def test_conversation_summary_length_limit(self):
        """Test that conversation summaries respect length limits."""
        # Create conversation with very long messages
        long_message = "x" * 500
        conversation_data = {
            "messages": [
                {"role": "user", "content": long_message},
                {"role": "user", "content": long_message}
            ]
        }
        
        result = generate_conversation_summary(conversation_data)
        
        # Summary should be truncated to 500 characters (code target)
        assert len(result) <= 500

class TestErrorHandling:
    
    @pytest.mark.asyncio
    async def test_get_user_context_error_handling(self):
        """Test error handling in get_user_context."""
        with patch('services.context_service.get_profile_context', side_effect=Exception("Database error")):
            result = await get_user_context("test_user")
            
            # Should return empty context on error
            assert result["profile_context"] == ""
            assert result["conversation_context"] == ""
            assert result["total_chars"] == 0

    def test_generate_conversation_summary_error_handling(self):
        """Test error handling in conversation summary generation."""
        # Invalid conversation data
        invalid_data = {"invalid": "data"}
        
        result = generate_conversation_summary(invalid_data)
        assert result == ""
