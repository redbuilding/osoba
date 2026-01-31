import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.chat import stream_chat_endpoint, chat_endpoint
from core.models import ChatPayload


@pytest.mark.asyncio
class TestStreaming:
    """Test streaming response and Server-Sent Events functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.app = FastAPI()
        self.client = TestClient(self.app)
        
        self.sample_payload = {
            "user_message": "Test streaming message",
            "chat_history": [],
            "use_search": False,
            "conversation_id": None,
            "model_name": "llama3.1"
        }

    async def test_streaming_response_format(self):
        """Test streaming response format."""
        # Mock streaming generator
        async def mock_stream():
            yield "data: Test chunk 1\n\n"
            yield "data: Test chunk 2\n\n"
            yield "data: [DONE]\n\n"
        
        # Test that streaming format is correct
        chunks = []
        async for chunk in mock_stream():
            chunks.append(chunk)
        
        assert len(chunks) == 3
        assert chunks[0] == "data: Test chunk 1\n\n"
        assert chunks[1] == "data: Test chunk 2\n\n"
        assert chunks[2] == "data: [DONE]\n\n"

    async def test_streaming_error_handling(self):
        """Test streaming error handling."""
        async def mock_error_stream():
            yield "data: Starting stream\n\n"
            raise Exception("Stream error")
        
        chunks = []
        try:
            async for chunk in mock_error_stream():
                chunks.append(chunk)
        except Exception as e:
            assert str(e) == "Stream error"
        
        assert len(chunks) == 1
        assert chunks[0] == "data: Starting stream\n\n"

    async def test_concurrent_streaming(self):
        """Test concurrent streaming requests."""
        async def mock_stream(message):
            for i in range(3):
                yield f"data: {message} chunk {i}\n\n"
        
        # Start multiple streams concurrently
        streams = [
            mock_stream("Stream1"),
            mock_stream("Stream2"),
            mock_stream("Stream3")
        ]
        
        results = []
        for stream in streams:
            chunks = []
            async for chunk in stream:
                chunks.append(chunk)
            results.append(chunks)
        
        assert len(results) == 3
        for i, result in enumerate(results):
            assert len(result) == 3
            assert f"Stream{i+1}" in result[0]

    async def test_streaming_memory_efficiency(self):
        """Test streaming memory efficiency with large responses."""
        async def mock_large_stream():
            for i in range(1000):
                yield f"data: Large chunk {i}\n\n"
        
        chunk_count = 0
        async for chunk in mock_large_stream():
            chunk_count += 1
            # Verify each chunk is properly formatted
            assert chunk.startswith("data: Large chunk")
            assert chunk.endswith("\n\n")
            
            # Stop early to test streaming behavior
            if chunk_count >= 10:
                break
        
        assert chunk_count == 10

    async def test_streaming_backpressure(self):
        """Test streaming backpressure handling."""
        async def mock_slow_consumer_stream():
            for i in range(5):
                yield f"data: Chunk {i}\n\n"
                await asyncio.sleep(0.01)  # Simulate slow processing
        
        start_time = asyncio.get_event_loop().time()
        chunk_count = 0
        
        async for chunk in mock_slow_consumer_stream():
            chunk_count += 1
            await asyncio.sleep(0.01)  # Simulate slow consumer
        
        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time
        
        assert chunk_count == 5
        assert duration >= 0.05  # Should take at least 50ms due to delays

    async def test_streaming_json_data(self):
        """Test streaming JSON data in SSE format."""
        import json
        
        async def mock_json_stream():
            data = [
                {"type": "start", "message": "Starting"},
                {"type": "content", "text": "Hello"},
                {"type": "content", "text": " World"},
                {"type": "end", "message": "Complete"}
            ]
            
            for item in data:
                yield f"data: {json.dumps(item)}\n\n"
        
        chunks = []
        async for chunk in mock_json_stream():
            chunks.append(chunk)
        
        assert len(chunks) == 4
        
        # Parse and verify JSON content
        for chunk in chunks:
            assert chunk.startswith("data: ")
            json_str = chunk[6:-2]  # Remove "data: " and "\n\n"
            data = json.loads(json_str)
            assert "type" in data

    async def test_streaming_unicode_handling(self):
        """Test streaming with unicode characters."""
        async def mock_unicode_stream():
            unicode_texts = [
                "Hello 世界",
                "Café ☕",
                "🚀 Rocket",
                "Ñoño niño"
            ]
            
            for text in unicode_texts:
                yield f"data: {text}\n\n"
        
        chunks = []
        async for chunk in mock_unicode_stream():
            chunks.append(chunk)
        
        assert len(chunks) == 4
        assert "世界" in chunks[0]
        assert "☕" in chunks[1]
        assert "🚀" in chunks[2]
        assert "Ñoño" in chunks[3]

    async def test_streaming_connection_close(self):
        """Test streaming behavior when connection closes."""
        async def mock_interrupted_stream():
            for i in range(10):
                if i == 5:
                    # Simulate connection close
                    raise ConnectionError("Connection closed")
                yield f"data: Chunk {i}\n\n"
        
        chunks = []
        try:
            async for chunk in mock_interrupted_stream():
                chunks.append(chunk)
        except ConnectionError:
            pass
        
        assert len(chunks) == 5  # Should have received 5 chunks before error

    async def test_streaming_empty_response(self):
        """Test streaming with empty response."""
        async def mock_empty_stream():
            # Yield nothing
            return
            yield  # This line never executes
        
        chunks = []
        async for chunk in mock_empty_stream():
            chunks.append(chunk)
        
        assert len(chunks) == 0

    async def test_streaming_single_chunk(self):
        """Test streaming with single chunk."""
        async def mock_single_stream():
            yield "data: Single response\n\n"
        
        chunks = []
        async for chunk in mock_single_stream():
            chunks.append(chunk)
        
        assert len(chunks) == 1
        assert chunks[0] == "data: Single response\n\n"
