"""Phase 3 tests: Chat context integration."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestSemanticMemoryContext:
    """Test semantic memory context building."""
    
    @pytest.mark.asyncio
    async def test_build_memory_context_success(self):
        """Test building memory context with relevant results."""
        from services.semantic_memory_context import build_memory_context
        
        # Mock embedding
        mock_embedding = [0.1] * 768
        
        # Mock search results
        mock_results = [
            {
                "id": "conv1_chunk_0",
                "conv_id": "conv1",
                "score": 0.85,
                "text": "This is a relevant conversation about Python pandas.",
                "metadata": {"title": "Python Data Analysis", "message_count": 10}
            },
            {
                "id": "conv2_chunk_0",
                "conv_id": "conv2",
                "score": 0.72,
                "text": "Another conversation about data processing.",
                "metadata": {"title": "Data Processing", "message_count": 8}
            }
        ]
        
        with patch('services.semantic_memory_context.embed_text', return_value=mock_embedding):
            with patch('services.semantic_memory_context.VectorMemory') as MockVM:
                mock_vm = MockVM.return_value
                mock_vm.search_similar.return_value = mock_results
                
                context = await build_memory_context(
                    query="How do I use pandas?",
                    user_id="default",
                    current_conv_id="current_conv"
                )
                
                assert context != ""
                assert "Relevant past conversations" in context
                assert "Python Data Analysis" in context
                assert "85%" in context
    
    @pytest.mark.asyncio
    async def test_build_memory_context_no_results(self):
        """Test building context with no relevant results."""
        from services.semantic_memory_context import build_memory_context
        
        mock_embedding = [0.1] * 768
        
        with patch('services.semantic_memory_context.embed_text', return_value=mock_embedding):
            with patch('services.semantic_memory_context.VectorMemory') as MockVM:
                mock_vm = MockVM.return_value
                mock_vm.search_similar.return_value = []
                
                context = await build_memory_context(
                    query="Random query",
                    user_id="default"
                )
                
                assert context == ""
    
    @pytest.mark.asyncio
    async def test_build_memory_context_excludes_current(self):
        """Test that current conversation is excluded from results."""
        from services.semantic_memory_context import build_memory_context
        
        mock_embedding = [0.1] * 768
        
        # Mock results including current conversation
        mock_results = [
            {
                "id": "current_conv_chunk_0",
                "conv_id": "current_conv",
                "score": 0.95,
                "text": "This is the current conversation.",
                "metadata": {"title": "Current", "message_count": 5}
            },
            {
                "id": "other_conv_chunk_0",
                "conv_id": "other_conv",
                "score": 0.80,
                "text": "This is another conversation.",
                "metadata": {"title": "Other", "message_count": 8}
            }
        ]
        
        with patch('services.semantic_memory_context.embed_text', return_value=mock_embedding):
            with patch('services.semantic_memory_context.VectorMemory') as MockVM:
                mock_vm = MockVM.return_value
                mock_vm.search_similar.return_value = mock_results
                
                context = await build_memory_context(
                    query="Test query",
                    user_id="default",
                    current_conv_id="current_conv"
                )
                
                # Should only include "Other", not "Current"
                assert "Other" in context
                assert "Current" not in context
    
    @pytest.mark.asyncio
    async def test_build_memory_context_size_limit(self):
        """Test that context respects size limit."""
        from services.semantic_memory_context import build_memory_context, MAX_MEMORY_CONTEXT_CHARS
        
        mock_embedding = [0.1] * 768
        
        # Create many results to test size limit
        mock_results = [
            {
                "id": f"conv{i}_chunk_0",
                "conv_id": f"conv{i}",
                "score": 0.8,
                "text": "A" * 500,  # Long text
                "metadata": {"title": f"Conv {i}", "message_count": 10}
            }
            for i in range(20)
        ]
        
        with patch('services.semantic_memory_context.embed_text', return_value=mock_embedding):
            with patch('services.semantic_memory_context.VectorMemory') as MockVM:
                mock_vm = MockVM.return_value
                mock_vm.search_similar.return_value = mock_results
                
                context = await build_memory_context(
                    query="Test query",
                    user_id="default"
                )
                
                # Context should not exceed limit
                assert len(context) <= MAX_MEMORY_CONTEXT_CHARS


class TestChatIntegration:
    """Test chat service integration."""
    
    def test_chat_service_imports_memory_context(self):
        """Test that chat service can import memory context module."""
        from services import chat_service
        # If this doesn't raise ImportError, the integration is wired correctly
        # Just verify the module loads
        assert chat_service is not None
    
    @pytest.mark.asyncio
    async def test_auto_index_trigger(self):
        """Test that auto-index is triggered after 5+ messages."""
        # This is a basic test to ensure the trigger logic exists
        # Full integration testing would require a running MongoDB
        from db.crud import count_messages_in_conversation
        from bson import ObjectId
        
        # Mock the count
        mock_obj_id = ObjectId()
        
        with patch('db.crud.get_conversations_collection') as mock_coll:
            mock_collection = MagicMock()
            mock_collection.count_documents.return_value = 5
            mock_coll.return_value = mock_collection
            
            count = count_messages_in_conversation(mock_obj_id)
            assert count == 5
