// frontend/src/components/ChatInput.jsx
import React, { useState, useRef } from "react";
import { Send, Sparkles, Search, Database, Share2, Youtube, FileCode, Paperclip, X, BookOpen } from "lucide-react";

const ChatInput = ({
  onSendMessage,
  onStopGenerating,
  isLoading,
  activeTool,
  onToggleToolSelector,
  disabled,
  placeholder,
  onFileChange,
  uploadedFile,
  onClearFile,
  onInjectDocs,
  docsInjected,
  currentConversationId,
}) => {
  const [inputValue, setInputValue] = useState("");
  const fileInputRef = useRef(null);

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

  const handleFileButtonClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileSelected = (e) => {
    const file = e.target.files[0];
    if (file) {
      onFileChange(file);
    }
    // Reset file input value to allow re-uploading the same file
    e.target.value = null;
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
          buttonColorClass: "bg-brand-accent text-brand-main-bg hover:bg-yellow-400",
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
      case "youtube":
        return {
          Icon: Youtube,
          text: "YouTube transcript is active. Paste a video URL to get its transcript.",
          colorClass: "text-red-500",
          buttonColorClass: "bg-red-600 text-white hover:bg-red-700",
        };
      case "python":
        return {
          Icon: FileCode,
          text: "Python analysis is active. Upload a CSV and ask a question.",
          colorClass: "text-green-400",
          buttonColorClass: "bg-green-600 text-white hover:bg-green-700",
        };
      case "codex":
        return {
          Icon: Sparkles,
          text: "Codex workspace is active. Your message will run Codex to generate files.",
          colorClass: "text-brand-purple",
          buttonColorClass: "bg-brand-purple text-white hover:bg-brand-button-grad-to",
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

        {/* File Upload Button for Python Tool */}
        {activeTool === 'python' && (
          <>
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileSelected}
              className="hidden"
              accept=".csv"
              disabled={disabled}
            />
            <button
              type="button"
              onClick={handleFileButtonClick}
              title="Upload CSV file"
              disabled={disabled}
              className="p-2 rounded-md mr-2 bg-gray-700 text-brand-text-secondary hover:bg-gray-600 disabled:opacity-50"
            >
              <Paperclip size={20} />
            </button>
          </>
        )}

        {/* Docs Injection Button */}
        <button
          type="button"
          onClick={onInjectDocs}
          title={docsInjected ? "Disable documentation context" : "Enable Osoba documentation context"}
          disabled={disabled}
          className={`p-2 rounded-md mr-2 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-brand-purple ${
            docsInjected 
              ? "bg-brand-purple text-white" 
              : "bg-gray-700 text-brand-text-secondary hover:bg-brand-purple hover:text-white"
          } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
        >
          <BookOpen size={20} />
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

      {/* Active tool hint & file info */}
      <div className="h-4 mt-2 text-xs ml-4 flex items-center">
        {activeToolInfo && (
          <p className={activeToolInfo.colorClass}>⚡ {activeToolInfo.text}</p>
        )}
        {activeTool === 'python' && uploadedFile && (
          <div className="ml-auto flex items-center bg-gray-700 text-brand-text-secondary px-2 py-1 rounded-full">
            <span>{uploadedFile.filename}</span>
            <button
              type="button"
              onClick={onClearFile}
              className="ml-2 text-gray-400 hover:text-white"
              title="Clear file"
            >
              <X size={14} />
            </button>
          </div>
        )}
      </div>
    </form>
  );
};

export default ChatInput;
