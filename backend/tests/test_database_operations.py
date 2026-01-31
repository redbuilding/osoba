import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from bson import ObjectId

from db.crud import (
    get_all_conversations, count_messages_in_conversation, get_conversation_by_id,
    get_messages_by_conv_id, delete_conversation_by_id, search_conversations,
    rename_conversation_by_id
)
from core.models import ChatMessage


@pytest.mark.asyncio
class TestDatabaseOperations:
    """Test database CRUD operations with proper mocking."""

    def setup_method(self):
        """Set up test fixtures."""
        self.valid_object_id = ObjectId("507f1f77bcf86cd799439011")
        self.invalid_object_id = "invalid_id"
        
        self.sample_conversation = {
            "_id": self.valid_object_id,
            "title": "Test Conversation",
            "messages": [
                {
                    "role": "user",
                    "content": "Hello",
                    "timestamp": datetime.now(timezone.utc),
                    "is_html": False
                },
                {
                    "role": "assistant", 
                    "content": "Hi there!",
                    "timestamp": datetime.now(timezone.utc),
                    "is_html": False
                }
            ],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "model_name": "llama3.1"
        }

    async def test_get_all_conversations(self):
        """Test retrieving all conversations."""
        mock_collection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value.limit.return_value = [
            {
                "_id": self.valid_object_id,
                "title": "Conversation 1",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
        ]
        mock_collection.find.return_value = mock_cursor
        
        with patch('db.crud.get_conversations_collection', return_value=mock_collection):
            conversations = get_all_conversations()
        
        assert len(conversations) == 1
        assert conversations[0]["title"] == "Conversation 1"
        mock_collection.find.assert_called_once_with({}, {"messages": 0, "youtube_transcript": 0})

    async def test_get_conversation_by_id_valid(self):
        """Test retrieving conversation by valid ID."""
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = self.sample_conversation
        
        with patch('db.crud.get_conversations_collection', return_value=mock_collection):
            conversation = get_conversation_by_id(str(self.valid_object_id))
        
        assert conversation is not None
        assert conversation["title"] == "Test Conversation"
        mock_collection.find_one.assert_called_once_with({"_id": self.valid_object_id})

    async def test_get_conversation_by_id_invalid(self):
        """Test retrieving conversation by invalid ID."""
        mock_collection = MagicMock()
        
        with patch('db.crud.get_conversations_collection', return_value=mock_collection):
            conversation = get_conversation_by_id(self.invalid_object_id)
        
        assert conversation is None
        mock_collection.find_one.assert_not_called()

    async def test_get_messages_by_conv_id_valid(self):
        """Test retrieving messages by valid conversation ID."""
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = self.sample_conversation
        
        with patch('db.crud.get_conversations_collection', return_value=mock_collection):
            messages = get_messages_by_conv_id(str(self.valid_object_id))
        
        assert messages is not None
        assert len(messages) == 2
        assert all(isinstance(msg, ChatMessage) for msg in messages)
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"

    async def test_delete_conversation_by_id_valid(self):
        """Test deleting conversation by valid ID."""
        mock_collection = MagicMock()
        mock_result = MagicMock()
        mock_result.deleted_count = 1
        mock_collection.delete_one.return_value = mock_result
        
        with patch('db.crud.get_conversations_collection', return_value=mock_collection):
            result = delete_conversation_by_id(str(self.valid_object_id))
        
        assert result is True
        mock_collection.delete_one.assert_called_once_with({"_id": self.valid_object_id})

    async def test_delete_conversation_by_id_invalid(self):
        """Test deleting conversation by invalid ID."""
        mock_collection = MagicMock()
        
        with patch('db.crud.get_conversations_collection', return_value=mock_collection):
            result = delete_conversation_by_id(self.invalid_object_id)
        
        assert result is False
        mock_collection.delete_one.assert_not_called()

    async def test_search_conversations(self):
        """Test searching conversations."""
        mock_collection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value.limit.return_value = [
            {
                "_id": self.valid_object_id,
                "title": "Python Tutorial",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
        ]
        mock_collection.find.return_value = mock_cursor
        
        with patch('db.crud.get_conversations_collection', return_value=mock_collection):
            results = search_conversations("python", limit=10)
        
        assert len(results) == 1
        assert results[0]["title"] == "Python Tutorial"
        
        # Verify search query structure
        call_args = mock_collection.find.call_args[0]
        assert "$or" in call_args[0]
        assert len(call_args[0]["$or"]) == 2

    async def test_rename_conversation_by_id_valid(self):
        """Test renaming conversation by valid ID."""
        mock_collection = MagicMock()
        mock_update_result = MagicMock()
        mock_update_result.matched_count = 1
        mock_collection.update_one.return_value = mock_update_result
        mock_collection.find_one.return_value = {
            "_id": self.valid_object_id,
            "title": "New Title",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        with patch('db.crud.get_conversations_collection', return_value=mock_collection):
            result = rename_conversation_by_id(str(self.valid_object_id), "New Title")
        
        assert result is not None
        assert result["title"] == "New Title"
        mock_collection.update_one.assert_called_once()

    async def test_objectid_validation_edge_cases(self):
        """Test ObjectId validation with various edge cases."""
        invalid_ids = [
            "",
            "123",
            "not_an_objectid",
            "507f1f77bcf86cd79943901",  # Too short
            "507f1f77bcf86cd799439011x",  # Invalid character
            None
        ]
        
        for invalid_id in invalid_ids:
            # These functions should handle invalid ObjectIds gracefully
            assert get_conversation_by_id(invalid_id) is None
            assert get_messages_by_conv_id(invalid_id) is None
            assert delete_conversation_by_id(invalid_id) is False
            assert rename_conversation_by_id(invalid_id, "New Title") is None

    async def test_count_messages_in_conversation(self):
        """Test counting messages in a conversation."""
        mock_collection = MagicMock()
        mock_collection.count_documents.return_value = 5
        
        with patch('db.crud.get_conversations_collection', return_value=mock_collection):
            count = count_messages_in_conversation(self.valid_object_id)
        
        assert count == 5
        mock_collection.count_documents.assert_called_once()

    async def test_message_validation_in_get_messages(self):
        """Test message validation when retrieving messages."""
        conversation_with_bad_messages = {
            "_id": self.valid_object_id,
            "title": "Test Conversation",
            "messages": [
                {
                    "role": "user",
                    "content": "Valid message",
                    "timestamp": datetime.now(timezone.utc),
                    "is_html": False
                },
                {
                    # Missing required fields - this will cause validation error
                    "content": "Invalid message - no role"
                },
                "not a dict",  # Invalid message format - filtered out by isinstance check
                {
                    "role": "assistant",
                    "content": "Another valid message",
                    "timestamp": datetime.now(timezone.utc),
                    "is_html": False
                }
            ],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = conversation_with_bad_messages
        
        with patch('db.crud.get_conversations_collection', return_value=mock_collection):
            # The current implementation will raise ValidationError for invalid messages
            with pytest.raises(Exception):  # Pydantic ValidationError
                messages = get_messages_by_conv_id(str(self.valid_object_id))
