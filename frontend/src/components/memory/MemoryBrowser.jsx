import React, { useState, useEffect } from 'react';
import { searchMemory, removeFromMemory } from '../../services/api';

export default function MemoryBrowser({ isOpen, onClose }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  const handleSearch = async () => {
    if (!query.trim()) return;

    setSearching(true);
    try {
      const data = await searchMemory(query, 10);
      setResults(data.results || []);
    } catch (error) {
      console.error('Error searching memory:', error);
    } finally {
      setSearching(false);
    }
  };

  const handleRemove = async (convId) => {
    try {
      await removeFromMemory(convId);
      setResults(results.filter(r => r.conv_id !== convId));
    } catch (error) {
      console.error('Error removing from memory:', error);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="memory-browser-overlay" onClick={onClose}>
      <div className="memory-browser" onClick={(e) => e.stopPropagation()}>
        <div className="memory-browser-header">
          <h2>🧠 Semantic Memory Search</h2>
          <button onClick={onClose} className="close-button">×</button>
        </div>

        <div className="memory-search-box">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Search past conversations..."
            className="memory-search-input"
            autoFocus
          />
          <button onClick={handleSearch} disabled={searching} className="search-button">
            {searching ? 'Searching...' : 'Search'}
          </button>
        </div>

        <div className="memory-results">
          {results.length === 0 && !searching && (
            <div className="no-results">
              {query ? 'No relevant conversations found' : 'Enter a query to search your memory'}
            </div>
          )}

          {results.map((result) => (
            <div key={result.id} className="memory-result">
              <div className="result-header">
                <span className="result-title">{result.metadata?.title || 'Untitled'}</span>
                <span className="result-score">{Math.round(result.score * 100)}% match</span>
              </div>
              <div className="result-preview">{result.text}</div>
              <div className="result-actions">
                <button onClick={() => handleRemove(result.conv_id)} className="remove-button">
                  Remove
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
