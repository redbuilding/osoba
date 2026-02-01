import React, { useState, useEffect } from 'react';
import { X, Plus, Trash2, Save, AlertCircle } from 'lucide-react';

const ProfileForm = ({ profile, onSave, onCancel, isLoading }) => {
  const [formData, setFormData] = useState({
    name: '',
    communication_style: 'professional',
    expertise_areas: []
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
        expertise_areas: profile.expertise_areas || []
      });
    } else {
      setFormData({
        name: '',
        communication_style: 'professional',
        expertise_areas: []
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
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900">
          {profile ? 'Edit Profile' : 'Create New Profile'}
        </h3>
        <button
          onClick={onCancel}
          className="text-gray-400 hover:text-gray-600"
          disabled={isLoading}
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Profile Name */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Profile Name *
          </label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => handleInputChange('name', e.target.value)}
            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              errors.name ? 'border-red-300' : 'border-gray-300'
            }`}
            placeholder="e.g., Technical Assistant, Creative Helper"
            maxLength={100}
            disabled={isLoading}
          />
          {errors.name && (
            <div className="mt-1 flex items-center text-sm text-red-600">
              <AlertCircle className="w-4 h-4 mr-1" />
              {errors.name}
            </div>
          )}
          <div className="mt-1 text-xs text-gray-500">
            {formData.name.length}/100 characters
          </div>
        </div>

        {/* Communication Style */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Communication Style
          </label>
          <select
            value={formData.communication_style}
            onChange={(e) => handleInputChange('communication_style', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isLoading}
          >
            {communicationStyles.map((style) => (
              <option key={style.value} value={style.value}>
                {style.label}
              </option>
            ))}
          </select>
          <div className="mt-1 text-sm text-gray-600">
            {communicationStyles.find(s => s.value === formData.communication_style)?.description}
          </div>
        </div>

        {/* Expertise Areas */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Expertise Areas (Optional)
          </label>
          
          {/* Add new expertise area */}
          <div className="flex space-x-2 mb-3">
            <input
              type="text"
              value={newExpertiseArea}
              onChange={(e) => setNewExpertiseArea(e.target.value)}
              onKeyPress={handleKeyPress}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., AI, Programming, Writing"
              disabled={isLoading || formData.expertise_areas.length >= 5}
            />
            <button
              type="button"
              onClick={addExpertiseArea}
              disabled={!newExpertiseArea.trim() || formData.expertise_areas.length >= 5 || isLoading}
              className="px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>

          {/* Current expertise areas */}
          {formData.expertise_areas.length > 0 && (
            <div className="space-y-2">
              {formData.expertise_areas.map((area, index) => (
                <div key={index} className="flex items-center justify-between bg-gray-50 px-3 py-2 rounded-md">
                  <span className="text-sm text-gray-700">{area}</span>
                  <button
                    type="button"
                    onClick={() => removeExpertiseArea(index)}
                    className="text-gray-400 hover:text-red-600"
                    disabled={isLoading}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {errors.expertise_areas && (
            <div className="mt-1 flex items-center text-sm text-red-600">
              <AlertCircle className="w-4 h-4 mr-1" />
              {errors.expertise_areas}
            </div>
          )}
          
          <div className="mt-1 text-xs text-gray-500">
            {formData.expertise_areas.length}/5 areas added
          </div>
        </div>

        {/* Form Actions */}
        <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
            disabled={isLoading}
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isLoading}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-blue-400 flex items-center space-x-2"
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
