import React, { useEffect, useMemo, useState } from 'react';
import { X, Check, AlertCircle, Search } from 'lucide-react';
import { getProviderModels } from '../services/api';

const ProviderItem = ({ providerId, provider, selected, onSelect }) => {
  const status = provider.status || {};
  const configured = !!status.configured;
  const available = !!status.available;
  return (
    <button
      onClick={() => onSelect(providerId)}
      className={`w-full text-left px-3 py-2 rounded-md border ${
        selected ? 'bg-black/30 border-gray-700' : 'bg-brand-surface-bg border-transparent hover:bg-gray-800'
      } flex items-center justify-between`}
    >
      <span className="text-sm text-brand-text-primary truncate">{provider.name}</span>
      {configured ? (
        <Check className={`w-4 h-4 ${available ? 'text-brand-success-green' : 'text-brand-text-secondary'}`} />
      ) : (
        <AlertCircle className="w-4 h-4 text-brand-alert-red" />
      )}
    </button>
  );
};

const ModelRow = ({ name, selected, onClick }) => {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-3 py-2 rounded-md text-sm ${
        selected ? 'bg-black/30 text-brand-purple' : 'hover:bg-gray-700 text-brand-text-primary'
      }`}
      title={name}
    >
      {name}
    </button>
  );
};

const ModelPickerModal = ({ isOpen, onClose, onSelectModel, currentModel, onOpenSettings }) => {
  const [providers, setProviders] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeProvider, setActiveProvider] = useState(null);
  const [query, setQuery] = useState('');

  useEffect(() => {
    if (!isOpen) return;
    const fetchData = async () => {
      try {
        setLoading(true);
        setError('');
        const data = await getProviderModels();
        const map = data.providers || {};
        setProviders(map);
        // Choose initial active provider: current model's provider or first configured
        let initial = activeProvider;
        if (!initial) {
          if (currentModel) {
            const parts = currentModel.split('/');
            if (parts.length > 1 && map[parts[0]]) initial = parts[0];
            else if (map['ollama']) initial = 'ollama';
          }
        }
        if (!initial) {
          const configuredFirst = Object.entries(map).find(([, p]) => p?.status?.configured);
          initial = configuredFirst ? configuredFirst[0] : Object.keys(map)[0];
        }
        setActiveProvider(initial || null);
      } catch (e) {
        console.error('Failed to load provider models:', e);
        setError('Failed to load models.');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [isOpen]);

  const modelsForActive = useMemo(() => {
    if (!activeProvider || !providers[activeProvider]) return [];
    const list = providers[activeProvider].models || [];
    const normalized = activeProvider === 'ollama' ? list : list.map(m => (m.startsWith(activeProvider + '/') ? m.slice(activeProvider.length + 1) : m));
    if (!query) return normalized;
    const q = query.toLowerCase();
    return normalized.filter(m => m.toLowerCase().includes(q));
  }, [activeProvider, providers, query]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100]">
      <div className="absolute inset-0 bg-black bg-opacity-60" onClick={onClose} />
      <div className="absolute inset-0 flex items-center justify-center p-4">
        <div className="w-full max-w-4xl bg-brand-surface-bg border border-gray-700 rounded-xl shadow-2xl overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-700 bg-black/20">
            <h2 className="text-lg font-semibold text-brand-text-primary">Select Model</h2>
            <button onClick={onClose} className="p-1 rounded hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-brand-purple" aria-label="Close model picker">
              <X className="w-5 h-5 text-brand-text-secondary" />
            </button>
          </div>

          {/* Body: two-pane */}
          <div className="grid grid-cols-[220px_1fr] max-h-[75vh]">
            {/* Left: providers, no internal scroll; right: the only scroll region */}
            <div className="p-3 border-r border-gray-700 bg-brand-surface-bg">
              <div className="space-y-2">
                {Object.entries(providers).map(([pid, p]) => (
                  <ProviderItem key={pid} providerId={pid} provider={p} selected={pid === activeProvider} onSelect={setActiveProvider} />
                ))}
                {Object.keys(providers).length === 0 && (
                  <div className="text-sm text-brand-text-secondary">No providers.</div>
                )}
              </div>
            </div>
            <div className="flex flex-col">
              {/* Right header with search and state */}
              <div className="p-3 bg-black/10 border-b border-gray-700">
                <div className="flex items-center gap-2">
                  <div className="relative flex-1">
                    <Search className="w-4 h-4 text-brand-text-secondary absolute left-2 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="Search models"
                      className="w-full pl-8 pr-3 py-2 bg-brand-main-bg border border-gray-700 rounded-md text-brand-text-primary placeholder-brand-text-secondary focus:outline-none focus:ring-2 focus:ring-brand-purple"
                    />
                  </div>
                  {activeProvider && providers[activeProvider] && !providers[activeProvider].status?.configured && (
                    <button onClick={onOpenSettings} className="px-3 py-2 text-sm bg-brand-purple text-white rounded-md hover:bg-brand-button-grad-to focus:outline-none focus:ring-2 focus:ring-brand-purple">
                      Open Settings
                    </button>
                  )}
                </div>
                {loading && <div className="text-xs text-brand-text-secondary mt-2">Loading models…</div>}
                {error && <div className="text-xs text-brand-alert-red mt-2">{error}</div>}
              </div>
              {/* Right list: the single scroll region */}
              <div className="flex-1 overflow-y-auto p-2">
                {!activeProvider && (
                  <div className="text-sm text-brand-text-secondary p-3">Select a provider to view models.</div>
                )}
                {activeProvider && modelsForActive.length === 0 && (
                  <div className="text-sm text-brand-text-secondary p-3">
                    {providers[activeProvider]?.status?.configured ? 'No models available.' : 'API key required for this provider.'}
                  </div>
                )}
                {activeProvider && modelsForActive.length > 0 && (
                  <div className="space-y-1">
                    {modelsForActive.map((model) => {
                      // Build full name used by backend
                      const fullName = activeProvider === 'ollama' ? model : `${activeProvider}/${model}`;
                      const selected = currentModel === fullName || currentModel === model;
                      return (
                        <ModelRow
                          key={fullName}
                          name={model}
                          selected={selected}
                          onClick={() => onSelectModel(fullName, activeProvider)}
                        />
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ModelPickerModal;
