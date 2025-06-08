// frontend/src/App.jsx
import React, {
  useState,
  useEffect,
  useRef,
  useCallback,
  useMemo,
} from "react";
import ChatMessage from "./components/ChatMessage";
import ChatInput from "./components/ChatInput";
import ConversationSidebar from "./components/ConversationSidebar";
import ToolSelector from "./components/ToolSelector";
import {
  sendMessage, // still used for legacy / fall‑back
  streamMessage, // ✨ NEW – SSE streaming
  getServiceStatus,
  getConversations,
  getConversationMessages,
  getOllamaModels,
  deleteConversation,
  renameConversation,
  getHubspotAuthStatus,
  BACKEND_URL,
} from "./services/api";
import {
  AlertTriangle,
  Wifi,
  Database,
  Loader2,
  BrainCircuit,
  PanelLeftClose,
  PanelRightOpen,
  Server,
  Share2,
  Search,
} from "lucide-react";

// MCP service names
const WEB_SEARCH_SERVICE_NAME = "web_search_service";
const MYSQL_DB_SERVICE_NAME = "mysql_db_service";
const HUBSPOT_SERVICE_NAME = "hubspot_service";

const App = () => {
  // Chat & loading state
  const [chatHistory, setChatHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Tool selector state
  const [activeTool, setActiveTool] = useState(null);
  const [isToolSelectorOpen, setIsToolSelectorOpen] = useState(false);

  // Service status state
  const [mcpSearchServiceReady, setMcpSearchServiceReady] = useState(false);
  const [mcpDbServiceReady, setMcpDbServiceReady] = useState(false);
  const [mcpHubspotServiceReady, setMcpHubspotServiceReady] = useState(false);
  const [isHubspotAuthenticated, setIsHubspotAuthenticated] = useState(false);
  const [dbConnected, setDbConnected] = useState(false);
  const [ollamaAvailable, setOllamaAvailable] = useState(false);

  // Conversation list / sidebar
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [isConversationsLoading, setIsConversationsLoading] = useState(true);
  const [conversationsError, setConversationsError] = useState(null);
  const [isChatHistoryLoading, setIsChatHistoryLoading] = useState(false);

  // Ollama models
  const [availableOllamaModels, setAvailableOllamaModels] = useState([]);
  const [selectedOllamaModel, setSelectedOllamaModel] = useState("");
  const [ollamaModelsError, setOllamaModelsError] = useState(null);

  // Layout
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  // Refs
  const chatContainerRef = useRef(null);
  const abortControllerRef = useRef(null); // ✨ NEW – for cancelling streams

  // Initial assistant message
  const initialWelcomeMessage = useMemo(
    () => ({
      role: "assistant",
      content:
        "Hello! I'm your AI assistant. Select a model for new chats. Click the ✨ icon to use tools. Select 'New Chat' or a past conversation.",
      timestamp: new Date().toISOString(),
    }),
    [],
  );

  /* --------------------------------------------------------------------- */
  /*  Scroll chat to bottom whenever it grows                              */
  /* --------------------------------------------------------------------- */
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop =
        chatContainerRef.current.scrollHeight;
    }
  }, [chatHistory]);

  /* --------------------------------------------------------------------- */
  /*  Service status polling                                               */
  /* --------------------------------------------------------------------- */
  const fetchServiceStatus = useCallback(async () => {
    try {
      const status = await getServiceStatus();
      setMcpSearchServiceReady(
        status.mcp_services?.[WEB_SEARCH_SERVICE_NAME]?.ready || false,
      );
      setMcpDbServiceReady(
        status.mcp_services?.[MYSQL_DB_SERVICE_NAME]?.ready || false,
      );
      setMcpHubspotServiceReady(
        status.mcp_services?.[HUBSPOT_SERVICE_NAME]?.ready || false,
      );
      setOllamaAvailable(status.ollama_available);
      const newDbConnected = status.db_connected;
      setDbConnected(newDbConnected);

      if (!newDbConnected) {
        setConversationsError(
          "Chat history database (MongoDB) not connected. History is unavailable.",
        );
      } else {
        if (conversationsError?.includes("MongoDB"))
          setConversationsError(null);
      }
    } catch {
      setMcpSearchServiceReady(false);
      setMcpDbServiceReady(false);
      setMcpHubspotServiceReady(false);
      setDbConnected(false);
      setOllamaAvailable(false);
      setConversationsError(
        "Failed to fetch service status. History may be unavailable.",
      );
    }
  }, [conversationsError]);

  useEffect(() => {
    fetchServiceStatus();
    const intervalId = setInterval(fetchServiceStatus, 15000);
    return () => clearInterval(intervalId);
  }, [fetchServiceStatus]);

  /* --------------------------------------------------------------------- */
  /*  HubSpot auth polling                                                 */
  /* --------------------------------------------------------------------- */
  useEffect(() => {
    const checkAuth = async (isInitialLoad = false) => {
      const { authenticated } = await getHubspotAuthStatus();
      setIsHubspotAuthenticated(authenticated);

      if (isInitialLoad) {
        const pending = localStorage.getItem("pendingHubspotAuth");
        if (pending === "true") {
          localStorage.removeItem("pendingHubspotAuth");
          if (authenticated) setActiveTool("hubspot");
        }
      }
    };

    checkAuth(true);
    const intervalId = setInterval(() => checkAuth(false), 30000);
    return () => clearInterval(intervalId);
  }, []);

  /* --------------------------------------------------------------------- */
  /*  Ollama models                                                        */
  /* --------------------------------------------------------------------- */
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const models = await getOllamaModels();
        setAvailableOllamaModels(models || []);
        if (models?.length) {
          const preferred =
            models.find(
              (m) =>
                !m.toLowerCase().includes("embed") &&
                (m.toLowerCase().includes("instruct") ||
                  m.toLowerCase().includes("chat")),
            ) || models[0];
          setSelectedOllamaModel(preferred);
        } else {
          setSelectedOllamaModel("");
        }
        setOllamaModelsError(null);
      } catch (err) {
        setOllamaModelsError(
          err.detail || err.message || "Failed to load models.",
        );
        setAvailableOllamaModels([]);
        setSelectedOllamaModel("");
      }
    };
    if (ollamaAvailable) {
      fetchModels();
    } else {
      setAvailableOllamaModels([]);
      setSelectedOllamaModel("");
      setOllamaModelsError("Ollama server unavailable.");
    }
  }, [ollamaAvailable]);

  /* --------------------------------------------------------------------- */
  /*  Conversation list (sidebar)                                          */
  /* --------------------------------------------------------------------- */
  const fetchConversationsList = useCallback(async () => {
    setIsConversationsLoading(true);
    setConversationsError(null);
    try {
      const convs = await getConversations();
      setConversations(convs || []);
    } catch (err) {
      setConversationsError(
        err.detail || err.message || "Failed to fetch conversations list.",
      );
      setConversations([]);
    } finally {
      setIsConversationsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (dbConnected) {
      fetchConversationsList();
    } else {
      setConversations([]);
      setIsConversationsLoading(false);
      if (!conversationsError?.includes("status")) {
        setConversationsError(
          "Chat history database (MongoDB) not connected. History is unavailable.",
        );
      }
    }
  }, [dbConnected, fetchConversationsList, conversationsError]);

  /* --------------------------------------------------------------------- */
  /*  Load messages for a conversation                                     */
  /* --------------------------------------------------------------------- */
  useEffect(() => {
    const loadMessages = async () => {
      if (currentConversationId) {
        setIsChatHistoryLoading(true);
        setError(null);
        try {
          const msgs = await getConversationMessages(currentConversationId);
          setChatHistory(msgs || []);
        } catch (err) {
          setError(
            err.detail ||
              err.message ||
              "Failed to load messages for conversation.",
          );
          setChatHistory([initialWelcomeMessage]);
        } finally {
          setIsChatHistoryLoading(false);
        }
      } else {
        setChatHistory([initialWelcomeMessage]);
        setIsChatHistoryLoading(false);
      }
    };
    loadMessages();
  }, [currentConversationId, initialWelcomeMessage]);

  /* --------------------------------------------------------------------- */
  /*  Send / Stream message                                                */
  /* --------------------------------------------------------------------- */
  const handleSendMessage = async (userInput) => {
    /* --- guards -------------------------------------------------------- */
    if (isLoading || isChatHistoryLoading) return;

    const modelForThisMsg = currentConversationId ? null : selectedOllamaModel;

    if (!modelForThisMsg && !currentConversationId) {
      setError("Please select an Ollama model for this new chat.");
      return;
    }
    if (!ollamaAvailable) {
      setError("Ollama server is not available. Cannot start chat.");
      return;
    }

    /* --- begin streaming ---------------------------------------------- */
    setIsLoading(true);
    setError(null);

    // Abort any existing stream
    if (abortControllerRef.current) abortControllerRef.current.abort();
    abortControllerRef.current = new AbortController();

    const payload = {
      user_message: userInput,
      chat_history: chatHistory,
      use_search: activeTool === "search",
      use_database: activeTool === "database",
      use_hubspot: activeTool === "hubspot",
      conversation_id: currentConversationId,
      ollama_model_name: modelForThisMsg,
    };

    // Push user message + assistant placeholder to UI immediately
    const newUserMsg = {
      role: "user",
      content: userInput,
      timestamp: new Date().toISOString(),
    };
    const assistantPlaceholder = {
      role: "assistant",
      content: "",
      is_html: false,
      timestamp: new Date().toISOString(),
    };
    setChatHistory((prev) => [...prev, newUserMsg, assistantPlaceholder]);

    await streamMessage(
      payload,
      {
        onData: (data) => {
          setChatHistory((prev) => {
            const historyCopy = [...prev];
            const last = historyCopy[historyCopy.length - 1];

            if (data.type === "token") {
              last.content += data.content;
            } else if (data.type === "indicator") {
              last.is_html = data.is_html;
              last.content = data.content + last.content;
            } else if (data.type === "done") {
              setChatHistory((prev) => {
                const newHist = [...prev];
                const last = newHist[newHist.length - 1];

                // Overwrite the streamed (possibly duplicated) text with the final version
                if (data.content) {
                  last.content = data.content;
                  last.is_html = data.is_html;
                }

                // If a new conversation was created, reflect its ID
                if (
                  data.conversation_id &&
                  data.conversation_id !== currentConversationId
                ) {
                  setCurrentConversationId(data.conversation_id);
                }
                return newHist;
              });
            }
            return historyCopy;
          });
        },
        onError: (err) => {
          setError(err.message || "An error occurred during streaming.");
        },
        onClose: () => {
          setIsLoading(false);
          abortControllerRef.current = null;
          fetchConversationsList();
        },
      },
      abortControllerRef.current.signal,
    );
  };

  /* --------------------------------------------------------------------- */
  /*  Stop streaming                                                       */
  /* --------------------------------------------------------------------- */
  const handleStopGenerating = () => {
    if (abortControllerRef.current) abortControllerRef.current.abort();
  };

  /* --------------------------------------------------------------------- */
  /*  Conversation / sidebar handlers                                      */
  /* --------------------------------------------------------------------- */
  const handleSelectConversation = (id) => {
    if (id !== currentConversationId) {
      if (abortControllerRef.current) abortControllerRef.current.abort();
      setCurrentConversationId(id);
      setActiveTool(null);
    }
  };

  const handleNewChat = () => {
    if (abortControllerRef.current) abortControllerRef.current.abort();
    setCurrentConversationId(null);
    setChatHistory([initialWelcomeMessage]);
    setActiveTool(null);
    setError(null);
    if (availableOllamaModels.length && !selectedOllamaModel) {
      const preferred =
        availableOllamaModels.find(
          (m) =>
            !m.toLowerCase().includes("embed") &&
            (m.toLowerCase().includes("instruct") ||
              m.toLowerCase().includes("chat")),
        ) || availableOllamaModels[0];
      setSelectedOllamaModel(preferred);
    }
  };

  const handleDeleteConversation = async (id) => {
    if (abortControllerRef.current) abortControllerRef.current.abort();
    setError(null);
    try {
      await deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (currentConversationId === id) handleNewChat();
    } catch (err) {
      setError(err.detail || err.message || "Failed to delete conversation.");
    }
  };

  const handleRenameConversation = async (id, newTitle) => {
    setError(null);
    try {
      const updated = await renameConversation(id, newTitle);
      setConversations((prev) =>
        prev
          .map((c) =>
            c.id === id
              ? { ...c, title: updated.title, updated_at: updated.updated_at }
              : c,
          )
          .sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at)),
      );
    } catch (err) {
      setError(err.detail || err.message || "Failed to rename conversation.");
    }
  };

  /* --------------------------------------------------------------------- */
  /*  Misc helpers                                                         */
  /* --------------------------------------------------------------------- */
  const toggleSidebarCollapse = () => setIsSidebarCollapsed((prev) => !prev);

  const handleHubspotConnect = () => {
    localStorage.setItem("pendingHubspotAuth", "true");
    window.location.href = `${BACKEND_URL}/auth/hubspot/connect`;
  };

  const tools = useMemo(
    () => [
      {
        id: "search",
        name: "Web Search",
        description: "Search the web for up-to-date information.",
        icon: <Search size={24} />,
        isReady: mcpSearchServiceReady,
      },
      {
        id: "database",
        name: "Database Query",
        description: "Ask questions about the connected SQL database.",
        icon: <Database size={24} />,
        isReady: mcpDbServiceReady,
      },
      {
        id: "hubspot",
        name: "HubSpot Actions",
        description: "Create marketing emails in HubSpot.",
        icon: <Share2 size={24} />,
        isReady: mcpHubspotServiceReady,
        isAuthenticated: isHubspotAuthenticated,
      },
    ],
    [
      mcpSearchServiceReady,
      mcpDbServiceReady,
      mcpHubspotServiceReady,
      isHubspotAuthenticated,
    ],
  );

  const currentConversationDetails = useMemo(
    () => conversations.find((c) => c.id === currentConversationId),
    [conversations, currentConversationId],
  );

  const modelForDisplay =
    currentConversationDetails?.ollama_model_name ||
    selectedOllamaModel ||
    "N/A";

  const getChatInputPlaceholder = () => {
    if (!ollamaAvailable) return "Ollama server unavailable...";
    if (
      !selectedOllamaModel &&
      !currentConversationId &&
      availableOllamaModels.length
    )
      return "Select a model to begin...";
    if (activeTool === "search") return "Enter web search query...";
    if (activeTool === "database")
      return "Enter question for database query...";
    if (activeTool === "hubspot")
      return "Describe the HubSpot email to create...";
    return "Type your message...";
  };

  /* --------------------------------------------------------------------- */
  /*  Render                                                               */
  /* --------------------------------------------------------------------- */
  return (
    <div className="flex h-screen bg-brand-main-bg text-brand-text-primary overflow-hidden">
      {/* Sidebar */}
      <ConversationSidebar
        conversations={conversations}
        currentConversationId={currentConversationId}
        onSelectConversation={handleSelectConversation}
        onNewChat={handleNewChat}
        onDeleteConversation={handleDeleteConversation}
        onRenameConversation={handleRenameConversation}
        isLoading={isConversationsLoading}
        dbConnected={dbConnected}
        conversationsError={conversationsError}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={toggleSidebarCollapse}
        mcpSearchServiceReady={mcpSearchServiceReady}
        mcpDbServiceReady={mcpDbServiceReady}
        mcpHubspotServiceReady={mcpHubspotServiceReady}
      />

      {/* Main column */}
      <div className="flex flex-col flex-grow h-screen transition-all duration-300 ease-in-out">
        {/* Header */}
        <header className="p-4 bg-brand-surface-bg shadow-md border-b border-gray-700 flex items-center justify-between">
          <div className="flex items-center">
            <button
              onClick={toggleSidebarCollapse}
              className="p-2 mr-2 rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-brand-purple"
              title={isSidebarCollapsed ? "Open sidebar" : "Close sidebar"}
            >
              {isSidebarCollapsed ? (
                <PanelRightOpen size={20} />
              ) : (
                <PanelLeftClose size={20} />
              )}
            </button>
            <h1 className="text-xl font-semibold text-brand-purple">OhSee</h1>
          </div>

          <div className="text-xs text-brand-text-secondary flex items-center space-x-2 sm:space-x-3 flex-wrap">
            {/* Model select / label */}
            <div className="flex items-center" title="Ollama Model Selection">
              <BrainCircuit
                size={14}
                className={`mr-1 ${
                  ollamaAvailable ? "text-brand-purple" : "text-brand-alert-red"
                }`}
              />
              {!currentConversationId ? (
                <select
                  value={selectedOllamaModel}
                  onChange={(e) => setSelectedOllamaModel(e.target.value)}
                  disabled={
                    !availableOllamaModels.length ||
                    isLoading ||
                    isChatHistoryLoading ||
                    !ollamaAvailable
                  }
                  className="bg-brand-surface-bg text-brand-text-secondary text-xs p-1 rounded border border-gray-600 focus:outline-none focus:ring-1 focus:ring-brand-purple max-w-[120px] sm:max-w-[180px] truncate"
                  title={modelForDisplay}
                >
                  {ollamaModelsError && (
                    <option value="">{ollamaModelsError}</option>
                  )}
                  {!ollamaModelsError && !ollamaAvailable && (
                    <option value="">Ollama N/A</option>
                  )}
                  {!ollamaModelsError &&
                    ollamaAvailable &&
                    availableOllamaModels.length === 0 && (
                      <option value="">No models</option>
                    )}
                  {availableOllamaModels.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              ) : (
                <span
                  className="text-brand-text-secondary max-w-[120px] sm:max-w-[180px] truncate"
                  title={modelForDisplay}
                >
                  Model: {modelForDisplay}
                </span>
              )}
            </div>

            {/* MongoDB status */}
            <span
              className={`flex items-center ${
                dbConnected
                  ? "text-brand-success-green"
                  : "text-brand-alert-red"
              }`}
              title="Chat History DB (MongoDB) Status"
            >
              <Database size={14} className="mr-1" />
              History DB: {dbConnected ? "Conn." : "Disc."}
            </span>
          </div>
        </header>

        {/* Chat area */}
        <div
          ref={chatContainerRef}
          className="flex-grow p-4 overflow-y-auto space-y-2 bg-brand-main-bg"
        >
          {isChatHistoryLoading && (
            <div className="flex justify-center items-center h-full">
              <Loader2 size={32} className="animate-spin text-brand-purple" />
            </div>
          )}

          {!isChatHistoryLoading &&
            chatHistory.map((msg, idx) => (
              <ChatMessage
                key={msg.timestamp ? `${msg.timestamp}-${idx}` : idx}
                message={msg}
              />
            ))}

          {isLoading && !isChatHistoryLoading && (
            <div className="flex justify-start mb-4 animate-pulse">
              <div className="max-w-[70%] p-3 rounded-lg shadow bg-brand-surface-bg text-brand-text-primary rounded-bl-none">
                Thinking with{" "}
                {currentConversationDetails?.ollama_model_name ||
                  selectedOllamaModel}
                ...
              </div>
            </div>
          )}
        </div>

        {/* Error banner */}
        {error && (
          <div className="p-3 bg-brand-alert-red text-white text-sm flex items-center justify-center">
            <AlertTriangle size={18} className="mr-2" /> {error}
          </div>
        )}

        {/* Chat input */}
        <ChatInput
          onSendMessage={handleSendMessage}
          onStopGenerating={handleStopGenerating}
          isLoading={isLoading || isChatHistoryLoading}
          activeTool={activeTool}
          onToggleToolSelector={() =>
            setIsToolSelectorOpen(!isToolSelectorOpen)
          }
          disabled={
            isChatHistoryLoading ||
            isLoading ||
            (!selectedOllamaModel &&
              !currentConversationId &&
              availableOllamaModels.length > 0 &&
              ollamaAvailable) ||
            !ollamaAvailable
          }
          placeholder={getChatInputPlaceholder()}
        />
      </div>

      {/* Tool selector panel */}
      <ToolSelector
        isOpen={isToolSelectorOpen}
        onClose={() => setIsToolSelectorOpen(false)}
        tools={tools}
        activeTool={activeTool}
        onSelectTool={setActiveTool}
        onHubspotConnect={handleHubspotConnect}
      />
    </div>
  );
};

export default App;
