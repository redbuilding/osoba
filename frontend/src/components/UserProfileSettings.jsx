import React, { useState, useEffect } from 'react';
import { User, Briefcase, MessageCircle, Target, Settings, Save, Loader2 } from 'lucide-react';

const UserProfileSettings = ({ onProfileUpdate }) => {
  const [formData, setFormData] = useState({
    name: '',
    role: '',
    communication_style: 'professional',
    expertise_areas: [],
    current_projects: '',
    preferred_tools: []
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const communicationStyles = [
    { value: 'professional', label: 'Professional' },
    { value: 'friendly', label: 'Friendly' },
    { value: 'casual', label: 'Casual' },
    { value: 'technical', label: 'Technical' },
    { value: 'creative', label: 'Creative' },
    { value: 'supportive', label: 'Supportive' }
  ];

  const availableTools = [
    'Web Search', 'Database', 'YouTube', 'HubSpot', 'Python', 'Codex'
  ];

  useEffect(() => {
    fetchActiveProfile();
  }, []);

  const fetchActiveProfile = async () => {
    try {
      setIsLoading(true);
      // TODO: Implement API call to get active profile
      // const response = await getActiveProfile();
      // setFormData(response.profile || {});
    } catch (err) {
      console.error('Error fetching profile:', err);
      setError('Failed to load profile');
    } finally {
      setIsLoading(false);
    }
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
    setError('');
    setSuccess('');
  };

  const handleArrayInputChange = (field, value) => {
    const items = value.split(',').map(item => item.trim()).filter(item => item);
    setFormData(prev => ({
      ...prev,
      [field]: items
    }));
  };

  const handleToolToggle = (tool) => {
    setFormData(prev => ({
      ...prev,
      preferred_tools: prev.preferred_tools.includes(tool)
        ? prev.preferred_tools.filter(t => t !== tool)
        : [...prev.preferred_tools, tool]
    }));
  };

  const handleSave = async () => {
    try {
      setIsLoading(true);
      setError('');
      
      // TODO: Implement API call to save profile
      // await saveUserProfile(formData);
      
      setSuccess('Profile saved successfully!');
      if (onProfileUpdate) {
        onProfileUpdate(formData);
      }
    } catch (err) {
      console.error('Error saving profile:', err);
      setError('Failed to save profile');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-2 mb-4">
        <User className="w-5 h-5 text-brand-purple" />
        <h3 className="text-lg font-semibold text-brand-text-primary">User Profile</h3>
      </div>

      {error && (
        <div className="bg-red-900/20 border border-red-500 text-red-400 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {success && (
        <div className="bg-green-900/20 border border-green-500 text-green-400 px-4 py-3 rounded">
          {success}
        </div>
      )}

      <div className="space-y-4">
        {/* Name Field */}
        <div>
          <label className="block text-sm font-medium text-brand-text-secondary mb-2">
            <User className="w-4 h-4 inline mr-2" />
            Name
          </label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => handleInputChange('name', e.target.value)}
            placeholder="Your name or preferred assistant name"
            className="w-full bg-brand-surface-bg text-brand-text-secondary border border-gray-600 
                     focus:outline-none focus:ring-1 focus:ring-brand-purple rounded px-3 py-2"
          />
        </div>

        {/* Role Field */}
        <div>
          <label className="block text-sm font-medium text-brand-text-secondary mb-2">
            <Briefcase className="w-4 h-4 inline mr-2" />
            Role
          </label>
          <input
            type="text"
            value={formData.role}
            onChange={(e) => handleInputChange('role', e.target.value)}
            placeholder="e.g., Software Developer, Researcher, Student"
            className="w-full bg-brand-surface-bg text-brand-text-secondary border border-gray-600 
                     focus:outline-none focus:ring-1 focus:ring-brand-purple rounded px-3 py-2"
          />
        </div>

        {/* Communication Style */}
        <div>
          <label className="block text-sm font-medium text-brand-text-secondary mb-2">
            <MessageCircle className="w-4 h-4 inline mr-2" />
            Communication Style
          </label>
          <select
            value={formData.communication_style}
            onChange={(e) => handleInputChange('communication_style', e.target.value)}
            className="w-full bg-brand-surface-bg text-brand-text-secondary border border-gray-600 
                     focus:outline-none focus:ring-1 focus:ring-brand-purple rounded px-3 py-2"
          >
            {communicationStyles.map(style => (
              <option key={style.value} value={style.value}>
                {style.label}
              </option>
            ))}
          </select>
        </div>

        {/* Expertise Areas */}
        <div>
          <label className="block text-sm font-medium text-brand-text-secondary mb-2">
            <Settings className="w-4 h-4 inline mr-2" />
            Expertise Areas
          </label>
          <input
            type="text"
            value={formData.expertise_areas.join(', ')}
            onChange={(e) => handleArrayInputChange('expertise_areas', e.target.value)}
            placeholder="e.g., JavaScript, Machine Learning, Data Analysis (comma-separated)"
            className="w-full bg-brand-surface-bg text-brand-text-secondary border border-gray-600 
                     focus:outline-none focus:ring-1 focus:ring-brand-purple rounded px-3 py-2"
          />
          <p className="text-xs text-gray-400 mt-1">Maximum 5 areas, separated by commas</p>
        </div>

        {/* Current Projects */}
        <div>
          <label className="block text-sm font-medium text-brand-text-secondary mb-2">
            <Target className="w-4 h-4 inline mr-2" />
            Current Projects
          </label>
          <textarea
            value={formData.current_projects}
            onChange={(e) => handleInputChange('current_projects', e.target.value)}
            placeholder="Describe what you're currently working on..."
            rows={3}
            className="w-full bg-brand-surface-bg text-brand-text-secondary border border-gray-600 
                     focus:outline-none focus:ring-1 focus:ring-brand-purple rounded px-3 py-2"
          />
        </div>

        {/* Preferred Tools */}
        <div>
          <label className="block text-sm font-medium text-brand-text-secondary mb-2">
            Preferred Tools
          </label>
          <div className="grid grid-cols-2 gap-2">
            {availableTools.map(tool => (
              <label key={tool} className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.preferred_tools.includes(tool)}
                  onChange={() => handleToolToggle(tool)}
                  className="rounded border-gray-600 bg-brand-surface-bg text-brand-purple 
                           focus:ring-brand-purple focus:ring-1"
                />
                <span className="text-sm text-brand-text-secondary">{tool}</span>
              </label>
            ))}
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end pt-4">
        <button
          onClick={handleSave}
          disabled={isLoading}
          className="flex items-center space-x-2 bg-brand-purple text-white rounded-md 
                   hover:bg-brand-button-grad-to transition-colors duration-200 
                   focus:outline-none focus:ring-2 focus:ring-brand-blue px-4 py-2 disabled:opacity-50"
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Save className="w-4 h-4" />
          )}
          <span>{isLoading ? 'Saving...' : 'Save Profile'}</span>
        </button>
      </div>
    </div>
  );
};

export default UserProfileSettings;
