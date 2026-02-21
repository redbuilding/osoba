"""Phase 2 tests: Conversation indexing and API endpoints."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from bson import ObjectId


class TestConversationIndexing:
    """Test conversation indexing service."""
    
    @pytest.mark.asyncio
    async def test_index_conversation_success(self):
        """Test successful conversation indexing."""
        from services.conversation_indexing import index_conversation
        
        # Mock conversation data
        mock_conv = {
            "_id": ObjectId(),
            "title": "Test Conversation",
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"},
                {"role": "user", "content": "How are you?"},
                {"role": "assistant", "content": "I'm good"},
                {"role": "user", "content": "Great!"}
            ],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        with patch('services.conversation_indexing.get_conversation_by_id', return_value=mock_conv):
            with patch('db.crud.mark_conversation_indexed', return_value=True):
                success = await index_conversation(str(mock_conv["_id"]))
                assert success is True
    
    @pytest.mark.asyncio
    async def test_index_conversation_too_few_messages(self):
        """Test that conversations with <5 messages are skipped."""
        from services.conversation_indexing import index_conversation
        
        mock_conv = {
            "_id": ObjectId(),
            "title": "Short Conversation",
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi"}
            ]
        }
        
        with patch('services.conversation_indexing.get_conversation_by_id', return_value=mock_conv):
            success = await index_conversation(str(mock_conv["_id"]))
            assert success is False
    
    @pytest.mark.asyncio
    async def test_find_conversations_to_index(self):
        """Test finding conversations eligible for indexing."""
        from services.conversation_indexing import find_conversations_to_index
        
        mock_convs = [
            {"_id": ObjectId(), "title": "Conv 1"},
            {"_id": ObjectId(), "title": "Conv 2"}
        ]
        
        with patch('db.crud.find_conversations_for_auto_indexing', return_value=mock_convs):
            conv_ids = await find_conversations_to_index(limit=10)
            assert len(conv_ids) == 2


class TestCRUDIndexingMethods:
    """Test CRUD indexing status methods."""
    
    def test_mark_conversation_indexed(self):
        """Test marking conversation as indexed."""
        from db.crud import mark_conversation_indexed
        
        # Mock collection
        mock_collection = MagicMock()
        mock_collection.update_one.return_value = MagicMock(matched_count=1)
        
        with patch('db.crud.get_conversations_collection', return_value=mock_collection):
            result = mark_conversation_indexed("test_id", indexed=True)
            assert result is True
            assert mock_collection.update_one.called
    
    def test_get_conversation_indexing_status(self):
        """Test getting indexing status."""
        from db.crud import get_conversation_indexing_status
        
        conv_id = str(ObjectId())
        mock_conv = {
            "_id": ObjectId(conv_id),
            "indexed_to_memory": True,
            "indexed_at": datetime.now(timezone.utc),
            "messages": [{"role": "user", "content": "test"}] * 5
        }
        
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = mock_conv
        
        with patch('db.crud.get_conversations_collection', return_value=mock_collection):
            status = get_conversation_indexing_status(conv_id)
            assert status is not None
            assert status["indexed"] is True
            assert status["message_count"] == 5
    
    def test_find_conversations_for_auto_indexing(self):
        """Test finding conversations for auto-indexing."""
        from db.crud import find_conversations_for_auto_indexing
        
        mock_convs = [
            {"_id": ObjectId(), "title": "Conv 1", "updated_at": datetime.now(timezone.utc) - timedelta(minutes=15)},
            {"_id": ObjectId(), "title": "Conv 2", "updated_at": datetime.now(timezone.utc) - timedelta(minutes=20)}
        ]
        
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_convs
        
        mock_collection = MagicMock()
        mock_collection.find.return_value = mock_cursor
        
        with patch('db.crud.get_conversations_collection', return_value=mock_collection):
            convs = find_conversations_for_auto_indexing(limit=10)
            assert len(convs) == 2


class TestMemoryAPI:
    """Test memory API endpoints."""
    
    @pytest.mark.asyncio
    async def test_save_conversation_endpoint(self):
        """Test manual save endpoint."""
        from api.memory import save_conversation_to_memory
        
        with patch('api.memory.index_conversation', return_value=True):
            result = await save_conversation_to_memory("test_conv_id")
            assert result["status"] == "success"
            assert "conv_id" in result
    
    @pytest.mark.asyncio
    async def test_get_memory_stats_endpoint(self):
        """Test stats endpoint."""
        from api.memory import get_memory_stats
        
        mock_stats = {"total_chunks": 10, "collection_name": "conversations"}
        
        with patch('api.memory.VectorMemory') as MockVM:
            mock_vm = MockVM.return_value
            mock_vm.get_stats.return_value = mock_stats
            
            result = await get_memory_stats()
            assert result["status"] == "ok"
            assert "total_chunks" in result
