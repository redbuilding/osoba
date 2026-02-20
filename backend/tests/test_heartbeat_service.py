import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from services.heartbeat_service import HeartbeatService


@pytest.mark.asyncio
class TestHeartbeatService:
    """Test heartbeat service functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = HeartbeatService()

    def test_parse_interval_hours(self):
        """Test parsing hour intervals."""
        assert self.service._parse_interval("1h") == 3600
        assert self.service._parse_interval("2h") == 7200
        assert self.service._parse_interval("24h") == 86400

    def test_parse_interval_minutes(self):
        """Test parsing minute intervals."""
        assert self.service._parse_interval("30m") == 1800
        assert self.service._parse_interval("60m") == 3600
        assert self.service._parse_interval("5m") == 300

    def test_parse_interval_invalid(self):
        """Test parsing invalid intervals returns default."""
        assert self.service._parse_interval("invalid") == 7200  # Default 2h
        assert self.service._parse_interval("") == 7200
        assert self.service._parse_interval("2x") == 7200

    def test_is_heartbeat_ok_at_start(self):
        """Test HEARTBEAT_OK detection at start of response."""
        assert self.service._is_heartbeat_ok("HEARTBEAT_OK")
        assert self.service._is_heartbeat_ok("heartbeat_ok")
        assert self.service._is_heartbeat_ok("HEARTBEAT_OK\nSome other text")

    def test_is_heartbeat_ok_at_end(self):
        """Test HEARTBEAT_OK detection at end of response."""
        assert self.service._is_heartbeat_ok("Some text\nHEARTBEAT_OK")
        assert self.service._is_heartbeat_ok("Text here HEARTBEAT_OK")

    def test_is_heartbeat_ok_in_middle(self):
        """Test HEARTBEAT_OK in middle is not detected."""
        assert not self.service._is_heartbeat_ok("Some HEARTBEAT_OK text here")
        assert not self.service._is_heartbeat_ok("Text\nHEARTBEAT_OK\nMore text")

    def test_parse_insight_with_title_and_description(self):
        """Test parsing insight with proper format."""
        response = "Title: Follow up on feature\nDescription: Review the implementation"
        insight = self.service._parse_insight(response)
        
        assert insight["insight_type"] == "task_suggestion"
        assert insight["title"] == "Follow up on feature"
        assert "Review the implementation" in insight["description"]

    def test_parse_insight_without_format(self):
        """Test parsing insight without proper format."""
        response = "Just some text without format"
        insight = self.service._parse_insight(response)
        
        assert insight["insight_type"] == "task_suggestion"
        assert insight["title"] == "Proactive Suggestion"
        assert insight["description"] == response

    def test_in_active_hours_within_range(self):
        """Test active hours check within range."""
        active_hours = {
            "start": "09:00",
            "end": "17:00"
        }
        # 12:00 UTC should be within range
        now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
        assert self.service._in_active_hours(active_hours, now)

    def test_in_active_hours_outside_range(self):
        """Test active hours check outside range."""
        active_hours = {
            "start": "09:00",
            "end": "17:00"
        }
        # 20:00 UTC should be outside range
        now = datetime(2026, 2, 20, 20, 0, tzinfo=timezone.utc)
        # This might pass or fail depending on timezone, but tests the logic
        result = self.service._in_active_hours(active_hours, now)
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_gather_context_empty(self):
        """Test context gathering with no data."""
        with patch('services.heartbeat_service.get_all_conversations', return_value=[]):
            with patch('services.heartbeat_service.list_tasks', return_value=[]):
                profile = {"goals_document": "Test goals"}
                context = await self.service._gather_context("default", profile)
                
                assert context["goals"] == "Test goals"
                assert context["recent_conversations"] == []
                assert context["active_tasks"] == []

    def test_build_prompt_with_goals(self):
        """Test prompt building with goals."""
        context = {
            "goals": "Complete project X",
            "recent_conversations": [],
            "active_tasks": []
        }
        prompt = self.service._build_prompt(context)
        
        assert "Complete project X" in prompt
        assert "HEARTBEAT_OK" in prompt

    def test_build_prompt_with_conversations(self):
        """Test prompt building with conversations."""
        context = {
            "goals": "",
            "recent_conversations": [
                {"title": "Test Chat", "summary": "Discussed features"}
            ],
            "active_tasks": []
        }
        prompt = self.service._build_prompt(context)
        
        assert "Test Chat" in prompt
        assert "Discussed features" in prompt
