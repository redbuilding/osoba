import pytest
from unittest.mock import Mock, patch, AsyncMock
from services.profile_service import (
    generate_system_prompt, get_profiles_for_user, get_profile_by_id_service,
    get_active_profile_service, create_profile_service, update_profile_service,
    delete_profile_service, set_active_profile_service, get_system_prompt_for_user
)
from core.profile_models import ProfileCreatePayload, ProfileUpdatePayload

class TestProfileService:
    
    def test_generate_system_prompt_full_profile(self):
        # Setup
        profile_data = {
            "name": "Technical Assistant",
            "communication_style": "technical",
            "expertise_areas": ["AI", "Programming", "Data Science"]
        }
        
        # Execute
        result = generate_system_prompt(profile_data)
        
        # Assert
        assert "Technical Assistant" in result
        assert "technical communication style" in result
        assert "AI, Programming, Data Science" in result
        assert "precision and accuracy" in result  # Technical style instruction

    def test_generate_system_prompt_minimal_profile(self):
        # Setup
        profile_data = {
            "name": "Simple Assistant",
            "communication_style": "friendly",
            "expertise_areas": []
        }
        
        # Execute
        result = generate_system_prompt(profile_data)
        
        # Assert
        assert "Simple Assistant" in result
        assert "friendly communication style" in result
        assert "warm, approachable tone" in result  # Friendly style instruction
        assert "expertise" not in result.lower()  # No expertise areas

    def test_generate_system_prompt_empty_profile(self):
        # Setup
        profile_data = {}
        
        # Execute
        result = generate_system_prompt(profile_data)
        
        # Assert
        assert result == ""  # Empty profile should return empty string

    def test_generate_system_prompt_none_profile(self):
        # Execute
        result = generate_system_prompt(None)
        
        # Assert
        assert result == ""

    def test_generate_system_prompt_all_styles(self):
        # Test all communication styles have instructions
        styles = ["professional", "friendly", "casual", "technical", "creative", "supportive"]
        
        for style in styles:
            profile_data = {
                "name": "Test Assistant",
                "communication_style": style,
                "expertise_areas": []
            }
            
            result = generate_system_prompt(profile_data)
            
            # Each style should have specific instructions
            assert len(result) > 50  # Should have substantial content
            assert style in result

    @patch('services.profile_service.get_user_profiles')
    @pytest.mark.asyncio
    async def test_get_profiles_for_user_success(self, mock_get_profiles):
        # Setup
        mock_profiles = [
            {"_id": "1", "name": "Profile 1"},
            {"_id": "2", "name": "Profile 2"}
        ]
        mock_get_profiles.return_value = mock_profiles
        
        # Execute
        result = await get_profiles_for_user("test_user")
        
        # Assert
        assert result == mock_profiles
        mock_get_profiles.assert_called_once_with("test_user")

    @patch('services.profile_service.get_user_profiles')
    @pytest.mark.asyncio
    async def test_get_profiles_for_user_error(self, mock_get_profiles):
        # Setup
        mock_get_profiles.side_effect = Exception("Database error")
        
        # Execute
        result = await get_profiles_for_user("test_user")
        
        # Assert
        assert result == []

    @patch('services.profile_service.get_profile_by_id')
    @pytest.mark.asyncio
    async def test_get_profile_by_id_service_success(self, mock_get_profile):
        # Setup
        mock_profile = {"_id": "1", "name": "Test Profile"}
        mock_get_profile.return_value = mock_profile
        
        # Execute
        result = await get_profile_by_id_service("1", "test_user")
        
        # Assert
        assert result == mock_profile
        mock_get_profile.assert_called_once_with("1", "test_user")

    @patch('services.profile_service.get_active_profile')
    @pytest.mark.asyncio
    async def test_get_active_profile_service_success(self, mock_get_active):
        # Setup
        mock_profile = {"_id": "1", "name": "Active Profile", "is_active": True}
        mock_get_active.return_value = mock_profile
        
        # Execute
        result = await get_active_profile_service("test_user")
        
        # Assert
        assert result == mock_profile
        mock_get_active.assert_called_once_with("test_user")

    @patch('services.profile_service.create_profile')
    @pytest.mark.asyncio
    async def test_create_profile_service_success(self, mock_create):
        # Setup
        mock_create.return_value = "new_profile_id"
        payload = ProfileCreatePayload(
            name="New Profile",
            communication_style="professional",
            expertise_areas=["AI"]
        )
        
        # Execute
        result = await create_profile_service(payload, "test_user")
        
        # Assert
        assert result == "new_profile_id"
        mock_create.assert_called_once()

    @patch('services.profile_service.update_profile')
    @pytest.mark.asyncio
    async def test_update_profile_service_success(self, mock_update):
        # Setup
        mock_update.return_value = True
        payload = ProfileUpdatePayload(name="Updated Profile")
        
        # Execute
        result = await update_profile_service("profile_id", payload, "test_user")
        
        # Assert
        assert result is True
        mock_update.assert_called_once()

    @patch('services.profile_service.delete_profile')
    @pytest.mark.asyncio
    async def test_delete_profile_service_success(self, mock_delete):
        # Setup
        mock_delete.return_value = True
        
        # Execute
        result = await delete_profile_service("profile_id", "test_user")
        
        # Assert
        assert result is True
        mock_delete.assert_called_once_with("profile_id", "test_user")

    @patch('services.profile_service.set_active_profile')
    @pytest.mark.asyncio
    async def test_set_active_profile_service_success(self, mock_set_active):
        # Setup
        mock_set_active.return_value = True
        
        # Execute
        result = await set_active_profile_service("profile_id", "test_user")
        
        # Assert
        assert result is True
        mock_set_active.assert_called_once_with("profile_id", "test_user")

    @patch('services.profile_service.get_active_profile')
    @pytest.mark.asyncio
    async def test_get_system_prompt_for_user_with_active_profile(self, mock_get_active):
        # Setup
        mock_profile = {
            "name": "Test Assistant",
            "communication_style": "professional",
            "expertise_areas": ["AI"]
        }
        mock_get_active.return_value = mock_profile
        
        # Execute
        result = await get_system_prompt_for_user("test_user")
        
        # Assert
        assert "Test Assistant" in result
        assert "professional" in result
        mock_get_active.assert_called_once_with("test_user")

    @patch('services.profile_service.get_active_profile')
    @pytest.mark.asyncio
    async def test_get_system_prompt_for_user_no_active_profile(self, mock_get_active):
        # Setup
        mock_get_active.return_value = None
        
        # Execute
        result = await get_system_prompt_for_user("test_user")
        
        # Assert
        assert result == ""
        mock_get_active.assert_called_once_with("test_user")

    @patch('services.profile_service.get_active_profile')
    @pytest.mark.asyncio
    async def test_get_system_prompt_for_user_error(self, mock_get_active):
        # Setup
        mock_get_active.side_effect = Exception("Database error")
        
        # Execute
        result = await get_system_prompt_for_user("test_user")
        
        # Assert
        assert result == ""
