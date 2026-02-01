import React, { useState, useEffect } from 'react';
import { Plus, Edit, Trash2, User, Star, AlertCircle, Loader2 } from 'lucide-react';
import ProfileForm from './ProfileForm';
import { 
  getProfiles, 
  createProfile, 
  updateProfile, 
  deleteProfile, 
  activateProfile, 
  deactivateAllProfiles 
} from '../services/api';

const ProfileManager = () => {
  const [profiles, setProfiles] = useState([]);
  const [activeProfile, setActiveProfile] = useState(null);
  const [editingProfile, setEditingProfile] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    fetchProfiles();
  }, []);

  const fetchProfiles = async () => {
    try {
      setIsLoading(true);
      const data = await getProfiles();
      setProfiles(data.profiles || []);
      
      // Find active profile
      const active = data.profiles?.find(p => p.is_active);
      setActiveProfile(active || null);
    } catch (err) {
      console.error('Error fetching profiles:', err);
      setError('Failed to load profiles');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateProfile = () => {
    if (profiles.length >= 3) {
      setError('Maximum 3 profiles allowed');
      return;
    }
    setEditingProfile(null);
    setShowForm(true);
    setError('');
  };

  const handleEditProfile = (profile) => {
    setEditingProfile(profile);
    setShowForm(true);
    setError('');
  };

  const handleSaveProfile = async (formData) => {
    try {
      setIsLoading(true);
      setError('');
      
      let result;
      if (editingProfile) {
        result = await updateProfile(editingProfile._id, formData);
      } else {
        result = await createProfile(formData);
      }
      
      if (result.success) {
        setSuccess(editingProfile ? 'Profile updated successfully' : 'Profile created successfully');
        setShowForm(false);
        setEditingProfile(null);
        await fetchProfiles();
        
        // Clear success message after 3 seconds
        setTimeout(() => setSuccess(''), 3000);
      } else {
        setError(result.message || 'Failed to save profile');
      }
    } catch (err) {
      console.error('Error saving profile:', err);
      setError('Failed to save profile');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteProfile = async (profileId) => {
    if (!confirm('Are you sure you want to delete this profile?')) {
      return;
    }
    
    try {
      setIsLoading(true);
      setError('');
      
      const result = await deleteProfile(profileId);
      if (result.success) {
        setSuccess('Profile deleted successfully');
        await fetchProfiles();
        
        // Clear success message after 3 seconds
        setTimeout(() => setSuccess(''), 3000);
      } else {
        setError(result.message || 'Failed to delete profile');
      }
    } catch (err) {
      console.error('Error deleting profile:', err);
      setError('Failed to delete profile');
    } finally {
      setIsLoading(false);
    }
  };

  const handleActivateProfile = async (profileId) => {
    try {
      setIsLoading(true);
      setError('');
      
      const result = await activateProfile(profileId);
      if (result.success) {
        setSuccess('Profile activated successfully');
        await fetchProfiles();
        
        // Clear success message after 3 seconds
        setTimeout(() => setSuccess(''), 3000);
      } else {
        setError(result.message || 'Failed to activate profile');
      }
    } catch (err) {
      console.error('Error activating profile:', err);
      setError('Failed to activate profile');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeactivateAll = async () => {
    try {
      setIsLoading(true);
      setError('');
      
      const result = await deactivateAllProfiles();
      if (result.success) {
        setSuccess('All profiles deactivated - using default behavior');
        await fetchProfiles();
        
        // Clear success message after 3 seconds
        setTimeout(() => setSuccess(''), 3000);
      } else {
        setError(result.message || 'Failed to deactivate profiles');
      }
    } catch (err) {
      console.error('Error deactivating profiles:', err);
      setError('Failed to deactivate profiles');
    } finally {
      setIsLoading(false);
    }
  };

  const getCommunicationStyleLabel = (style) => {
    const styles = {
      professional: 'Professional',
      friendly: 'Friendly',
      casual: 'Casual',
      technical: 'Technical',
      creative: 'Creative',
      supportive: 'Supportive'
    };
    return styles[style] || style;
  };

  if (showForm) {
    return (
      <ProfileForm
        profile={editingProfile}
        onSave={handleSaveProfile}
        onCancel={() => {
          setShowForm(false);
          setEditingProfile(null);
          setError('');
        }}
        isLoading={isLoading}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">AI Profiles</h2>
          <p className="text-gray-600 mt-1">
            Create personalized AI assistants with custom communication styles and expertise areas.
          </p>
        </div>
        <button
          onClick={handleCreateProfile}
          disabled={profiles.length >= 3 || isLoading}
          className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          <Plus className="w-4 h-4" />
          <span>New Profile</span>
        </button>
      </div>

      {/* Messages */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex items-center">
            <AlertCircle className="w-5 h-5 text-red-600 mr-2" />
            <span className="text-red-800">{error}</span>
          </div>
        </div>
      )}

      {success && (
        <div className="bg-green-50 border border-green-200 rounded-md p-4">
          <div className="flex items-center">
            <div className="w-5 h-5 bg-green-600 rounded-full flex items-center justify-center mr-2">
              <div className="w-2 h-2 bg-white rounded-full"></div>
            </div>
            <span className="text-green-800">{success}</span>
          </div>
        </div>
      )}

      {/* Profile Limit Info */}
      <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <User className="w-5 h-5 text-blue-600 mr-2" />
            <span className="text-blue-800">
              {profiles.length}/3 profiles created
            </span>
          </div>
          {activeProfile ? (
            <button
              onClick={handleDeactivateAll}
              disabled={isLoading}
              className="text-sm text-blue-600 hover:text-blue-800 underline"
            >
              Use Default (No Profile)
            </button>
          ) : (
            <span className="text-sm text-blue-600">Using default behavior</span>
          )}
        </div>
      </div>

      {/* Profiles List */}
      {isLoading && profiles.length === 0 ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
          <span className="ml-2 text-gray-600">Loading profiles...</span>
        </div>
      ) : profiles.length === 0 ? (
        <div className="text-center py-12">
          <User className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No profiles yet</h3>
          <p className="text-gray-600 mb-4">
            Create your first AI profile to get started with personalized conversations.
          </p>
          <button
            onClick={handleCreateProfile}
            className="inline-flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            <Plus className="w-4 h-4" />
            <span>Create Profile</span>
          </button>
        </div>
      ) : (
        <div className="grid gap-4">
          {profiles.map((profile) => (
            <div
              key={profile._id}
              className={`bg-white border rounded-lg p-6 ${
                profile.is_active ? 'border-blue-300 bg-blue-50' : 'border-gray-200'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-2 mb-2">
                    <h3 className="text-lg font-semibold text-gray-900">
                      {profile.name}
                    </h3>
                    {profile.is_active && (
                      <div className="flex items-center space-x-1 px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs">
                        <Star className="w-3 h-3" />
                        <span>Active</span>
                      </div>
                    )}
                  </div>
                  
                  <div className="space-y-2 text-sm text-gray-600">
                    <div>
                      <span className="font-medium">Style:</span> {getCommunicationStyleLabel(profile.communication_style)}
                    </div>
                    
                    {profile.expertise_areas && profile.expertise_areas.length > 0 && (
                      <div>
                        <span className="font-medium">Expertise:</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {profile.expertise_areas.map((area, index) => (
                            <span
                              key={index}
                              className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs"
                            >
                              {area}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
                
                <div className="flex items-center space-x-2 ml-4">
                  {!profile.is_active && (
                    <button
                      onClick={() => handleActivateProfile(profile._id)}
                      disabled={isLoading}
                      className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded"
                      title="Activate profile"
                    >
                      <Star className="w-4 h-4" />
                    </button>
                  )}
                  
                  <button
                    onClick={() => handleEditProfile(profile)}
                    disabled={isLoading}
                    className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-50 rounded"
                    title="Edit profile"
                  >
                    <Edit className="w-4 h-4" />
                  </button>
                  
                  <button
                    onClick={() => handleDeleteProfile(profile._id)}
                    disabled={isLoading}
                    className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded"
                    title="Delete profile"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ProfileManager;
