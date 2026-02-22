import React, { useState, useEffect } from 'react';
import { 
  getHeartbeatConfig, 
  updateHeartbeatConfig,
  getContextConfig,
  updateContextConfig,
  getFileStatus,
  syncFromFile,
  syncToFile,
  triggerHeartbeat
} from '../services/heartbeatApi';

const EnhancedHeartbeatSettings = () => {
  const [config, setConfig] = useState(null);
  const [contextConfig, setContextConfig] = useState(null);
  const [fileStatus, setFileStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const [configData, contextData, fileData] = await Promise.all([
        getHeartbeatConfig(),
        getContextConfig(),
        getFileStatus()
      ]);
      setConfig(configData);
      setContextConfig(contextData.context_sources);
      setFileStatus(fileData);
    } catch (error) {
      console.error('Error loading settings:', error);
      showMessage('Failed to load settings', 'error');
    } finally {
      setLoading(false);
    }
  };

  const showMessage = (text, type = 'success') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 3000);
  };

  const handleConfigUpdate = async (updates) => {
    try {
      setSaving(true);
      await updateHeartbeatConfig(updates);
      setConfig({ ...config, ...updates });
      showMessage('Settings saved successfully');
    } catch (error) {
      console.error('Error updating config:', error);
      showMessage('Failed to save settings', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleContextUpdate = async (updates) => {
    try {
      setSaving(true);
      await updateContextConfig(updates);
      setContextConfig(updates);
      showMessage('Context sources updated');
    } catch (error) {
      console.error('Error updating context:', error);
      showMessage('Failed to update context sources', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleSyncFromFile = async () => {
    try {
      setSyncing(true);
      const result = await syncFromFile();
      if (result.status === 'success') {
        showMessage(`Synced ${result.tasks?.length || 0} tasks from file`);
        await loadSettings();
      } else {
        showMessage(result.message || 'Sync failed', 'error');
      }
    } catch (error) {
      console.error('Error syncing from file:', error);
      showMessage('Failed to sync from file', 'error');
    } finally {
      setSyncing(false);
    }
  };

  const handleSyncToFile = async () => {
    try {
      setSyncing(true);
      const result = await syncToFile();
      showMessage(`Wrote tasks to ${result.file_path}`);
      await loadSettings();
    } catch (error) {
      console.error('Error syncing to file:', error);
      showMessage('Failed to sync to file', 'error');
    } finally {
      setSyncing(false);
    }
  };

  const handleTestHeartbeat = async () => {
    try {
      setSaving(true);
      await triggerHeartbeat();
      showMessage('Heartbeat triggered successfully');
    } catch (error) {
      console.error('Error triggering heartbeat:', error);
      showMessage('Failed to trigger heartbeat', 'error');
    } finally {
      setSaving(false);
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
      {/* Message Banner */}
      {message && (
        <div className={`p-4 rounded-lg ${message.type === 'error' ? 'bg-red-900/20 border border-red-500' : 'bg-green-900/20 border border-green-500'}`}>
          <p className={message.type === 'error' ? 'text-red-400' : 'text-green-400'}>
            {message.text}
          </p>
        </div>
      )}

      {/* Basic Configuration */}
      <div className="bg-brand-surface-bg rounded-lg border border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-brand-text-primary mb-4">Basic Configuration</h3>
        
        <div className="space-y-4">
          {/* Enabled Toggle */}
          <div className="flex items-center justify-between">
            <div>
              <label className="text-brand-text-primary font-medium">Enable Heartbeat</label>
              <p className="text-sm text-brand-text-secondary">Periodic proactive insights</p>
            </div>
            <button
              onClick={() => handleConfigUpdate({ enabled: !config.enabled })}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-brand-purple ${config.enabled ? 'bg-brand-purple' : 'bg-gray-600'}`}
              disabled={saving}
            >
              <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${config.enabled ? 'translate-x-6' : 'translate-x-1'}`} />
            </button>
          </div>

          {/* Interval */}
          <div>
            <label className="block text-brand-text-primary font-medium mb-2">Check Interval</label>
            <select
              value={config.interval}
              onChange={(e) => handleConfigUpdate({ interval: e.target.value })}
              className="w-full bg-brand-main-bg text-brand-text-secondary border border-gray-600 rounded px-3 py-2 focus:outline-none focus:ring-1 focus:ring-brand-purple"
              disabled={saving}
            >
              <option value="30m">30 minutes</option>
              <option value="1h">1 hour</option>
              <option value="2h">2 hours</option>
              <option value="4h">4 hours</option>
              <option value="6h">6 hours</option>
            </select>
          </div>

          {/* Create Task Toggle */}
          <div className="flex items-center justify-between">
            <div>
              <label className="text-brand-text-primary font-medium">Auto-Create Tasks</label>
              <p className="text-sm text-brand-text-secondary">Convert insights to tracked tasks</p>
            </div>
            <button
              onClick={() => handleConfigUpdate({ create_task: !config.create_task })}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-brand-purple ${config.create_task ? 'bg-brand-purple' : 'bg-gray-600'}`}
              disabled={saving}
            >
              <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${config.create_task ? 'translate-x-6' : 'translate-x-1'}`} />
            </button>
          </div>

          {/* Max Insights */}
          <div>
            <label className="block text-brand-text-primary font-medium mb-2">Max Insights Per Day</label>
            <input
              type="number"
              min="1"
              max="20"
              value={config.max_insights_per_day}
              onChange={(e) => handleConfigUpdate({ max_insights_per_day: parseInt(e.target.value) })}
              className="w-full bg-brand-main-bg text-brand-text-secondary border border-gray-600 rounded px-3 py-2 focus:outline-none focus:ring-1 focus:ring-brand-purple"
              disabled={saving}
            />
          </div>
        </div>
      </div>

      {/* Context Sources */}
      <div className="bg-brand-surface-bg rounded-lg border border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-brand-text-primary mb-4">Context Sources</h3>
        <p className="text-sm text-brand-text-secondary mb-4">
          Select which context sources to include in heartbeat analysis
        </p>
        
        <div className="space-y-3">
          {[
            { key: 'memory', label: 'Semantic Memory', desc: 'Conversation history and search stats' },
            { key: 'git', label: 'Git Repository', desc: 'Branch, commits, and uncommitted changes' },
            { key: 'project', label: 'Project Files', desc: 'TODO comments and recent file changes' },
            { key: 'system', label: 'System Health', desc: 'Disk usage and service status' }
          ].map(({ key, label, desc }) => (
            <div key={key} className="flex items-center justify-between p-3 bg-brand-main-bg rounded border border-gray-700">
              <div>
                <label className="text-brand-text-primary font-medium">{label}</label>
                <p className="text-xs text-brand-text-secondary">{desc}</p>
              </div>
              <button
                onClick={() => handleContextUpdate({ ...contextConfig, [key]: !contextConfig[key] })}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-brand-purple ${contextConfig[key] ? 'bg-brand-purple' : 'bg-gray-600'}`}
                disabled={saving}
              >
                <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${contextConfig[key] ? 'translate-x-6' : 'translate-x-1'}`} />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* File-Based Configuration */}
      <div className="bg-brand-surface-bg rounded-lg border border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-brand-text-primary mb-4">File-Based Configuration</h3>
        <p className="text-sm text-brand-text-secondary mb-4">
          Power users can define heartbeat tasks in HEARTBEAT.md
        </p>
        
        {fileStatus?.exists ? (
          <div className="space-y-4">
            <div className="flex items-center space-x-2 text-brand-success-green">
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <span className="font-medium">HEARTBEAT.md found</span>
            </div>
            
            <div className="bg-brand-main-bg rounded p-3 border border-gray-700">
              <div className="text-sm space-y-1">
                <div className="flex justify-between">
                  <span className="text-brand-text-secondary">File Path:</span>
                  <span className="text-brand-text-primary font-mono text-xs">{fileStatus.file_path}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-brand-text-secondary">Tasks Defined:</span>
                  <span className="text-brand-text-primary">{fileStatus.task_count || 0}</span>
                </div>
                {fileStatus.errors?.length > 0 && (
                  <div className="mt-2 p-2 bg-red-900/20 border border-red-500 rounded">
                    <p className="text-red-400 text-xs font-medium mb-1">Validation Errors:</p>
                    {fileStatus.errors.map((err, i) => (
                      <p key={i} className="text-red-400 text-xs">• {err}</p>
                    ))}
                  </div>
                )}
              </div>
            </div>
            
            <div className="flex space-x-3">
              <button
                onClick={handleSyncFromFile}
                disabled={syncing || !fileStatus.valid}
                className="flex-1 px-4 py-2 bg-brand-purple text-white rounded hover:bg-brand-button-grad-to transition-colors focus:outline-none focus:ring-2 focus:ring-brand-blue disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {syncing ? 'Syncing...' : 'Load from File'}
              </button>
              <button
                onClick={handleSyncToFile}
                disabled={syncing}
                className="flex-1 px-4 py-2 bg-gray-700 text-white rounded hover:bg-gray-600 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-purple disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {syncing ? 'Syncing...' : 'Save to File'}
              </button>
            </div>
          </div>
        ) : (
          <div className="text-center py-6">
            <svg className="w-12 h-12 mx-auto text-brand-text-secondary mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p className="text-brand-text-secondary mb-2">No HEARTBEAT.md file found</p>
            <p className="text-xs text-brand-text-secondary mb-4">
              Create HEARTBEAT.md in your project root to define custom tasks
            </p>
            <a
              href="https://github.com/redbuilding/ohsee/blob/main/HEARTBEAT.md.example"
              target="_blank"
              rel="noopener noreferrer"
              className="text-brand-purple hover:text-brand-button-grad-to text-sm"
            >
              View Example File →
            </a>
          </div>
        )}
      </div>

      {/* Test Button */}
      <div className="flex justify-end">
        <button
          onClick={handleTestHeartbeat}
          disabled={saving}
          className="px-6 py-2 bg-brand-blue text-white rounded hover:bg-blue-600 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-blue disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? 'Running...' : 'Test Heartbeat Now'}
        </button>
      </div>
    </div>
  );
};

export default EnhancedHeartbeatSettings;
