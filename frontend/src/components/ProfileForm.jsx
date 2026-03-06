import React, { useState, useEffect } from 'react';
import { X, Plus, Trash2, Save, AlertCircle } from 'lucide-react';

const ProfileForm = ({ profile, onSave, onCancel, isLoading }) => {
  const [formData, setFormData] = useState({
    name: '',
    communication_style: 'professional',
    expertise_areas: [],
    backstory: ''
  });
  const [newExpertiseArea, setNewExpertiseArea] = useState('');
  const [errors, setErrors] = useState({});

  const communicationStyles = [
    { value: 'professional', label: 'Professional', description: 'Formal, business-appropriate tone' },
    { value: 'friendly', label: 'Friendly', description: 'Warm, approachable conversation' },
    { value: 'casual', label: 'Casual', description: 'Relaxed, informal interaction' },
    { value: 'technical', label: 'Technical', description: 'Precise, detail-oriented responses' },
    { value: 'creative', label: 'Creative', description: 'Imaginative, innovative thinking' },
    { value: 'supportive', label: 'Supportive', description: 'Empathetic, encouraging guidance' }
  ];

  useEffect(() => {
    if (profile) {
      setFormData({
        name: profile.name || '',
        communication_style: profile.communication_style || 'professional',
        expertise_areas: profile.expertise_areas || [],
        backstory: profile.backstory || ''
      });
    } else {
      setFormData({
        name: '',
        communication_style: 'professional',
        expertise_areas: [],
        backstory: ''
      });
    }
    setErrors({});
  }, [profile]);

  const validateForm = () => {
    const newErrors = {};
    
    if (!formData.name.trim()) {
      newErrors.name = 'Profile name is required';
    } else if (formData.name.length > 100) {
      newErrors.name = 'Profile name must be 100 characters or less';
    }
    
    if (formData.expertise_areas.length > 5) {
      newErrors.expertise_areas = 'Maximum 5 expertise areas allowed';
    }

    if (formData.backstory && formData.backstory.length > 1000) {
      newErrors.backstory = 'Backstory must be 1000 characters or less';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (validateForm()) {
      onSave(formData);
    }
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
    
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({
        ...prev,
        [field]: undefined
      }));
    }
  };

  const addExpertiseArea = () => {
    const area = newExpertiseArea.trim();
    if (area && !formData.expertise_areas.includes(area) && formData.expertise_areas.length < 5) {
      setFormData(prev => ({
        ...prev,
        expertise_areas: [...prev.expertise_areas, area]
      }));
      setNewExpertiseArea('');
    }
  };

  const removeExpertiseArea = (index) => {
    setFormData(prev => ({
      ...prev,
      expertise_areas: prev.expertise_areas.filter((_, i) => i !== index)
    }));
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addExpertiseArea();
    }
  };

  return (
    <div className="bg-brand-surface-bg rounded-lg border border-gray-700 p-6 text-brand-text-primary">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold">
          {profile ? 'Edit Profile' : 'Create New Profile'}
        </h3>
        <button
          onClick={onCancel}
          className="text-brand-text-secondary hover:text-brand-text-primary focus:outline-none focus:ring-2 focus:ring-brand-purple rounded"
          disabled={isLoading}
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Profile Name */}
        <div>
          <label className="block text-sm font-medium text-brand-text-secondary mb-2">
            Profile Name *
          </label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => handleInputChange('name', e.target.value)}
            className={`w-full px-3 py-2 border rounded-md bg-brand-main-bg text-brand-text-primary placeholder-brand-text-secondary focus:outline-none focus:ring-2 focus:ring-brand-purple ${
              errors.name ? 'border-red-600' : 'border-gray-700'
            }`}
            placeholder="e.g., Technical Assistant, Creative Helper"
            maxLength={100}
            disabled={isLoading}
          />
          {errors.name && (
            <div className="mt-1 flex items-center text-sm text-brand-alert-red">
              <AlertCircle className="w-4 h-4 mr-1" />
              {errors.name}
            </div>
          )}
          <div className="mt-1 text-xs text-brand-text-secondary">
            {formData.name.length}/100 characters
          </div>
        </div>

        {/* Communication Style */}
        <div>
          <label className="block text-sm font-medium text-brand-text-secondary mb-2">
            Communication Style
          </label>
          <select
            value={formData.communication_style}
            onChange={(e) => handleInputChange('communication_style', e.target.value)}
            className="w-full px-3 py-2 border border-gray-700 rounded-md bg-brand-main-bg text-brand-text-primary focus:outline-none focus:ring-2 focus:ring-brand-purple"
            disabled={isLoading}
          >
            {communicationStyles.map((style) => (
              <option key={style.value} value={style.value}>
                {style.label}
              </option>
            ))}
          </select>
          <div className="mt-1 text-sm text-brand-text-secondary">
            {communicationStyles.find(s => s.value === formData.communication_style)?.description}
          </div>
        </div>

        {/* Expertise Areas */}
        <div>
          <label className="block text-sm font-medium text-brand-text-secondary mb-2">
            Expertise Areas (Optional)
          </label>
          
          {/* Add new expertise area */}
          <div className="flex space-x-2 mb-3">
            <input
              type="text"
              value={newExpertiseArea}
              onChange={(e) => setNewExpertiseArea(e.target.value)}
              onKeyPress={handleKeyPress}
              className="flex-1 px-3 py-2 border border-gray-700 rounded-md bg-brand-main-bg text-brand-text-primary placeholder-brand-text-secondary focus:outline-none focus:ring-2 focus:ring-brand-purple"
              placeholder="e.g., AI, Programming, Writing"
              disabled={isLoading || formData.expertise_areas.length >= 5}
            />
            <button
              type="button"
              onClick={addExpertiseArea}
              disabled={!newExpertiseArea.trim() || formData.expertise_areas.length >= 5 || isLoading}
              className="px-3 py-2 bg-brand-purple text-white rounded-md hover:bg-brand-button-grad-to disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-brand-purple"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>

          {/* Current expertise areas */}
          {formData.expertise_areas.length > 0 && (
            <div className="space-y-2">
              {formData.expertise_areas.map((area, index) => (
                <div key={index} className="flex items-center justify-between bg-black/30 border border-gray-700 px-3 py-2 rounded-md">
                  <span className="text-sm text-brand-text-secondary">{area}</span>
                  <button
                    type="button"
                    onClick={() => removeExpertiseArea(index)}
                    className="text-brand-text-secondary hover:text-brand-alert-red focus:outline-none focus:ring-2 focus:ring-brand-purple rounded"
                    disabled={isLoading}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {errors.expertise_areas && (
            <div className="mt-1 flex items-center text-sm text-brand-alert-red">
              <AlertCircle className="w-4 h-4 mr-1" />
              {errors.expertise_areas}
            </div>
          )}
          
          <div className="mt-1 text-xs text-brand-text-secondary">
            {formData.expertise_areas.length}/5 areas added
          </div>
        </div>

        {/* Backstory */}
        <div>
          <label className="block text-sm font-medium text-brand-text-secondary mb-2">
            Persona Backstory (Optional)
          </label>
          <textarea
            value={formData.backstory}
            onChange={(e) => handleInputChange('backstory', e.target.value)}
            className={`w-full px-3 py-2 border rounded-md bg-brand-main-bg text-brand-text-primary placeholder-brand-text-secondary focus:outline-none focus:ring-2 focus:ring-brand-purple resize-none ${
              errors.backstory ? 'border-red-600' : 'border-gray-700'
            }`}
            placeholder="e.g., A seasoned startup founder who spent 10 years in Silicon Valley before moving to focus on meaningful work. Passionate about clear thinking and helping others cut through complexity."
            rows={4}
            maxLength={1000}
            disabled={isLoading}
          />
          {errors.backstory && (
            <div className="mt-1 flex items-center text-sm text-brand-alert-red">
              <AlertCircle className="w-4 h-4 mr-1" />
              {errors.backstory}
            </div>
          )}
          <div className="mt-1 text-xs text-brand-text-secondary">
            {(formData.backstory || '').length}/1000 characters · This shapes the persona's character and how it relates to you in conversation.
          </div>
        </div>

        {/* Form Actions */}
        <div className="flex justify-end space-x-3 pt-4 border-t border-gray-700">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 text-brand-text-secondary bg-gray-700 rounded-md hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-brand-purple"
            disabled={isLoading}
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isLoading}
            className="px-4 py-2 bg-brand-purple text-white rounded-md hover:bg-brand-button-grad-to disabled:opacity-50 flex items-center space-x-2 focus:outline-none focus:ring-2 focus:ring-brand-purple"
          >
            <Save className="w-4 h-4" />
            <span>{isLoading ? 'Saving...' : 'Save Profile'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};

export default ProfileForm;
