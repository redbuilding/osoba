import React from 'react';
import { X, Search, Database, Share2, Sparkles, Youtube } from 'lucide-react';

const ToolSelector = ({
  isOpen,
  onClose,
  tools,
  activeTool,
  onSelectTool,
  onHubspotConnect,
}) => {
  if (!isOpen) return null;

  const handleToolClick = (tool) => {
    if (tool.id === 'hubspot' && !tool.isAuthenticated) {
      onHubspotConnect();
      onClose();
    } else {
      // Toggle behavior: if clicking the active tool, deactivate it.
      onSelectTool(activeTool === tool.id ? null : tool.id);
      onClose();
    }
  };

  return (
    <div
      className="tool-selector-overlay"
      onClick={onClose}
    >
      <div
        className="tool-selector-container"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold text-brand-text-primary flex items-center">
            <Sparkles size={20} className="mr-2 text-brand-purple" />
            Select a Tool
          </h2>
          <button
            onClick={onClose}
            className="p-1 rounded-full hover:bg-gray-700 text-brand-text-secondary"
            aria-label="Close tool selector"
          >
            <X size={20} />
          </button>
        </div>
        <div className="space-y-2">
          {tools.map((tool) => (
            <button
              key={tool.id}
              onClick={() => handleToolClick(tool)}
              disabled={!tool.isReady}
              className={`w-full flex items-center p-3 rounded-lg text-left transition-colors duration-200
                ${activeTool === tool.id ? 'bg-brand-blue text-white' : 'bg-gray-700 hover:bg-gray-600'}
                ${!tool.isReady ? 'opacity-50 cursor-not-allowed' : ''}
              `}
            >
              <div className="flex-shrink-0 mr-3">{tool.icon}</div>
              <div className="flex-grow">
                <p className="font-semibold">{tool.name}</p>
                <p className="text-xs opacity-80">{tool.description}</p>
              </div>
              <div className="flex items-center">
                {tool.id === 'hubspot' && !tool.isAuthenticated && (
                   <span className="text-xs bg-yellow-500 text-black font-bold py-1 px-2 rounded-md mr-3">Connect</span>
                )}
                <div
                  className={`w-3 h-3 rounded-full ${tool.isReady ? 'bg-brand-success-green' : 'bg-brand-alert-red'}`}
                  title={tool.isReady ? 'Service Ready' : 'Service Unavailable'}
                ></div>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ToolSelector;
