import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const GoalsEditor = ({ userId = 'default' }) => {
  const [goals, setGoals] = useState('');
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadGoals();
  }, [userId]);

  const loadGoals = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/user-profile`, {
        params: { user_id: userId }
      });
      setGoals(response.data.profile?.goals_document || '');
    } catch (err) {
      console.error('Error loading goals:', err);
      setError('Failed to load goals');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setLoading(true);
      setError('');
      await axios.put(
        `${API_URL}/user-profile`,
        { goals_document: goals },
        { params: { user_id: userId } }
      );
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      console.error('Error saving goals:', err);
      setError('Failed to save goals');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-brand-surface-bg rounded-lg shadow border border-gray-700 p-6">
      <h3 className="text-lg font-semibold text-brand-text-primary mb-4">
        Goals & Priorities
      </h3>
      <p className="text-sm text-brand-text-secondary mb-4">
        Define your goals and priorities. The AI will use this to provide proactive suggestions.
      </p>
      
      <textarea
        value={goals}
        onChange={(e) => setGoals(e.target.value)}
        className="w-full bg-brand-main-bg text-brand-text-primary border border-gray-600 
                   focus:outline-none focus:ring-2 focus:ring-brand-purple rounded p-3 
                   font-mono text-sm"
        rows={10}
        placeholder="Enter your goals and priorities...

Example:
- Complete the user authentication feature
- Improve test coverage to 80%
- Research new deployment strategies"
        disabled={loading}
      />
      
      <div className="flex items-center justify-between mt-4">
        <div>
          {saved && (
            <span className="text-brand-success-green text-sm">
              ✓ Goals saved successfully
            </span>
          )}
          {error && (
            <span className="text-brand-alert-red text-sm">
              {error}
            </span>
          )}
        </div>
        
        <button
          onClick={handleSave}
          disabled={loading}
          className="bg-brand-purple text-white rounded-md px-4 py-2 
                     hover:bg-brand-button-grad-to transition-colors duration-200
                     focus:outline-none focus:ring-2 focus:ring-brand-blue
                     disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Saving...' : 'Save Goals'}
        </button>
      </div>
    </div>
  );
};

export default GoalsEditor;
