import React, { useState, useCallback, useRef, useEffect } from 'react';
import { Search, X } from 'lucide-react';
import { searchConversations } from '../services/api';

const debounce = (func, wait) => {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
};

const SidebarSearch = ({ onSelectConversation, isCollapsed }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const inputRef = useRef(null);

  const handleSearch = useCallback(
    debounce(async (searchQuery) => {
      if (!searchQuery.trim()) {
        setResults([]);
        return;
      }
      
      setIsSearching(true);
      try {
        const searchResults = await searchConversations(searchQuery);
        setResults(searchResults);
      } catch (error) {
        console.error('Search error:', error);
        setResults([]);
      } finally {
        setIsSearching(false);
      }
    }, 300),
    []
  );

  useEffect(() => {
    handleSearch(query);
  }, [query, handleSearch]);

  const handleSelectConversation = (conversation) => {
    onSelectConversation(conversation._id);
    // Delay clearing to allow conversation selection to complete
    setTimeout(() => {
      setQuery('');
      setResults([]);
      setIsExpanded(false);
    }, 100);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      setQuery('');
      setResults([]);
      setIsExpanded(false);
      inputRef.current?.blur();
    }
  };

  const focusSearch = () => {
    if (inputRef.current) {
      inputRef.current.focus();
      setIsExpanded(true);
    }
  };

  // Expose focus method for keyboard shortcuts
  useEffect(() => {
    window.focusSidebarSearch = focusSearch;
    return () => {
      delete window.focusSidebarSearch;
    };
  }, []);

  if (isCollapsed) {
    return (
      <div className="p-2">
        <button
          onClick={focusSearch}
          className="w-full p-2 rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-brand-purple"
          title="Search conversations (Ctrl+K)"
        >
          <Search size={16} className="text-brand-text-secondary mx-auto" />
        </button>
      </div>
    );
  }

  return (
    <div className="p-3 border-b border-gray-700">
      {/* Search Input */}
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <Search className="h-4 w-4 text-brand-text-secondary" />
        </div>
        <input
          ref={inputRef}
          type="text"
          placeholder="Search conversations..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => setIsExpanded(true)}
          className="
            w-full pl-10 pr-8 py-2 
            bg-brand-surface-bg 
            border border-gray-700 
            rounded-md 
            text-brand-text-primary 
            placeholder-brand-text-secondary 
            focus:outline-none 
            focus:ring-2 
            focus:ring-brand-purple 
            focus:border-transparent
            text-sm
          "
        />
        {query && (
          <button
            onClick={() => {
              setQuery('');
              setResults([]);
              setIsExpanded(false);
            }}
            className="absolute inset-y-0 right-0 pr-3 flex items-center"
          >
            <X className="h-4 w-4 text-brand-text-secondary hover:text-brand-text-primary" />
          </button>
        )}
      </div>

      {/* Search Results */}
      {isExpanded && (query || results.length > 0) && (
        <div className="mt-2 max-h-64 overflow-y-auto bg-brand-surface-bg border border-gray-700 rounded-md">
          {isSearching && (
            <div className="p-3 text-center text-brand-text-secondary text-sm">
              Searching...
            </div>
          )}
          
          {!isSearching && query && results.length === 0 && (
            <div className="p-3 text-center text-brand-text-secondary text-sm">
              No conversations found
            </div>
          )}
          
          {results.map((conversation) => (
            <div
              key={conversation._id}
              onClick={() => handleSelectConversation(conversation)}
              className="p-3 hover:bg-gray-700 cursor-pointer border-b border-gray-700 last:border-b-0"
            >
              <div className="font-medium text-brand-text-primary text-sm mb-1 truncate">
                {conversation.title || 'Untitled Conversation'}
              </div>
              <div className="text-xs text-brand-text-secondary">
                {conversation.message_count} messages • {new Date(conversation.updated_at).toLocaleDateString()}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SidebarSearch;
