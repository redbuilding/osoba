import React, { useState } from 'react';
import { Send, Search, Zap, Database, Server, Share2, LogIn } from 'lucide-react';

const ChatInput = ({ 
  onSendMessage, 
  isLoading, 
  isSearchActive, 
  onToggleSearch,
  isDatabaseActive,
  onToggleDatabase,
  isHubspotActive,
  onHubspotButtonClick,
  isHubspotAuthenticated,
  disabled,
  placeholder
}) => {
  const [inputValue, setInputValue] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (inputValue.trim() && !isLoading && !disabled) {
      onSendMessage(inputValue.trim());
      setInputValue('');
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="sticky bottom-0 left-0 right-0 p-4 bg-brand-main-bg border-t border-brand-surface-bg"
    >
      <div className="flex items-center bg-brand-surface-bg rounded-lg p-2 shadow-md">
        {/* Search Toggle Button */}
        <button
          type="button"
          onClick={onToggleSearch}
          title={isSearchActive ? "Disable Web Search" : "Enable Web Search"}
          disabled={disabled}
          className={`p-2 rounded-md mr-2 transition-colors duration-200 focus:outline-none focus:ring-2
            focus:ring-brand-purple ${
            isSearchActive ? 'bg-brand-accent text-brand-main-bg hover:bg-yellow-400' : 'bg-gray-700 text-brand-text-secondary hover:bg-gray-600'
          } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          {isSearchActive ? <Zap size={20} /> : <Search size={20} />}
        </button>

        {/* Database Toggle Button */}
        <button
          type="button"
          onClick={onToggleDatabase}
          title={isDatabaseActive ? "Disable Database Query" : "Enable Database Query"}
          disabled={disabled}
          className={`p-2 rounded-md mr-2 transition-colors duration-200 focus:outline-none focus:ring-2
            focus:ring-brand-purple ${
            isDatabaseActive ? 'bg-brand-blue text-white hover:bg-blue-500' : 'bg-gray-700 text-brand-text-secondary hover:bg-gray-600'
          } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          {isDatabaseActive ? <Server size={20} /> : <Database size={20} />}
        </button>

        {/* HubSpot Toggle/Connect Button */}
        <button
          type="button"
          onClick={onHubspotButtonClick}
          title={isHubspotAuthenticated ? (isHubspotActive ? "Disable HubSpot Actions" : "Enable HubSpot Actions") : "Connect to HubSpot"}
          disabled={disabled}
          className={`p-2 rounded-md mr-2 transition-colors duration-200 focus:outline-none focus:ring-2
            focus:ring-brand-purple ${
            isHubspotActive ? 'bg-orange-500 text-white hover:bg-orange-600' : 'bg-gray-700 text-brand-text-secondary hover:bg-gray-600'
          } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          {isHubspotAuthenticated ? <Share2 size={20} /> : <LogIn size={20} />}
        </button>
        
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder={placeholder}
          className="flex-grow p-2 bg-transparent text-brand-text-primary focus:outline-none placeholder-brand-text-secondary"
          disabled={isLoading || disabled}
        />
        <button
          type="submit"
          disabled={isLoading || !inputValue.trim() || disabled}
          className="p-2 ml-2 rounded-md bg-brand-purple text-white hover:bg-brand-button-grad-to
            focus:outline-none focus:ring-2 focus:ring-brand-blue disabled:opacity-50 transition-colors duration-200"
        >
          {isLoading ? (
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
          ) : (
            <Send size={20} />
          )}
        </button>
      </div>
       <div className="h-4 mt-2 text-xs ml-12 sm:ml-40"> {/* Container for consistent height */}
        {isSearchActive && (
          <p className="text-brand-accent">
            ⚡ Web search is active. Your message will be used as a search query.
          </p>
        )}
        {isDatabaseActive && (
          <p className="text-brand-blue">
            💾 Database query is active. Your message will be interpreted to query the database.
          </p>
        )}
        {isHubspotActive && (
          <p className="text-orange-400">
            🤖 HubSpot actions are active. Describe the email you want to create.
          </p>
        )}
      </div>
    </form>
  );
};

export default ChatInput;
