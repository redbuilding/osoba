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
    <div className="space-y-6 text-brand-text-primary">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold">AI Profiles</h2>
          <p className="text-brand-text-secondary mt-1">
            Create personalized AI assistants with custom communication styles and expertise areas.
          </p>
        </div>
        <button
          onClick={handleCreateProfile}
          disabled={profiles.length >= 3 || isLoading}
          className="flex items-center space-x-2 px-4 py-2 bg-brand-purple text-white rounded-md hover:bg-brand-button-grad-to disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-brand-purple"
        >
          <Plus className="w-4 h-4" />
          <span>New Profile</span>
        </button>
      </div>

      {/* Messages */}
      {error && (
        <div className="bg-brand-surface-bg border border-gray-700 rounded-md p-4">
          <div className="flex items-center">
            <AlertCircle className="w-5 h-5 text-brand-alert-red mr-2" />
            <span className="text-brand-alert-red">{error}</span>
          </div>
        </div>
      )}

      {success && (
        <div className="bg-brand-surface-bg border border-gray-700 rounded-md p-4">
          <div className="flex items-center">
            <div className="w-3 h-3 rounded-full bg-brand-success-green mr-2"></div>
            <span className="text-brand-success-green">{success}</span>
          </div>
        </div>
      )}

      {/* Profile Limit Info */}
      <div className="bg-brand-surface-bg border border-gray-700 rounded-md p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <User className="w-5 h-5 text-brand-text-secondary mr-2" />
            <span className="text-brand-text-secondary">
              {profiles.length}/3 profiles created
            </span>
          </div>
          {activeProfile ? (
            <button
              onClick={handleDeactivateAll}
              disabled={isLoading}
              className="text-sm text-brand-purple hover:text-brand-button-grad-to underline"
            >
              Use Default (No Profile)
            </button>
          ) : (
            <span className="text-sm text-brand-text-secondary">Using default behavior</span>
          )}
        </div>
      </div>

      {/* Profiles List */}
      {isLoading && profiles.length === 0 ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-brand-purple" />
          <span className="ml-2 text-brand-text-secondary">Loading profiles...</span>
        </div>
      ) : profiles.length === 0 ? (
        <div className="text-center py-12">
          <User className="w-12 h-12 text-brand-text-secondary mx-auto mb-4" />
          <h3 className="text-lg font-medium mb-2">No profiles yet</h3>
          <p className="text-brand-text-secondary mb-4">
            Create your first AI profile to get started with personalized conversations.
          </p>
          <button
            onClick={handleCreateProfile}
            className="inline-flex items-center space-x-2 px-4 py-2 bg-brand-purple text-white rounded-md hover:bg-brand-button-grad-to focus:outline-none focus:ring-2 focus:ring-brand-purple"
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
              className={`bg-brand-surface-bg border rounded-lg p-6 border-gray-700 ${
                profile.is_active ? 'ring-1 ring-brand-purple' : ''
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-2 mb-2">
                    <h3 className="text-lg font-semibold">
                      {profile.name}
                    </h3>
                    {profile.is_active && (
                      <div className="flex items-center space-x-1 px-2 py-0.5 bg-black/30 text-brand-text-secondary border border-gray-700 rounded-full text-xs">
                        <Star className="w-3 h-3 text-brand-purple" />
                        <span>Active</span>
                      </div>
                    )}
                  </div>
                  
                  <div className="space-y-2 text-sm text-brand-text-secondary">
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
                              className="px-2 py-1 bg-black/30 text-brand-text-secondary border border-gray-700 rounded text-xs"
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
                      className="p-2 text-brand-text-secondary hover:text-brand-purple hover:bg-gray-800 rounded focus:outline-none focus:ring-2 focus:ring-brand-purple"
                      title="Activate profile"
                    >
                      <Star className="w-4 h-4" />
                    </button>
                  )}
                  
                  <button
                    onClick={() => handleEditProfile(profile)}
                    disabled={isLoading}
                    className="p-2 text-brand-text-secondary hover:text-brand-text-primary hover:bg-gray-800 rounded focus:outline-none focus:ring-2 focus:ring-brand-purple"
                    title="Edit profile"
                  >
                    <Edit className="w-4 h-4" />
                  </button>
                  
                  <button
                    onClick={() => handleDeleteProfile(profile._id)}
                    disabled={isLoading}
                    className="p-2 text-brand-text-secondary hover:text-brand-alert-red hover:bg-gray-800 rounded focus:outline-none focus:ring-2 focus:ring-brand-purple"
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
