import React from 'react';
import { X } from 'lucide-react';

const RightPanel = ({ 
  isOpen, 
  onClose, 
  title, 
  children, 
  width = "w-96" // Default width, can be overridden
}) => {
  return (
    <div className={`
      ${isOpen ? width : 'w-0'} 
      transition-all duration-300 ease-in-out 
      bg-brand-surface-bg 
      border-l border-gray-700 
      flex flex-col 
      h-screen 
      overflow-hidden
    `}>
      {isOpen && (
        <>
          {/* Panel Header */}
          <div className="p-4 border-b border-gray-700 flex items-center justify-between bg-brand-surface-bg">
            <h2 className="font-semibold text-brand-text-primary">{title}</h2>
            <button
              onClick={onClose}
              className="p-1 rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-brand-purple"
              title="Close panel"
            >
              <X size={18} className="text-brand-text-secondary" />
            </button>
          </div>

          {/* Panel Content */}
          <div className="flex-1 overflow-hidden">
            {children}
          </div>
        </>
      )}
    </div>
  );
};

export default RightPanel;
