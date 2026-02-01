import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from bson import ObjectId

from db.profiles_crud import (
    get_user_profiles, get_profile_by_id, get_active_profile,
    create_profile, update_profile, delete_profile, set_active_profile,
    MAX_PROFILES_PER_USER
)

class TestProfilesCRUD:
    
    @patch('db.profiles_crud.get_profiles_collection')
    def test_get_user_profiles_success(self, mock_get_collection):
        # Setup
        mock_collection = Mock()
        mock_get_collection.return_value = mock_collection
        
        mock_profiles = [
            {"_id": ObjectId(), "name": "Test Profile", "user_id": "test_user"},
            {"_id": ObjectId(), "name": "Another Profile", "user_id": "test_user"}
        ]
        mock_cursor = Mock()
        mock_cursor.sort.return_value = mock_profiles
        mock_collection.find.return_value = mock_cursor
        
        # Execute
        result = get_user_profiles("test_user")
        
        # Assert
        assert len(result) == 2
        assert all("_id" in profile for profile in result)
        mock_collection.find.assert_called_once_with({"user_id": "test_user"})
        mock_cursor.sort.assert_called_once_with("created_at", -1)

    @patch('db.profiles_crud.get_profiles_collection')
    def test_get_user_profiles_error(self, mock_get_collection):
        # Setup
        mock_get_collection.side_effect = Exception("Database error")
        
        # Execute
        result = get_user_profiles("test_user")
        
        # Assert
        assert result == []

    @patch('db.profiles_crud.get_profiles_collection')
    def test_get_profile_by_id_success(self, mock_get_collection):
        # Setup
        mock_collection = Mock()
        mock_get_collection.return_value = mock_collection
        
        profile_id = str(ObjectId())
        mock_profile = {"_id": ObjectId(profile_id), "name": "Test Profile", "user_id": "test_user"}
        mock_collection.find_one.return_value = mock_profile
        
        # Execute
        result = get_profile_by_id(profile_id, "test_user")
        
        # Assert
        assert result is not None
        assert result["name"] == "Test Profile"
        assert "_id" in result
        mock_collection.find_one.assert_called_once()

    @patch('db.profiles_crud.get_profiles_collection')
    def test_get_profile_by_id_invalid_id(self, mock_get_collection):
        # Execute
        result = get_profile_by_id("invalid_id", "test_user")
        
        # Assert
        assert result is None

    @patch('db.profiles_crud.get_profiles_collection')
    def test_get_active_profile_success(self, mock_get_collection):
        # Setup
        mock_collection = Mock()
        mock_get_collection.return_value = mock_collection
        
        mock_profile = {"_id": ObjectId(), "name": "Active Profile", "is_active": True, "user_id": "test_user"}
        mock_collection.find_one.return_value = mock_profile
        
        # Execute
        result = get_active_profile("test_user")
        
        # Assert
        assert result is not None
        assert result["name"] == "Active Profile"
        mock_collection.find_one.assert_called_once_with({"user_id": "test_user", "is_active": True})

    @patch('db.profiles_crud.get_profiles_collection')
    def test_create_profile_success(self, mock_get_collection):
        # Setup
        mock_collection = Mock()
        mock_get_collection.return_value = mock_collection
        
        # Mock profile count check
        mock_collection.count_documents.return_value = 1  # Under limit
        
        # Mock name uniqueness check
        mock_collection.find_one.return_value = None  # No existing profile with same name
        
        # Mock insert result
        mock_result = Mock()
        mock_result.inserted_id = ObjectId()
        mock_collection.insert_one.return_value = mock_result
        
        profile_data = {
            "name": "New Profile",
            "communication_style": "professional",
            "expertise_areas": ["AI", "Technology"]
        }
        
        # Execute
        result = create_profile(profile_data, "test_user")
        
        # Assert
        assert result is not None
        assert isinstance(result, str)
        mock_collection.count_documents.assert_called_once_with({"user_id": "test_user"})
        mock_collection.insert_one.assert_called_once()

    @patch('db.profiles_crud.get_profiles_collection')
    def test_create_profile_limit_exceeded(self, mock_get_collection):
        # Setup
        mock_collection = Mock()
        mock_get_collection.return_value = mock_collection
        
        # Mock profile count at limit
        mock_collection.count_documents.return_value = MAX_PROFILES_PER_USER
        
        profile_data = {
            "name": "New Profile",
            "communication_style": "professional",
            "expertise_areas": []
        }
        
        # Execute
        result = create_profile(profile_data, "test_user")
        
        # Assert
        assert result is None

    @patch('db.profiles_crud.get_profiles_collection')
    def test_create_profile_name_exists(self, mock_get_collection):
        # Setup
        mock_collection = Mock()
        mock_get_collection.return_value = mock_collection
        
        # Mock profile count under limit
        mock_collection.count_documents.return_value = 1
        
        # Mock existing profile with same name
        mock_collection.find_one.return_value = {"_id": ObjectId(), "name": "Existing Profile"}
        
        profile_data = {
            "name": "Existing Profile",
            "communication_style": "professional",
            "expertise_areas": []
        }
        
        # Execute
        result = create_profile(profile_data, "test_user")
        
        # Assert
        assert result is None

    @patch('db.profiles_crud.get_profiles_collection')
    def test_update_profile_success(self, mock_get_collection):
        # Setup
        mock_collection = Mock()
        mock_get_collection.return_value = mock_collection
        
        profile_id = str(ObjectId())
        
        # Mock existing profile check
        mock_collection.find_one.side_effect = [
            {"_id": ObjectId(profile_id), "name": "Old Name"},  # First call: existing profile check
            None  # Second call: name conflict check (no conflict)
        ]
        
        # Mock update result
        mock_result = Mock()
        mock_result.modified_count = 1
        mock_collection.update_one.return_value = mock_result
        
        update_data = {"name": "New Name"}
        
        # Execute
        result = update_profile(profile_id, update_data, "test_user")
        
        # Assert
        assert result is True
        mock_collection.update_one.assert_called_once()

    @patch('db.profiles_crud.get_profiles_collection')
    def test_update_profile_not_found(self, mock_get_collection):
        # Setup
        mock_collection = Mock()
        mock_get_collection.return_value = mock_collection
        
        profile_id = str(ObjectId())
        
        # Mock profile not found
        mock_collection.find_one.return_value = None
        
        update_data = {"name": "New Name"}
        
        # Execute
        result = update_profile(profile_id, update_data, "test_user")
        
        # Assert
        assert result is False

    @patch('db.profiles_crud.get_profiles_collection')
    def test_delete_profile_success(self, mock_get_collection):
        # Setup
        mock_collection = Mock()
        mock_get_collection.return_value = mock_collection
        
        profile_id = str(ObjectId())
        
        # Mock delete result
        mock_result = Mock()
        mock_result.deleted_count = 1
        mock_collection.delete_one.return_value = mock_result
        
        # Execute
        result = delete_profile(profile_id, "test_user")
        
        # Assert
        assert result is True
        mock_collection.delete_one.assert_called_once_with({
            "_id": ObjectId(profile_id),
            "user_id": "test_user"
        })

    @patch('db.profiles_crud.get_profiles_collection')
    def test_set_active_profile_success(self, mock_get_collection):
        # Setup
        mock_collection = Mock()
        mock_get_collection.return_value = mock_collection
        
        profile_id = str(ObjectId())
        
        # Mock update results
        mock_result = Mock()
        mock_result.modified_count = 1
        mock_collection.update_many.return_value = mock_result
        mock_collection.update_one.return_value = mock_result
        
        # Execute
        result = set_active_profile(profile_id, "test_user")
        
        # Assert
        assert result is True
        # Should deactivate all profiles first
        mock_collection.update_many.assert_called_once()
        # Then activate the specified profile
        mock_collection.update_one.assert_called_once()

    @patch('db.profiles_crud.get_profiles_collection')
    def test_set_active_profile_deactivate_all(self, mock_get_collection):
        # Setup
        mock_collection = Mock()
        mock_get_collection.return_value = mock_collection
        
        # Mock update result
        mock_result = Mock()
        mock_result.modified_count = 1
        mock_collection.update_many.return_value = mock_result
        
        # Execute (None means deactivate all)
        result = set_active_profile(None, "test_user")
        
        # Assert
        assert result is True
        # Should only deactivate all profiles
        mock_collection.update_many.assert_called_once()
        mock_collection.update_one.assert_not_called()
