import React, { useState, useEffect } from 'react';
import { X, Eye, EyeOff, Check, AlertCircle, Loader2 } from 'lucide-react';
import { 
  getProviders, 
  getUserSettings, 
  saveProviderSettings, 
  removeProviderSettings 
} from '../services/api';

const SettingsModal = ({ isOpen, onClose, onSettingsUpdate }) => {
  const [providers, setProviders] = useState([]);
  const [apiKeys, setApiKeys] = useState({});
  const [showKeys, setShowKeys] = useState({});
  const [validationStatus, setValidationStatus] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (isOpen) {
      fetchProviders();
      fetchSettings();
    }
  }, [isOpen]);

  const fetchProviders = async () => {
    try {
      const data = await getProviders();
      setProviders(data.providers || []);
    } catch (err) {
      console.error('Error fetching providers:', err);
      setError('Failed to load providers');
    }
  };

  const fetchSettings = async () => {
    try {
      const data = await getUserSettings();
      
      // Initialize API keys state based on existing settings
      const keys = {};
      const validation = {};
      
      if (data.settings?.providers) {
        Object.entries(data.settings.providers).forEach(([providerId, config]) => {
          keys[providerId] = config.has_api_key ? '••••••••••••••••' : '';
          validation[providerId] = { configured: config.has_api_key };
        });
      }
      
      setApiKeys(keys);
      setValidationStatus(validation);
    } catch (err) {
      console.error('Error fetching settings:', err);
    }
  };

  const handleApiKeyChange = (providerId, value) => {
    setApiKeys(prev => ({
      ...prev,
      [providerId]: value
    }));
    
    // Clear validation status when key changes
    setValidationStatus(prev => ({
      ...prev,
      [providerId]: { ...prev[providerId], valid: undefined }
    }));
  };

  const toggleShowKey = (providerId) => {
    setShowKeys(prev => ({
      ...prev,
      [providerId]: !prev[providerId]
    }));
  };

  const validateAndSaveKey = async (providerId) => {
    const apiKey = apiKeys[providerId];
    if (!apiKey || apiKey === '••••••••••••••••') {
      return;
    }

    setIsLoading(true);
    setValidationStatus(prev => ({
      ...prev,
      [providerId]: { ...prev[providerId], validating: true }
    }));

    try {
      const result = await saveProviderSettings(providerId, apiKey);
      
      setValidationStatus(prev => ({
        ...prev,
        [providerId]: {
          configured: result.success,
          valid: result.success,
          validating: false,
          message: result.message
        }
      }));

      if (result.success) {
        // Mask the key after successful save
        setApiKeys(prev => ({
          ...prev,
          [providerId]: '••••••••••••••••'
        }));
        
        // Notify parent component of settings update
        if (onSettingsUpdate) {
          onSettingsUpdate();
        }
      }
    } catch (err) {
      console.error('Error saving API key:', err);
      setValidationStatus(prev => ({
        ...prev,
        [providerId]: {
          configured: false,
          valid: false,
          validating: false,
          message: err.message || 'Failed to save API key'
        }
      }));
    } finally {
      setIsLoading(false);
    }
  };

  const removeApiKey = async (providerId) => {
    setIsLoading(true);
    
    try {
      const result = await removeProviderSettings(providerId);
      
      if (result.success) {
        setApiKeys(prev => ({
          ...prev,
          [providerId]: ''
        }));
        
        setValidationStatus(prev => ({
          ...prev,
          [providerId]: { configured: false, valid: false }
        }));
        
        if (onSettingsUpdate) {
          onSettingsUpdate();
        }
      }
    } catch (err) {
      console.error('Error removing API key:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const getProviderStatus = (provider) => {
    const status = validationStatus[provider.id] || {};
    
    if (status.validating) {
      return <Loader2 className="w-4 h-4 animate-spin text-brand-purple" />;
    }
    
    if (status.valid) {
      return <Check className="w-4 h-4 text-brand-success-green" />;
    }
    
    if (status.configured === false && status.valid === false) {
      return <AlertCircle className="w-4 h-4 text-brand-alert-red" />;
    }
    
    return null;
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50">
      <div className="bg-brand-surface-bg border border-gray-700 rounded-xl shadow-2xl w-full max-w-2xl max-h-[80vh] overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b border-gray-700 bg-black/20">
          <h2 className="text-xl font-semibold text-brand-text-primary">Provider Settings</h2>
          <button
            onClick={onClose}
            className="p-1 rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-brand-purple"
            aria-label="Close settings"
          >
            <X className="w-5 h-5 text-brand-text-secondary" />
          </button>
        </div>
        
        <div className="p-6 overflow-y-auto max-h-[60vh]">
          {error && (
            <div className="mb-4 p-3 bg-brand-surface-bg border border-gray-700 text-brand-alert-red rounded">
              {error}
            </div>
          )}
          
          <div className="space-y-6">
            {providers.map((provider) => (
              <div key={provider.id} className="border border-gray-700 rounded-lg p-4 bg-brand-surface-bg">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-3">
                    <h3 className="text-lg font-medium text-brand-text-primary">
                      {provider.name}
                    </h3>
                    {getProviderStatus(provider)}
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className={`px-2 py-1 text-xs rounded-full border ${
                      provider.status?.available 
                        ? 'border-green-700 text-green-400'
                        : 'border-gray-700 text-brand-text-secondary'
                    }`}>
                      {provider.status?.available ? 'Available' : 'Unavailable'}
                    </span>
                  </div>
                </div>
                
                {provider.status?.requires_api_key && (
                  <div className="space-y-3">
                    <div className="flex space-x-2">
                      <div className="flex-1 relative">
                        <input
                          type={showKeys[provider.id] ? 'text' : 'password'}
                          value={apiKeys[provider.id] || ''}
                          onChange={(e) => handleApiKeyChange(provider.id, e.target.value)}
                          placeholder="Enter API key..."
                          className="w-full px-3 py-2 border border-gray-700 rounded-md bg-brand-main-bg text-brand-text-primary placeholder-brand-text-secondary focus:outline-none focus:ring-2 focus:ring-brand-purple"
                        />
                        <button
                          type="button"
                          onClick={() => toggleShowKey(provider.id)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-brand-text-secondary hover:text-brand-text-primary"
                        >
                          {showKeys[provider.id] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                      <button
                        onClick={() => validateAndSaveKey(provider.id)}
                        disabled={isLoading || !apiKeys[provider.id] || apiKeys[provider.id] === '••••••••••••••••'}
                        className="px-4 py-2 bg-brand-purple text-white rounded-md hover:bg-brand-button-grad-to disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-brand-purple"
                      >
                        Save
                      </button>
                      {validationStatus[provider.id]?.configured && (
                        <button
                          onClick={() => removeApiKey(provider.id)}
                          disabled={isLoading}
                          className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-brand-purple"
                        >
                          Remove
                        </button>
                      )}
                    </div>
                    
                    {validationStatus[provider.id]?.message && (
                      <p className={`text-sm ${
                        validationStatus[provider.id]?.valid 
                          ? 'text-green-400' 
                          : 'text-red-400'
                      }`}>
                        {validationStatus[provider.id].message}
                      </p>
                    )}
                  </div>
                )}
                
                {!provider.status?.requires_api_key && (
                  <p className="text-sm text-brand-text-secondary">
                    No API key required for this provider.
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
        
        <div className="flex justify-end p-6 border-t border-gray-700 bg-black/20">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-700 text-white rounded-md hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-brand-purple"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default SettingsModal;
