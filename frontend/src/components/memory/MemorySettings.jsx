import React, { useState, useEffect } from 'react';
import { getMemoryStats, triggerAutoIndex, clearMemory } from '../../services/api';

export default function MemorySettings() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [indexing, setIndexing] = useState(false);
  const [showClearConfirm, setShowClearConfirm] = useState(false);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    setLoading(true);
    try {
      const data = await getMemoryStats();
      setStats(data);
    } catch (error) {
      console.error('Error loading memory stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTriggerIndex = async () => {
    setIndexing(true);
    try {
      const result = await triggerAutoIndex();
      alert(`Indexed ${result.indexed} of ${result.found} conversations`);
      await loadStats();
    } catch (error) {
      console.error('Error triggering index:', error);
      alert('Error triggering auto-index');
    } finally {
      setIndexing(false);
    }
  };

  const handleClearMemory = async () => {
    try {
      await clearMemory();
      setShowClearConfirm(false);
      await loadStats();
      alert('Memory cleared successfully');
    } catch (error) {
      console.error('Error clearing memory:', error);
      alert('Error clearing memory');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-purple"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Statistics */}
      <div className="bg-brand-surface-bg rounded-lg border border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-brand-text-primary mb-4">Statistics</h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center justify-between p-3 bg-brand-main-bg rounded border border-gray-700">
            <span className="text-sm text-brand-text-secondary">Total Chunks</span>
            <span className="text-sm font-semibold text-brand-text-primary">{stats?.total_chunks || 0}</span>
          </div>
          <div className="flex items-center justify-between p-3 bg-brand-main-bg rounded border border-gray-700">
            <span className="text-sm text-brand-text-secondary">Collection</span>
            <span className="text-sm font-semibold text-brand-text-primary">{stats?.collection_name || 'N/A'}</span>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="bg-brand-surface-bg rounded-lg border border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-brand-text-primary mb-4">Actions</h3>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={handleTriggerIndex}
            disabled={indexing}
            className="px-4 py-2 bg-brand-purple text-white rounded hover:bg-brand-button-grad-to transition-colors focus:outline-none focus:ring-2 focus:ring-brand-purple disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {indexing ? 'Indexing...' : 'Trigger Auto-Index Now'}
          </button>
          <button
            onClick={() => setShowClearConfirm(true)}
            className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-alert-red"
          >
            Clear All Memory
          </button>
        </div>
      </div>

      {/* Clear Confirmation */}
      {showClearConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-[2000]">
          <div className="bg-brand-surface-bg border border-gray-700 rounded-lg p-6 max-w-sm shadow-2xl">
            <h4 className="text-lg font-semibold text-brand-text-primary mb-2">Clear All Memory?</h4>
            <p className="text-sm text-brand-text-secondary mb-4">
              This will permanently delete all indexed conversations from semantic memory.
            </p>
            <div className="flex gap-3">
              <button
                onClick={handleClearMemory}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
              >
                Yes, Clear All
              </button>
              <button
                onClick={() => setShowClearConfirm(false)}
                className="flex-1 px-4 py-2 bg-gray-700 text-white rounded hover:bg-gray-600 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Info */}
      <div className="bg-brand-main-bg rounded-lg border border-gray-700 p-4">
        <p className="text-sm text-brand-text-secondary leading-relaxed">
          <span className="font-semibold text-brand-text-primary">About Semantic Memory:</span>{' '}
          Conversations with 5+ messages are automatically indexed after 10 minutes of inactivity.
          The system uses semantic search to find relevant past conversations and inject them into new chats.
        </p>
      </div>
    </div>
  );
}
