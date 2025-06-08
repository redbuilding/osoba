// frontend/src/components/ChatInput.jsx
import React, { useState } from "react";
import { Send, Sparkles, Search, Database, Share2 } from "lucide-react";

const ChatInput = ({
  onSendMessage,
  onStopGenerating, // ✨ NEW – stop handler
  isLoading,
  activeTool,
  onToggleToolSelector,
  disabled,
  placeholder,
}) => {
  const [inputValue, setInputValue] = useState("");

  /* ------------------------------------------------------------------- */
  /*  Handlers                                                           */
  /* ------------------------------------------------------------------- */
  const handleSubmit = (e) => {
    e.preventDefault();
    if (inputValue.trim() && !isLoading && !disabled) {
      onSendMessage(inputValue.trim());
      setInputValue("");
    }
  };

  /* ------------------------------------------------------------------- */
  /*  Tool info helpers                                                  */
  /* ------------------------------------------------------------------- */
  const getActiveToolInfo = () => {
    switch (activeTool) {
      case "search":
        return {
          Icon: Search,
          text: "Web search is active. Your message will be used as a search query.",
          colorClass: "text-brand-accent",
          buttonColorClass:
            "bg-brand-accent text-brand-main-bg hover:bg-yellow-400",
        };
      case "database":
        return {
          Icon: Database,
          text: "Database query is active. Your message will be interpreted to query the database.",
          colorClass: "text-brand-blue",
          buttonColorClass: "bg-brand-blue text-white hover:bg-blue-500",
        };
      case "hubspot":
        return {
          Icon: Share2,
          text: "HubSpot actions are active. Describe the email you want to create.",
          colorClass: "text-orange-400",
          buttonColorClass: "bg-orange-500 text-white hover:bg-orange-600",
        };
      default:
        return null;
    }
  };

  const activeToolInfo = getActiveToolInfo();

  /* ------------------------------------------------------------------- */
  /*  Render                                                             */
  /* ------------------------------------------------------------------- */
  return (
    <form
      onSubmit={handleSubmit}
      className="sticky bottom-0 left-0 right-0 p-4 bg-brand-main-bg border-t border-brand-surface-bg"
    >
      <div className="flex items-center bg-brand-surface-bg rounded-lg p-2 shadow-md">
        {/* Tool selector button */}
        <button
          type="button"
          onClick={onToggleToolSelector}
          title={activeTool ? `Disable ${activeTool} Tool` : "Select a Tool"}
          disabled={disabled}
          className={`p-2 rounded-md mr-2 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-brand-purple ${
            activeToolInfo
              ? activeToolInfo.buttonColorClass
              : "bg-gray-700 text-brand-text-secondary hover:bg-gray-600"
          } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
        >
          {activeToolInfo ? (
            <activeToolInfo.Icon size={20} />
          ) : (
            <Sparkles size={20} />
          )}
        </button>

        {/* Text input */}
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder={placeholder}
          className="flex-grow p-2 bg-transparent text-brand-text-primary focus:outline-none placeholder-brand-text-secondary"
          disabled={isLoading || disabled}
        />

        {/* Send / Stop button */}
        {isLoading ? (
          <button
            type="button"
            onClick={onStopGenerating}
            className="p-2 ml-2 rounded-md bg-brand-alert-red text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 transition-colors duration-200"
            title="Stop Generating"
          >
            {/* simple square icon */}
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="currentColor"
            >
              <path d="M6 6h12v12H6z" />
            </svg>
          </button>
        ) : (
          <button
            type="submit"
            disabled={!inputValue.trim() || disabled}
            className="p-2 ml-2 rounded-md bg-brand-purple text-white hover:bg-brand-button-grad-to focus:outline-none focus:ring-2 focus:ring-brand-blue disabled:opacity-50 transition-colors duration-200"
          >
            <Send size={20} />
          </button>
        )}
      </div>

      {/* Active tool hint */}
      <div className="h-4 mt-2 text-xs ml-4">
        {activeToolInfo && (
          <p className={activeToolInfo.colorClass}>⚡ {activeToolInfo.text}</p>
        )}
      </div>
    </form>
  );
};

export default ChatInput;
