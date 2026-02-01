import React, { useState } from 'react';
import { Pin, PinOff, Loader2 } from 'lucide-react';

const ConversationPinButton = ({ 
  conversationId, 
  isPinned = false, 
  onPinToggle, 
  disabled = false 
}) => {
  const [isLoading, setIsLoading] = useState(false);

  const handleClick = async (e) => {
    e.stopPropagation(); // Prevent conversation selection
    
    if (disabled || isLoading) return;

    try {
      setIsLoading(true);
      await onPinToggle(conversationId, !isPinned);
    } catch (error) {
      console.error('Error toggling pin:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const buttonTitle = isPinned ? 'Unpin from context' : 'Pin for context';
  const IconComponent = isPinned ? PinOff : Pin;

  return (
    <button
      onClick={handleClick}
      disabled={disabled || isLoading}
      title={buttonTitle}
      className={`p-1.5 rounded-md transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-brand-purple
        ${isPinned 
          ? 'text-brand-purple hover:text-brand-button-grad-to hover:bg-gray-600' 
          : 'text-brand-text-secondary hover:text-brand-text-secondary hover:bg-gray-600'
        }
        ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
      `}
    >
      {isLoading ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : (
        <IconComponent className="w-4 h-4" />
      )}
    </button>
  );
};

export default ConversationPinButton;
