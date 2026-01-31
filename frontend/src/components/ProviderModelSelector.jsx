import React, { useState, useEffect } from 'react';
import { ChevronDown, AlertCircle, Check, X } from 'lucide-react';
import { getProviderModels } from '../services/api';

const ProviderModelSelector = ({ 
  selectedModel, 
  onModelSelect, 
  disabled = false,
  className = ""
}) => {
  const [providers, setProviders] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    fetchProviderModels();
  }, []);

  const fetchProviderModels = async () => {
    try {
      setIsLoading(true);
      const data = await getProviderModels();
      setProviders(data.providers || {});
      setError('');
    } catch (err) {
      console.error('Error fetching provider models:', err);
      setError('Failed to load models');
    } finally {
      setIsLoading(false);
    }
  };

  const getProviderStatus = (provider) => {
    if (!provider.status) return null;
    
    if (provider.status.available) {
      return <Check className="w-3 h-3 text-brand-success-green" />;
    } else {
      return <X className="w-3 h-3 text-brand-alert-red" />;
    }
  };

  const getModelDisplayName = (model, providerId) => {
    // For Ollama models, show without prefix for backward compatibility
    if (providerId === 'ollama') {
      return model;
    }
    
    // For other providers, show the model name without the provider prefix
    const prefix = `${providerId}/`;
    return model.startsWith(prefix) ? model.substring(prefix.length) : model;
  };

  const getFullModelName = (model, providerId) => {
    // For Ollama, return as-is for backward compatibility
    if (providerId === 'ollama') {
      return model;
    }
    
    // For other providers, ensure proper prefix
    const prefix = `${providerId}/`;
    return model.startsWith(prefix) ? model : `${prefix}${model}`;
  };

  const handleModelSelect = (model, providerId) => {
    const fullModelName = getFullModelName(model, providerId);
    onModelSelect(fullModelName, providerId);
    setIsOpen(false);
  };

  const getCurrentSelection = () => {
    if (!selectedModel) return { display: 'Select Model', provider: null };
    
    // Find which provider this model belongs to
    for (const [providerId, provider] of Object.entries(providers)) {
      const models = provider.models || [];
      
      if (providerId === 'ollama') {
        // For Ollama, check direct match
        if (models.includes(selectedModel)) {
          return { display: selectedModel, provider: providerId };
        }
      } else {
        // For other providers, check with prefix
        const prefix = `${providerId}/`;
        if (selectedModel.startsWith(prefix)) {
          const modelName = selectedModel.substring(prefix.length);
          if (models.includes(modelName) || models.includes(selectedModel)) {
            return { display: getModelDisplayName(selectedModel, providerId), provider: providerId };
          }
        }
      }
    }
    
    // Fallback - show the model name as-is
    return { display: selectedModel, provider: null };
  };

  const currentSelection = getCurrentSelection();

  if (isLoading) {
    return (
      <div className={`flex items-center space-x-2 ${className}`}>
        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
        <span className="text-sm text-gray-500">Loading models...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`flex items-center space-x-2 text-red-500 ${className}`}>
        <AlertCircle className="w-4 h-4" />
        <span className="text-sm">{error}</span>
      </div>
    );
  }

  return (
    <div className={`relative ${className}`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled}
        className="flex items-center justify-between w-full px-3 py-2 text-sm bg-brand-surface-bg text-brand-text-primary border border-gray-700 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-purple disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-700"
      >
        <div className="flex items-center space-x-2 min-w-0">
          {currentSelection.provider && (
            <span className="text-xs px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded">
              {providers[currentSelection.provider]?.name || currentSelection.provider}
            </span>
          )}
          <span className="truncate">{currentSelection.display}</span>
        </div>
        <ChevronDown className={`w-4 h-4 text-brand-text-secondary transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-brand-surface-bg border border-gray-700 rounded-md shadow-lg max-h-60 overflow-auto">
          {Object.entries(providers).map(([providerId, provider]) => (
            <div key={providerId}>
              <div className="px-3 py-2 bg-black/20 border-b border-gray-700">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-brand-text-primary">
                    {provider.name}
                  </span>
                  <div className="flex items-center space-x-2">
                    {getProviderStatus(provider)}
                    <span className="text-xs text-brand-text-secondary">
                      {provider.models?.length || 0} models
                    </span>
                  </div>
                </div>
              </div>
              
              {provider.status?.available || provider.status?.configured ? (
                <div className="max-h-32 overflow-y-auto">
                  {(provider.models || []).map((model) => {
                    const fullModelName = getFullModelName(model, providerId);
                    const isSelected = selectedModel === fullModelName || 
                                     (providerId === 'ollama' && selectedModel === model);
                    
                    return (
                      <button
                        key={model}
                        onClick={() => handleModelSelect(model, providerId)}
                        className={`w-full px-4 py-2 text-left text-sm hover:bg-gray-700 ${
                          isSelected 
                            ? 'bg-black/30 text-brand-purple' 
                            : 'text-brand-text-primary'
                        } ${!provider.status?.available ? 'opacity-75' : ''}`}
                        disabled={!provider.status?.available && !provider.status?.configured}
                      >
                        {getModelDisplayName(model, providerId)}
                        {!provider.status?.available && provider.status?.configured && (
                          <span className="text-xs text-yellow-400 ml-2">
                            (needs validation)
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              ) : (
                <div className="px-4 py-3 text-sm text-brand-text-secondary">
                  {provider.status?.requires_api_key && !provider.status?.configured
                    ? 'API key required'
                    : 'Provider unavailable'
                  }
                </div>
              )}
            </div>
          ))}
          
          {Object.keys(providers).length === 0 && (
            <div className="px-4 py-3 text-sm text-brand-text-secondary">
              No providers available
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ProviderModelSelector;
