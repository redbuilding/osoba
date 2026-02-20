import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from main import app

client = TestClient(app)


class TestHeartbeatAPI:
    """Test heartbeat API endpoints."""

    @patch('api.heartbeat.get_insights')
    def test_get_insights_success(self, mock_get_insights):
        """Test getting insights successfully."""
        mock_get_insights.return_value = [
            {
                "_id": "123",
                "title": "Test Insight",
                "description": "Test description",
                "dismissed": False
            }
        ]
        
        response = client.get("/api/heartbeat/insights?user_id=default")
        
        assert response.status_code == 200
        data = response.json()
        assert "insights" in data
        assert len(data["insights"]) == 1
        assert data["insights"][0]["title"] == "Test Insight"

    @patch('api.heartbeat.get_insights')
    def test_get_insights_with_filters(self, mock_get_insights):
        """Test getting insights with filters."""
        mock_get_insights.return_value = []
        
        response = client.get("/api/heartbeat/insights?user_id=test&dismissed=true")
        
        assert response.status_code == 200
        mock_get_insights.assert_called_once()

    @patch('api.heartbeat.dismiss_insight')
    def test_dismiss_insight_success(self, mock_dismiss):
        """Test dismissing an insight successfully."""
        mock_dismiss.return_value = True
        
        response = client.post("/api/heartbeat/insights/123/dismiss?user_id=default")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    @patch('api.heartbeat.dismiss_insight')
    def test_dismiss_insight_not_found(self, mock_dismiss):
        """Test dismissing non-existent insight."""
        mock_dismiss.return_value = False
        
        response = client.post("/api/heartbeat/insights/999/dismiss?user_id=default")
        
        assert response.status_code == 404

    @patch('api.heartbeat.get_user_profile')
    def test_get_config_with_profile(self, mock_get_profile):
        """Test getting config with existing profile."""
        mock_get_profile.return_value = {
            "heartbeat_config": {
                "enabled": True,
                "interval": "1h"
            }
        }
        
        response = client.get("/api/heartbeat/config?user_id=default")
        
        assert response.status_code == 200
        data = response.json()
        assert "config" in data
        assert data["config"]["enabled"] is True
        assert data["config"]["interval"] == "1h"

    @patch('api.heartbeat.get_user_profile')
    def test_get_config_no_profile(self, mock_get_profile):
        """Test getting config with no profile returns defaults."""
        mock_get_profile.return_value = None
        
        response = client.get("/api/heartbeat/config?user_id=default")
        
        assert response.status_code == 200
        data = response.json()
        assert "config" in data
        assert data["config"]["enabled"] is True
        assert data["config"]["interval"] == "2h"

    @patch('api.heartbeat.upsert_user_profile')
    @patch('api.heartbeat.get_user_profile')
    def test_update_config_success(self, mock_get_profile, mock_upsert):
        """Test updating config successfully."""
        mock_get_profile.return_value = {
            "heartbeat_config": {"enabled": True}
        }
        mock_upsert.return_value = {"heartbeat_config": {"enabled": False}}
        
        response = client.put(
            "/api/heartbeat/config?user_id=default",
            json={"enabled": False}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    @patch('api.heartbeat.get_user_profile')
    def test_update_config_no_profile(self, mock_get_profile):
        """Test updating config with no profile."""
        mock_get_profile.return_value = None
        
        response = client.put(
            "/api/heartbeat/config?user_id=default",
            json={"enabled": False}
        )
        
        assert response.status_code == 404

    @patch('api.heartbeat.heartbeat_service.run_heartbeat')
    @pytest.mark.asyncio
    async def test_trigger_heartbeat(self, mock_run):
        """Test manually triggering heartbeat."""
        mock_run.return_value = None
        
        response = client.post("/api/heartbeat/trigger?user_id=default")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
