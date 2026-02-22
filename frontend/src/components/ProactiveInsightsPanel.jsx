import React, { useState, useEffect, useRef } from 'react';
import { Bell, X, CheckCircle } from 'lucide-react';
import { getInsights, dismissInsight, createTaskFromInsight } from '../services/heartbeatApi';

const ProactiveInsightsPanel = ({ userId = 'default' }) => {
  const [insights, setInsights] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [creatingTask, setCreatingTask] = useState(null);
  const panelRef = useRef(null);
  const pollIntervalRef = useRef(null);

  useEffect(() => {
    // Load insights on mount
    loadInsights();
    
    // Poll for new insights every 60 seconds (always, not just when open)
    pollIntervalRef.current = setInterval(loadInsights, 60000);

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [userId]);

  useEffect(() => {
    // Reload insights when panel opens
    if (isOpen) {
      loadInsights();
    }
  }, [isOpen]);

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (panelRef.current && !panelRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const loadInsights = async () => {
    try {
      setLoading(true);
      const data = await getInsights(userId, false); // Only non-dismissed
      setInsights(data);
    } catch (error) {
      console.error('Error loading insights:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDismiss = async (insightId) => {
    try {
      await dismissInsight(insightId, userId);
      setInsights(insights.filter(i => i._id !== insightId));
    } catch (error) {
      console.error('Error dismissing insight:', error);
    }
  };

  const handleCreateTask = async (insightId) => {
    try {
      setCreatingTask(insightId);
      await createTaskFromInsight(insightId, userId);
      // Mark insight as having task created
      setInsights(insights.map(i => 
        i._id === insightId ? { ...i, taskCreated: true } : i
      ));
    } catch (error) {
      console.error('Error creating task:', error);
    } finally {
      setCreatingTask(null);
    }
  };

  const togglePanel = () => {
    setIsOpen(!isOpen);
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  };

  const undismissedCount = insights.length;

  return (
    <div className="relative" ref={panelRef}>
      {/* Bell Icon Button */}
      <button
        onClick={togglePanel}
        className="relative p-2 rounded-md hover:bg-gray-700 
                   focus:outline-none focus:ring-2 focus:ring-brand-purple
                   transition-colors duration-200"
        aria-label="View proactive insights"
        aria-expanded={isOpen}
      >
        <Bell className="w-5 h-5 text-brand-purple" aria-hidden="true" />
        
        {/* Badge */}
        {undismissedCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-brand-alert-red text-white 
                           text-xs rounded-full w-5 h-5 flex items-center justify-center
                           font-semibold">
            {undismissedCount > 9 ? '9+' : undismissedCount}
          </span>
        )}
      </button>

      {/* Dropdown Panel */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-brand-surface-bg rounded-lg 
                        shadow-lg border border-gray-700 max-h-96 overflow-y-auto
                        insights-panel z-50">
          {/* Header */}
          <div className="p-4 border-b border-gray-700 sticky top-0 bg-brand-surface-bg">
            <h3 className="text-lg font-semibold text-brand-text-primary">
              Proactive Insights
            </h3>
          </div>

          {/* Content */}
          {loading && insights.length === 0 ? (
            <div className="p-8 text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-2 
                              border-brand-purple border-t-transparent mx-auto" />
              <p className="text-brand-text-secondary text-sm mt-2">Loading insights...</p>
            </div>
          ) : insights.length === 0 ? (
            <div className="p-8 text-center text-brand-text-secondary">
              <Bell className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>No insights right now</p>
              <p className="text-xs mt-1">Check back later for suggestions</p>
            </div>
          ) : (
            <div>
              {insights.map((insight) => (
                <div
                  key={insight._id}
                  className="p-4 border-b border-gray-700 hover:bg-gray-700 
                             transition-colors duration-200"
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1 pr-2">
                      <h4 className="text-sm font-semibold text-brand-text-primary mb-1">
                        {insight.title}
                      </h4>
                      <p className="text-sm text-brand-text-secondary">
                        {insight.description}
                      </p>
                      <div className="flex items-center justify-between mt-3">
                        <div className="text-xs text-brand-text-secondary">
                          {formatTimestamp(insight.created_at)}
                        </div>
                        
                        {/* Create Task Button */}
                        {!insight.taskCreated && (
                          <button
                            onClick={() => handleCreateTask(insight._id)}
                            disabled={creatingTask === insight._id}
                            className="text-xs px-3 py-1 bg-brand-purple text-white rounded 
                                     hover:bg-brand-button-grad-to transition-colors
                                     focus:outline-none focus:ring-2 focus:ring-brand-blue
                                     disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            {creatingTask === insight._id ? 'Creating...' : 'Create Task'}
                          </button>
                        )}
                        
                        {insight.taskCreated && (
                          <div className="flex items-center space-x-1 text-xs text-brand-success-green">
                            <CheckCircle className="w-3 h-3" />
                            <span>Task Created</span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Dismiss Button */}
                    <button
                      onClick={() => handleDismiss(insight._id)}
                      className="ml-2 p-1 rounded hover:bg-gray-600 
                                 focus:outline-none focus:ring-2 focus:ring-brand-purple
                                 transition-colors duration-200"
                      aria-label={`Dismiss insight: ${insight.title}`}
                    >
                      <X className="w-4 h-4 text-brand-text-secondary hover:text-brand-alert-red" 
                         aria-hidden="true" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ProactiveInsightsPanel;
