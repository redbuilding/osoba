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
    return <div className="memory-settings">Loading...</div>;
  }

  return (
    <div className="memory-settings">
      <h3>Semantic Memory</h3>
      
      <div className="settings-section">
        <h4>Statistics</h4>
        <div className="stats-grid">
          <div className="stat-item">
            <span className="stat-label">Total Chunks:</span>
            <span className="stat-value">{stats?.total_chunks || 0}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Collection:</span>
            <span className="stat-value">{stats?.collection_name || 'N/A'}</span>
          </div>
        </div>
      </div>

      <div className="settings-section">
        <h4>Actions</h4>
        <button 
          onClick={handleTriggerIndex} 
          disabled={indexing}
          className="action-button"
        >
          {indexing ? 'Indexing...' : 'Trigger Auto-Index Now'}
        </button>
        
        <button 
          onClick={() => setShowClearConfirm(true)}
          className="action-button danger"
        >
          Clear All Memory
        </button>
      </div>

      {showClearConfirm && (
        <div className="confirm-modal">
          <div className="confirm-content">
            <h4>Clear All Memory?</h4>
            <p>This will permanently delete all indexed conversations from semantic memory.</p>
            <div className="confirm-actions">
              <button onClick={handleClearMemory} className="confirm-button danger">
                Yes, Clear All
              </button>
              <button onClick={() => setShowClearConfirm(false)} className="confirm-button">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="settings-info">
        <p>
          <strong>About Semantic Memory:</strong> Conversations with 5+ messages are automatically 
          indexed after 10 minutes of inactivity. The system uses semantic search to find relevant 
          past conversations and inject them into new chats.
        </p>
      </div>
    </div>
  );
}
