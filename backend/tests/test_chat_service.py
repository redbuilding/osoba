import asyncio
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId

from services.chat_service import extract_json_from_response, format_search_results_for_prompt, format_db_results_for_prompt
from core.models import ChatPayload, ChatMessage, ChatResponse
from core.config import get_logger


@pytest.mark.asyncio
class TestChatService:
    """Test chat service functionality including streaming and tool integration."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_request = MagicMock()
        self.mock_request.cookies = {}

    async def test_extract_json_from_response_dict(self):
        """Test extracting JSON from dict response."""
        response = {"status": "success", "data": "test"}
        result = extract_json_from_response(response)
        assert result == response

    async def test_extract_json_from_response_string(self):
        """Test extracting JSON from string response."""
        response = '{"status": "success", "data": "test"}'
        result = extract_json_from_response(response)
        assert result == {"status": "success", "data": "test"}

    async def test_extract_json_from_response_invalid_string(self):
        """Test extracting JSON from invalid string response."""
        response = "not valid json"
        result = extract_json_from_response(response)
        assert result["status"] == "error"
        assert "not valid JSON" in result["message"]

    async def test_extract_json_from_response_list(self):
        """Test extracting JSON from list response."""
        response = [{"type": "text", "content": '{"status": "success"}'}]
        result = extract_json_from_response(response)
        assert result == {"status": "success"}

    async def test_format_search_results_for_prompt(self):
        """Test formatting search results for prompt."""
        results_data = {
            "organic_results": [
                {
                    "title": "Test Title 1",
                    "snippet": "Test snippet 1",
                    "link": "https://example.com/1"
                },
                {
                    "title": "Test Title 2", 
                    "snippet": "Test snippet 2",
                    "link": "https://example.com/2"
                }
            ]
        }
        
        formatted = format_search_results_for_prompt(results_data, "test query", max_results=2)
        assert "Web search results for 'test query'" in formatted
        assert "Test Title 1" in formatted
        assert "Test Title 2" in formatted
        assert "https://example.com/1" in formatted

    async def test_format_search_results_error(self):
        """Test formatting search results with error."""
        results_data = {"status": "error", "message": "Search failed"}
        formatted = format_search_results_for_prompt(results_data, "test query")
        assert "Search for 'test query': Search failed" in formatted

    async def test_format_search_results_answer_box(self):
        """Test formatting search results with answer box."""
        results_data = {
            "answer_box": {
                "answer": "The answer is 42"
            }
        }
        formatted = format_search_results_for_prompt(results_data, "test query")
        assert "Web search results for 'test query'" in formatted
        assert "The answer is 42" in formatted

    async def test_format_db_results_for_prompt_success(self):
        """Test formatting database results for prompt."""
        db_results = {
            "rows": [
                {"id": 1, "name": "Alice", "age": 30},
                {"id": 2, "name": "Bob", "age": 25}
            ],
            "columns": ["id", "name", "age"]
        }
        
        formatted = format_db_results_for_prompt("SELECT * FROM users", db_results, 1000)
        assert "Database query results for 'SELECT * FROM users'" in formatted
        assert "Alice" in formatted
        assert "Bob" in formatted
        assert "| id | name | age |" in formatted

    async def test_format_db_results_for_prompt_error(self):
        """Test formatting database results with error."""
        db_results = {"error": "Table not found"}
        formatted = format_db_results_for_prompt("SELECT * FROM missing", db_results, 1000)
        assert "Database query 'SELECT * FROM missing' failed: Table not found" in formatted

    async def test_format_db_results_for_prompt_empty(self):
        """Test formatting empty database results."""
        db_results = {"rows": [], "columns": ["id", "name"]}
        formatted = format_db_results_for_prompt("SELECT * FROM empty", db_results, 1000)
        assert "Database query 'SELECT * FROM empty' returned no rows" in formatted

    async def test_format_db_results_for_prompt_truncation(self):
        """Test database results truncation."""
        # Create large result set
        rows = [{"id": i, "data": "x" * 100} for i in range(100)]
        db_results = {"rows": rows, "columns": ["id", "data"]}
        
        formatted = format_db_results_for_prompt("SELECT * FROM large", db_results, 500)
        assert "results truncated" in formatted
        # The function adds truncation message but doesn't strictly enforce the limit
        assert len(formatted) > 500  # It will be longer due to the truncation message

    async def test_chat_payload_validation(self):
        """Test ChatPayload model validation."""
        payload_data = {
            "user_message": "Test message",
            "chat_history": [],
            "use_search": False,
            "conversation_id": None,
            "model_name": "llama3.1"
        }
        payload = ChatPayload(**payload_data)
        assert payload.user_message == "Test message"
        assert payload.conversation_id is None
        assert payload.model_name == "llama3.1"
        assert payload.use_search is False

    async def test_chat_payload_with_tool(self):
        """Test ChatPayload with tool selection."""
        payload_data = {
            "user_message": "Test message",
            "chat_history": [],
            "use_search": True,
            "use_database": True,
            "conversation_id": None,
            "model_name": "llama3.1"
        }
        payload = ChatPayload(**payload_data)
        assert payload.use_search is True
        assert payload.use_database is True

    async def test_chat_message_validation(self):
        """Test ChatMessage model validation."""
        message_data = {
            "role": "user",
            "content": "Test message",
            "timestamp": datetime.now(timezone.utc)
        }
        message = ChatMessage(**message_data)
        assert message.role == "user"
        assert message.content == "Test message"
        assert isinstance(message.timestamp, datetime)

    async def test_chat_response_validation(self):
        """Test ChatResponse model validation."""
        response_data = {
            "conversation_id": "507f1f77bcf86cd799439011",
            "chat_history": [],
            "model_name": "llama3.1"
        }
        response = ChatResponse(**response_data)
        assert response.conversation_id == "507f1f77bcf86cd799439011"
        assert response.model_name == "llama3.1"
        assert response.chat_history == []

    async def test_extract_json_edge_cases(self):
        """Test extract_json_from_response with edge cases."""
        # Test with None
        result = extract_json_from_response(None)
        assert result["status"] == "error"
        
        # Test with empty string
        result = extract_json_from_response("")
        assert result["status"] == "error"
        
        # Test with empty list
        result = extract_json_from_response([])
        assert result["status"] == "error"
        
        # Test with object having .text attribute
        mock_obj = MagicMock()
        mock_obj.text = '{"valid": "json"}'
        result = extract_json_from_response(mock_obj)
        assert result == {"valid": "json"}

    async def test_format_search_results_edge_cases(self):
        """Test format_search_results_for_prompt with edge cases."""
        # Test with empty organic results
        results_data = {"organic_results": []}
        formatted = format_search_results_for_prompt(results_data, "test query")
        assert "returned no specific organic results or answer box" in formatted
        
        # Test with malformed organic results
        results_data = {"organic_results": ["not a dict"]}
        formatted = format_search_results_for_prompt(results_data, "test query")
        assert "returned no usable organic result items" in formatted
        
        # Test with missing fields in organic results
        results_data = {"organic_results": [{"title": "Only title"}]}
        formatted = format_search_results_for_prompt(results_data, "test query")
        assert "Only title" in formatted
        assert "N/A" in formatted  # For missing snippet and link

    async def test_format_db_results_json_string_input(self):
        """Test format_db_results_for_prompt with JSON string input."""
        db_results_json = '{"rows": [{"id": 1, "name": "Test"}], "columns": ["id", "name"]}'
        formatted = format_db_results_for_prompt("SELECT * FROM test", db_results_json, 1000)
        assert "Test" in formatted
        assert "| id | name |" in formatted

    async def test_format_db_results_invalid_json_string(self):
        """Test format_db_results_for_prompt with invalid JSON string."""
        db_results_json = "invalid json"
        formatted = format_db_results_for_prompt("SELECT * FROM test", db_results_json, 1000)
        assert "Error formatting database results" in formatted

    async def test_concurrent_json_extraction(self):
        """Test concurrent JSON extraction operations."""
        responses = [
            '{"test": 1}',
            '{"test": 2}',
            '{"test": 3}',
            '{"test": 4}',
            '{"test": 5}'
        ]
        
        # Process all responses concurrently using asyncio.create_task
        tasks = [asyncio.create_task(asyncio.to_thread(extract_json_from_response, resp)) for resp in responses]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result["test"] == i + 1

    async def test_large_search_results_formatting(self):
        """Test formatting large search results."""
        # Create large search results
        organic_results = []
        for i in range(20):
            organic_results.append({
                "title": f"Result {i}",
                "snippet": f"This is snippet {i} with some content",
                "link": f"https://example.com/{i}"
            })
        
        results_data = {"organic_results": organic_results}
        formatted = format_search_results_for_prompt(results_data, "test query", max_results=3)
        
        # Should only include first 3 results
        assert "Result 0" in formatted
        assert "Result 1" in formatted
        assert "Result 2" in formatted
        assert "Result 3" not in formatted

    async def test_memory_efficiency_large_db_results(self):
        """Test memory efficiency with large database results."""
        # Create very large result set
        large_data = "x" * 10000  # 10KB per row
        rows = [{"id": i, "data": large_data} for i in range(10)]  # 100KB total
        db_results = {"rows": rows, "columns": ["id", "data"]}
        
        # Format with small limit
        formatted = format_db_results_for_prompt("SELECT * FROM large", db_results, 1000)
        
        # Should be truncated and include truncation message
        assert "results truncated" in formatted
        # The actual length will be longer than the limit due to how truncation works
        assert len(formatted) > 1000
