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
import TasksInspector from "./components/TasksInspector";
import SettingsModal from "./components/SettingsModal";
import ModelPickerModal from "./components/ModelPickerModal";
import useKeyboardShortcuts from "./hooks/useKeyboardShortcuts";
import CodexRunCard from "./components/CodexRunCard";
import FileViewerModal from "./components/FileViewerModal";
import {
  sendMessage, // still used for legacy / fall‑back
  streamMessage, // ✨ NEW – SSE streaming
  getServiceStatus,
  getConversations,
  getConversationMessages,
  getOllamaModels,
  getProviderStatus,
  createCodexWorkspace,
  startCodexRun,
  getCodexRun,
  getCodexManifest,
  readCodexFile,
  getAllModels,
  getProviders,
  deleteConversation,
  renameConversation,
  getHubspotAuthStatus,
  BACKEND_URL,
  createTask,
  listTasks,
  getTaskDetail,
  streamTask,
  pauseTask,
  resumeTask,
  cancelTask,
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
  Youtube,
  FileCode,
  ListTodo,
  Settings,
  Sparkles,
} from "lucide-react";

// MCP service names
const WEB_SEARCH_SERVICE_NAME = "web_search_service";
const MYSQL_DB_SERVICE_NAME = "mysql_db_service";
const HUBSPOT_SERVICE_NAME = "hubspot_service";
const YOUTUBE_SERVICE_NAME = "youtube_service";
const PYTHON_SERVICE_NAME = "python_service";

const App = () => {
  // Chat & loading state
  const [chatHistory, setChatHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Tool selector state
  const [activeTool, setActiveTool] = useState(null);
  const [isToolSelectorOpen, setIsToolSelectorOpen] = useState(false);
  const [uploadedCsv, setUploadedCsv] = useState(null); // { filename, data_b64 }

  // Service status state
  const [mcpSearchServiceReady, setMcpSearchServiceReady] = useState(false);
  const [mcpDbServiceReady, setMcpDbServiceReady] = useState(false);
  const [mcpHubspotServiceReady, setMcpHubspotServiceReady] = useState(false);
  const [mcpYoutubeServiceReady, setMcpYoutubeServiceReady] = useState(false);
  const [mcpPythonServiceReady, setMcpPythonServiceReady] = useState(false);
  const [mcpCodexServiceReady, setMcpCodexServiceReady] = useState(false);
  const [openaiConfigured, setOpenaiConfigured] = useState(false);
  const [isHubspotAuthenticated, setIsHubspotAuthenticated] = useState(false);
  const [dbConnected, setDbConnected] = useState(false);
  const [ollamaAvailable, setOllamaAvailable] = useState(false);
  const [activeTasksCount, setActiveTasksCount] = useState(0);

  // Conversation list / sidebar
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [isConversationsLoading, setIsConversationsLoading] = useState(true);
  const [conversationsError, setConversationsError] = useState(null);
  const [isChatHistoryLoading, setIsChatHistoryLoading] = useState(false);

  // Ollama models (backward compatibility)
  const [availableOllamaModels, setAvailableOllamaModels] = useState([]);
  const [selectedOllamaModel, setSelectedOllamaModel] = useState("");
  const [ollamaModelsError, setOllamaModelsError] = useState(null);

  // Multi-provider support
  const [selectedModel, setSelectedModel] = useState("");
  const [selectedProvider, setSelectedProvider] = useState("ollama");
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isModelPickerOpen, setIsModelPickerOpen] = useState(false);

  // Layout
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isTasksOpen, setIsTasksOpen] = useState(false);
  const [promotedGoal, setPromotedGoal] = useState("");
  const [fileViewer, setFileViewer] = useState({ open: false, workspaceId: null });

  // Refs
  const chatContainerRef = useRef(null);
  const abortControllerRef = useRef(null); // ✨ NEW – for cancelling streams
  const processedTokens = useRef(new Set()); // For deduplicating tokens
  const tokenSequence = useRef(0); // Sequence counter for tokens
  const isProcessing = useRef(false); // Flag to prevent double processing
  const currentChatHistory = useRef(chatHistory); // Current chat history ref
  // Update ref when chatHistory changes
  useEffect(() => {
    currentChatHistory.current = chatHistory;
  }, [chatHistory]);
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
      setMcpYoutubeServiceReady(
        status.mcp_services?.[YOUTUBE_SERVICE_NAME]?.ready || false,
      );
      setMcpPythonServiceReady(
        status.mcp_services?.[PYTHON_SERVICE_NAME]?.ready || false,
      );
      setMcpCodexServiceReady(status.mcp_services?.["codex_workspace_service"]?.ready || false);
      setActiveTasksCount(status.tasks?.active || 0);
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
      // Fetch OpenAI provider status for gating Codex tool
      try {
        const prov = await getProviderStatus('openai');
        setOpenaiConfigured(!!prov?.status?.configured);
      } catch (e) {
        setOpenaiConfigured(false);
      }
    } catch {
      setMcpSearchServiceReady(false);
      setMcpDbServiceReady(false);
      setMcpHubspotServiceReady(false);
      setMcpYoutubeServiceReady(false);
      setMcpPythonServiceReady(false);
      setMcpCodexServiceReady(false);
      setOpenaiConfigured(false);
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
  /*  Keyboard shortcuts                                                   */
  /* --------------------------------------------------------------------- */
  useKeyboardShortcuts({
    'ctrl+k': () => {
      // Focus sidebar search
      if (window.focusSidebarSearch) {
        window.focusSidebarSearch();
      }
    }
  });

  /* --------------------------------------------------------------------- */
  /*  Provider Management                                                  */
  /* --------------------------------------------------------------------- */
  const handleModelSelect = (modelName, providerId) => {
    setSelectedModel(modelName);
    setSelectedProvider(providerId);
    
    // Maintain backward compatibility with Ollama
    if (providerId === 'ollama') {
      setSelectedOllamaModel(modelName);
    }
  };

  const handleSettingsUpdate = () => {
    // Refresh provider status or models if needed
    // This could trigger a re-fetch of provider models
  };

  /* --------------------------------------------------------------------- */
  /*  Send / Stream message                                                */
  /* --------------------------------------------------------------------- */
  const handleSendMessage = async (userInput) => {
    /* --- guards -------------------------------------------------------- */
    if (isLoading || isChatHistoryLoading) return;

    // Use selectedModel for new conversations, maintain backward compatibility
    const modelForThisMsg = currentConversationId ? null : (selectedModel || selectedOllamaModel);
    const providerForThisMsg = currentConversationId ? null : selectedProvider;

    if (!modelForThisMsg && !currentConversationId) {
      setError("Please select a model for this new chat.");
      return;
    }
    if (!ollamaAvailable && (!selectedProvider || selectedProvider === 'ollama')) {
      setError("Ollama server is not available. Cannot start chat.");
      return;
    }
    if (activeTool === "python" && !uploadedCsv) {
      const convHasDf = conversations.find(c => c.id === currentConversationId)?.python_df_id;
      if (!convHasDf) {
        setError("Please upload a CSV file to use the Python Analysis tool.");
        return;
      }
    }

    // Codex tool: start workspace run instead of LLM chat
    if (activeTool === 'codex') {
      setIsLoading(true);
      setError(null);
      try {
        const ws = await createCodexWorkspace({ name_hint: currentConversationDetails?.title || 'task', keep: false });
        const wsId = ws.workspace_id || ws.workspaceId || (ws.workspace_path && String(ws.workspace_path).split('/').pop()) || (ws.workspacePath && String(ws.workspacePath).split('/').pop());
        const text = typeof userInput === 'string' ? userInput.trim() : String(userInput || '').trim();
        const start = await startCodexRun({ workspace_id: wsId, instruction: text });
        const runId = start.run_id;
        // Insert inline Codex run message into chat history
        const runMsg = {
          role: 'assistant',
          type: 'codex_run',
          run_id: runId,
          workspace_id: wsId,
          status: 'queued',
          summary: '',
          timestamp: new Date().toISOString(),
        };
        setChatHistory((prev) => [...prev, { role: 'user', content: userInput, timestamp: new Date().toISOString() }, runMsg]);
        // Poll for status
        const poll = async () => {
          try {
            const status = await getCodexRun(runId);
            const run = status.run || {};
            // Update the inline codex_run message
            setChatHistory((prev) => prev.map(m => (m.type === 'codex_run' && m.run_id === runId) ? { ...m, status: run.status || m.status, summary: run.summary || m.summary } : m));
            if (run.status === 'completed' || run.status === 'failed') {
              const summary = run.summary || (run.status === 'completed' ? 'Codex run completed.' : (run.error_message || 'Codex run failed.'));
              setChatHistory((prev) => {
                const copy = [...prev];
                for (let i = copy.length - 1; i >= 0; i--) {
                  if (copy[i].role === 'assistant') { copy[i] = { ...copy[i], content: `[Codex] ${summary}` }; break; }
                }
                return copy;
              });
              setIsLoading(false);
              return;
            }
            setTimeout(poll, 1000);
          } catch (e) {
            setTimeout(poll, 1500);
          }
        };
        poll();
      } catch (e) {
        setError(e?.detail || e?.message || 'Failed to start Codex run');
        setIsLoading(false);
      }
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
      use_youtube: activeTool === "youtube",
      use_python: activeTool === "python",
      csv_data_b64: activeTool === "python" && uploadedCsv ? uploadedCsv.data_b64 : null,
      conversation_id: currentConversationId,
      model_name: modelForThisMsg,
      provider: providerForThisMsg,
      // Backward compatibility
      ollama_model_name: selectedProvider === 'ollama' ? modelForThisMsg : null,
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

    // Clear one-time-use data after preparing payload
    if (activeTool === "python" && uploadedCsv) {
      setUploadedCsv(null);
    }

    await streamMessage(
      payload,
      {
        onData: (data) => {
          setChatHistory((prev) => {
            // Simple deduplication check
            const last = prev[prev.length - 1];
            if (data.type === "token" && last && last.content.endsWith(data.content)) {
              return prev; // No change
            }
            
            const historyCopy = [...prev];
            const lastMessage = historyCopy[historyCopy.length - 1];

            if (data.type === "indicator") {
              lastMessage.indicator = data.content;
              lastMessage.is_html = data.is_html;
            } else if (data.type === "token") {
              lastMessage.content += data.content;
            } else if (data.type === "done") {
              lastMessage.is_html = data.is_html;
              
              // If a new conversation was created, reflect its ID
              if (
                data.conversation_id &&
                data.conversation_id !== currentConversationId
              ) {
                setCurrentConversationId(data.conversation_id);
              }
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
      setUploadedCsv(null);
    }
  };

  const handleNewChat = () => {
    if (abortControllerRef.current) abortControllerRef.current.abort();
    setCurrentConversationId(null);
    setChatHistory([initialWelcomeMessage]);
    setActiveTool(null);
    setUploadedCsv(null);
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

  const handleFileChange = (file) => {
    if (!file) {
      setUploadedCsv(null);
      return;
    }
    const reader = new FileReader();
    reader.onload = (e) => {
      const b64 = e.target.result.split(",")[1];
      setUploadedCsv({ filename: file.name, data_b64: b64 });
    };
    reader.readAsDataURL(file);
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
        id: "python",
        name: "Python Analysis",
        description: "Upload a CSV and ask questions about the data.",
        icon: <FileCode size={24} />,
        isReady: mcpPythonServiceReady,
      },
      {
        id: "codex",
        name: "Codex (Workspace)",
        description: openaiConfigured ? "Generate files in an isolated workspace." : "Requires OpenAI API key.",
        icon: <Sparkles size={24} />,
        isReady: mcpCodexServiceReady && openaiConfigured,
      },
      {
        id: "hubspot",
        name: "HubSpot Actions",
        description: "Create marketing emails in HubSpot.",
        icon: <Share2 size={24} />,
        isReady: mcpHubspotServiceReady,
        isAuthenticated: isHubspotAuthenticated,
      },
      {
        id: "youtube",
        name: "YouTube Transcript",
        description: "Get the transcript from a YouTube video URL.",
        icon: <Youtube size={24} />,
        isReady: mcpYoutubeServiceReady,
      },
    ],
    [
      mcpSearchServiceReady,
      mcpDbServiceReady,
      mcpHubspotServiceReady,
      mcpYoutubeServiceReady,
      mcpPythonServiceReady,
      mcpCodexServiceReady,
      openaiConfigured,
      isHubspotAuthenticated,
    ],
  );

  const currentConversationDetails = useMemo(
    () => conversations.find((c) => c.id === currentConversationId),
    [conversations, currentConversationId],
  );

  const modelForDisplay =
    currentConversationDetails?.model_name ||
    currentConversationDetails?.ollama_model_name ||
    selectedModel ||
    selectedOllamaModel ||
    "N/A";

  const getChatInputPlaceholder = () => {
    if (!ollamaAvailable && selectedProvider === 'ollama') return "Ollama server unavailable...";
    if (
      !selectedModel &&
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
    if (activeTool === "youtube")
      return "Enter a YouTube video URL to get the transcript...";
    if (activeTool === "python")
      return "Upload a CSV and ask a question about it...";
    return "Type your message...";
  };

  /* --------------------------------------------------------------------- */
  /*  Render                                                               */
  /* --------------------------------------------------------------------- */
  return (
    <div className="grid grid-cols-[auto_1fr_auto] h-screen bg-brand-main-bg text-brand-text-primary overflow-hidden">
      {/* Left Column - Sidebar */}
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
        mcpYoutubeServiceReady={mcpYoutubeServiceReady}
        mcpPythonServiceReady={mcpPythonServiceReady}
        mcpCodexServiceReady={mcpCodexServiceReady}
        openaiConfigured={openaiConfigured}
      />

      {/* Center Column - Main chat area */}
      <div className="flex flex-col h-screen transition-all duration-300 ease-in-out min-w-0">
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
            <div className="flex items-center" title="Model Selection">
              <BrainCircuit size={14} className="mr-1 text-brand-purple" />
              {!currentConversationId ? (
                <button
                  onClick={() => setIsModelPickerOpen(true)}
                  className="px-2 py-1 text-xs rounded bg-gray-700 hover:bg-gray-600 text-white"
                >
                  {modelForDisplay ? `Model: ${modelForDisplay}` : 'Select Model'}
                </button>
              ) : (
                <span className="text-brand-text-secondary max-w-[180px] truncate" title={modelForDisplay}>
                  Model: {modelForDisplay}
                </span>
              )}
            </div>

            {/* History DB indicator moved to sidebar */}

            {/* Tasks button */}
            <button
              onClick={() => setIsTasksOpen(true)}
              title="Open Tasks"
              className={`flex items-center gap-1 px-2 py-1 text-xs rounded bg-gray-700 hover:bg-gray-600 text-white transition-opacity duration-300 ${
                isTasksOpen ? 'opacity-0 pointer-events-none' : 'opacity-100'
              }`}
            >
              <ListTodo size={14} /> Tasks{activeTasksCount ? ` (${activeTasksCount})` : ""}
            </button>

            {/* Settings button */}
            <button
              onClick={() => setIsSettingsOpen(true)}
              title="Provider Settings"
              className="flex items-center gap-1 px-2 py-1 text-xs rounded bg-gray-700 hover:bg-gray-600 text-white"
            >
              <Settings size={14} /> Settings
            </button>
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
                isStreaming={isLoading && idx === chatHistory.length - 1 && msg.role === 'assistant'}
                onPromoteToTask={(goalText) => {
                  setPromotedGoal(goalText || "");
                  setIsTasksOpen(true);
                }}
              />
            ))}

          {isLoading && !isChatHistoryLoading && (
            <div className="flex justify-start mb-4 animate-pulse">
              <div className="max-w-[70%] p-3 rounded-lg shadow bg-brand-surface-bg text-brand-text-primary rounded-bl-none">
                Thinking with{" "}
                {currentConversationDetails?.model_name ||
                  currentConversationDetails?.ollama_model_name ||
                  selectedModel ||
                  selectedOllamaModel}
                ...
              </div>
            </div>
          )}

          {/* Inline Codex run messages are rendered as part of chat history above */}
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
          onFileChange={handleFileChange}
          uploadedFile={uploadedCsv}
          onClearFile={() => setUploadedCsv(null)}
        />
      </div>

      {/* Right Column - Tasks Inspector */}
      <TasksInspector
        isOpen={isTasksOpen}
        onClose={() => setIsTasksOpen(false)}
        initialGoal={promotedGoal}
        conversationId={currentConversationId}
        defaultConversationModel={currentConversationDetails?.model_name || currentConversationDetails?.ollama_model_name || selectedModel || selectedOllamaModel || null}
      />

      {/* Tool selector panel */}
      <ToolSelector
        isOpen={isToolSelectorOpen}
        onClose={() => setIsToolSelectorOpen(false)}
        tools={tools}
        activeTool={activeTool}
        onSelectTool={setActiveTool}
        onHubspotConnect={handleHubspotConnect}
      />

      {/* Settings modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        onSettingsUpdate={handleSettingsUpdate}
      />

      {/* Model Picker Modal */}
      <ModelPickerModal
        isOpen={isModelPickerOpen}
        onClose={() => setIsModelPickerOpen(false)}
        onSelectModel={(fullName, providerId) => {
          handleModelSelect(fullName, providerId);
          setIsModelPickerOpen(false);
        }}
        currentModel={selectedModel || selectedOllamaModel}
        onOpenSettings={() => setIsSettingsOpen(true)}
      />

      {/* File Viewer Modal (optional future enablement) */}
      <FileViewerModal
        isOpen={fileViewer.open}
        onClose={() => setFileViewer({ open: false, workspaceId: null })}
        workspaceId={fileViewer.workspaceId}
        fetchManifest={getCodexManifest}
        fetchFile={readCodexFile}
      />
    </div>
  );
};

export default App;
