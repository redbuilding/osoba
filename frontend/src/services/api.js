// frontend/src/services/api.js
import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

// The base URL for the backend, without the /api suffix.
// Useful for hitting auth endpoints that are not under /api.
export const BACKEND_URL = API_URL.endsWith("/api")
  ? API_URL.slice(0, -4)
  : API_URL;

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true,
});

/**
 * Classic, non‑streaming chat call.
 */
export const sendMessage = async (
  userMessage,
  chatHistory,
  useSearch,
  useDatabase,
  useHubspot,
  conversationId = null,
  modelName = null,
  provider = null,
) => {
  try {
    const payload = {
      user_message: userMessage,
      chat_history: chatHistory,
      use_search: useSearch,
      use_database: useDatabase,
      use_hubspot: useHubspot,
      conversation_id: conversationId,
    };
    if (modelName && !conversationId) {
      payload.model_name = modelName;
    }
    if (provider && !conversationId) {
      payload.provider = provider;
    }
    const response = await apiClient.post("/chat", payload);
    return response.data;
  } catch (error) {
    console.error(
      "Error sending message:",
      error.response ? error.response.data : error.message,
    );
    throw error.response
      ? error.response.data
      : new Error("Network error or server unavailable");
  }
};

/**
 * NEW – streaming chat with AbortController support.
 *
 * @param {object} payload   Same payload shape used in sendMessage.
 * @param {object} callbacks { onData, onError, onClose }
 * @param {AbortSignal} signal The signal from an AbortController.
 */
export const streamMessage = async (payload, callbacks, signal) => {
  try {
    const response = await fetch(`${API_URL}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal, // Link fetch to the AbortController
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || "Server error");
    }

    // Stream response.body via reader
    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const textChunk = decoder.decode(value, { stream: true });
      // SSE payloads are separated by blank lines
      const events = textChunk
        .split("\n\n")
        .map((e) => e.trim())
        .filter(Boolean);

      for (const evt of events) {
        if (evt.startsWith("data: ")) {
          const jsonData = evt.slice(6);
          try {
            const parsed = JSON.parse(jsonData);
            callbacks.onData && callbacks.onData(parsed);
          } catch (parseErr) {
            console.error("Failed to parse SSE data:", jsonData);
          }
        }
      }
    }
  } catch (error) {
    if (error.name === "AbortError") {
      console.log("Stream aborted by user.");
    } else {
      callbacks.onError && callbacks.onError(error);
    }
  } finally {
    callbacks.onClose && callbacks.onClose();
  }
};

export const getServiceStatus = async () => {
  try {
    const response = await apiClient.get("/status");
    return response.data;
  } catch (error) {
    console.error(
      "Error fetching service status:",
      error.response ? error.response.data : error.message,
    );
    throw error.response
      ? error.response.data
      : new Error("Network error or server unavailable");
  }
};

export const getHubspotAuthStatus = async () => {
  try {
    const response = await apiClient.get("/auth/hubspot/status");
    return response.data; // Expected: { authenticated: bool }
  } catch (error) {
    console.error(
      "Error fetching HubSpot auth status:",
      error.response ? error.response.data : error.message,
    );
    // Assume not authenticated on error to be safe
    return { authenticated: false };
  }
};

export const getOllamaModels = async () => {
  try {
    const response = await apiClient.get("/ollama-models");
    return response.data;
  } catch (error) {
    console.error(
      "Error fetching Ollama models:",
      error.response ? error.response.data : error.message,
    );
    throw error.response
      ? error.response.data
      : new Error("Network error or server unavailable fetching Ollama models");
  }
};

export const getConversations = async () => {
  try {
    const response = await apiClient.get("/conversations");
    return response.data;
  } catch (error) {
    console.error(
      "Error fetching conversations:",
      error.response ? error.response.data : error.message,
    );
    throw error.response
      ? error.response.data
      : new Error("Network error or server unavailable");
  }
};

export const searchConversations = async (query, limit = 20) => {
  try {
    const response = await apiClient.get("/conversations/search", {
      params: { q: query, limit }
    });
    return response.data;
  } catch (error) {
    console.error(
      "Error searching conversations:",
      error.response ? error.response.data : error.message,
    );
    throw error.response
      ? error.response.data
      : new Error("Network error or server unavailable");
  }
};

export const getConversationMessages = async (conversationId) => {
  try {
    const response = await apiClient.get(`/conversations/${conversationId}`);
    return response.data;
  } catch (error) {
    console.error(
      `Error fetching messages for conversation ${conversationId}:`,
      error.response ? error.response.data : error.message,
    );
    throw error.response
      ? error.response.data
      : new Error("Network error or server unavailable");
  }
};

export const deleteConversation = async (conversationId) => {
  try {
    const response = await apiClient.delete(`/conversations/${conversationId}`);
    return response.data;
  } catch (error) {
    console.error(
      `Error deleting conversation ${conversationId}:`,
      error.response ? error.response.data : error.message,
    );
    throw error.response
      ? error.response.data
      : new Error("Network error or server unavailable");
  }
};

export const renameConversation = async (conversationId, newTitle) => {
  try {
    const response = await apiClient.put(
      `/conversations/${conversationId}/rename`,
      { new_title: newTitle },
    );
    return response.data;
  } catch (error) {
    console.error(
      `Error renaming conversation ${conversationId}:`,
      error.response ? error.response.data : error.message,
    );
    throw error.response
      ? error.response.data
      : new Error("Network error or server unavailable");
  }
};

// ---------- Long-running Tasks API ----------

export const createTask = async (payload) => {
  try {
    const response = await apiClient.post("/tasks", payload);
    return response.data;
  } catch (error) {
    throw error.response ? error.response.data : new Error("Network error");
  }
};

export const listTasks = async () => {
  try {
    const response = await apiClient.get("/tasks");
    return response.data;
  } catch (error) {
    throw error.response ? error.response.data : new Error("Network error");
  }
};

export const getTaskDetail = async (taskId) => {
  try {
    const response = await apiClient.get(`/tasks/${taskId}`);
    return response.data;
  } catch (error) {
    throw error.response ? error.response.data : new Error("Network error");
  }
};

export const streamTask = async (taskId, callbacks, signal) => {
  try {
    const response = await fetch(`${API_URL}/tasks/${taskId}/stream`, {
      method: "GET",
      headers: { "Accept": "text/event-stream" },
      signal,
      credentials: "include",
    });
    if (!response.ok) throw new Error("Task stream error");

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const textChunk = decoder.decode(value, { stream: true });
      const events = textChunk
        .split("\n\n")
        .map((e) => e.trim())
        .filter(Boolean);
      for (const evt of events) {
        if (evt.startsWith("data: ")) {
          const jsonData = evt.slice(6);
          try {
            const parsed = JSON.parse(jsonData);
            callbacks.onData && callbacks.onData(parsed);
          } catch (e) {
            console.error("Bad SSE JSON:", jsonData);
          }
        }
      }
    }
  } catch (err) {
    if (err.name !== "AbortError") callbacks.onError && callbacks.onError(err);
  } finally {
    callbacks.onClose && callbacks.onClose();
  }
};

export const pauseTask = async (taskId) => {
  try {
    const res = await apiClient.post(`/tasks/${taskId}/pause`);
    return res.data;
  } catch (error) {
    throw error.response ? error.response.data : new Error("Network error");
  }
};

export const resumeTask = async (taskId) => {
  try {
    const res = await apiClient.post(`/tasks/${taskId}/resume`);
    return res.data;
  } catch (error) {
    throw error.response ? error.response.data : new Error("Network error");
  }
};

export const cancelTask = async (taskId) => {
  try {
    const res = await apiClient.post(`/tasks/${taskId}/cancel`);
    return res.data;
  } catch (error) {
    throw error.response ? error.response.data : new Error("Network error");
  }
};

export const deleteTask = async (taskId) => {
  try {
    const res = await apiClient.delete(`/tasks/${taskId}`);
    return res.data;
  } catch (error) {
    throw error.response ? error.response.data : new Error("Network error");
  }
};

// ---------- Scheduled Tasks API ----------

export const createScheduledTask = async (payload) => {
  try {
    const response = await apiClient.post("/scheduled-tasks", payload);
    return response.data;
  } catch (error) {
    console.error("Error creating scheduled task:", error);
    throw error;
  }
};

export const listScheduledTasks = async () => {
  try {
    const response = await apiClient.get("/scheduled-tasks");
    return response.data;
  } catch (error) {
    console.error("Error listing scheduled tasks:", error);
    throw error;
  }
};

export const deleteScheduledTask = async (taskId) => {
  try {
    const response = await apiClient.delete(`/scheduled-tasks/${taskId}`);
    return response.data;
  } catch (error) {
    console.error("Error deleting scheduled task:", error);
    throw error;
  }
};

export const runScheduledTaskNow = async (taskId, modelName = null) => {
  try {
    const response = await apiClient.post(`/scheduled-tasks/${taskId}/run`, modelName ? { model_name: modelName } : {});
    return response.data;
  } catch (error) {
    console.error("Error running scheduled task now:", error);
    throw error;
  }
};

export const improveScheduledInstruction = async ({ draft_text, model_name = null, mode = 'Clarify', language = null, context_hints = null }) => {
  try {
    const response = await apiClient.post(`/scheduled-tasks/improve-instruction`, {
      draft_text,
      model_name,
      mode,
      language,
      context_hints,
      task_type: 'scheduled'
    });
    return response.data;
  } catch (error) {
    console.error("Error improving instruction:", error);
    throw error;
  }
};

// ---------- Templates API ----------

export const listTemplates = async (category = null) => {
  try {
    const params = category ? { category } : {};
    const response = await apiClient.get("/templates", { params });
    return response.data;
  } catch (error) {
    console.error("Error listing templates:", error);
    throw error;
  }
};

export const getDefaultTemplates = async () => {
  try {
    const response = await apiClient.get("/templates/default");
    return response.data;
  } catch (error) {
    console.error("Error getting default templates:", error);
    throw error;
  }
};

export const createTemplate = async (template) => {
  try {
    const response = await apiClient.post("/templates", template);
    return response.data;
  } catch (error) {
    console.error("Error creating template:", error);
    throw error;
  }
};

export const createTaskFromTemplate = async (templateId, payload) => {
  try {
    const response = await apiClient.post(`/templates/${templateId}/create-task`, payload);
    return response.data;
  } catch (error) {
    console.error("Error creating task from template:", error);
    throw error;
  }
};

export const getTemplateParameters = async (templateId) => {
  try {
    const response = await apiClient.get(`/templates/${templateId}/parameters`);
    return response.data;
  } catch (error) {
    console.error("Error getting template parameters:", error);
    throw error;
  }
};

// Provider management functions
export const getProviders = async () => {
  try {
    const response = await apiClient.get("/providers");
    return response.data;
  } catch (error) {
    console.error("Error fetching providers:", error);
    throw error.response
      ? error.response.data
      : new Error("Network error or server unavailable");
  }
};

export const getProviderModels = async () => {
  try {
    const response = await apiClient.get("/providers/models");
    return response.data;
  } catch (error) {
    console.error("Error fetching provider models:", error);
    throw error.response
      ? error.response.data
      : new Error("Network error or server unavailable");
  }
};

export const getProviderStatus = async (providerId) => {
  try {
    const response = await apiClient.get(`/providers/${providerId}/status`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching provider ${providerId} status:`, error);
    throw error.response
      ? error.response.data
      : new Error("Network error or server unavailable");
  }
};

export const saveProviderSettings = async (provider, apiKey) => {
  try {
    const response = await apiClient.post("/providers/settings", {
      provider,
      api_key: apiKey
    });
    return response.data;
  } catch (error) {
    console.error("Error saving provider settings:", error);
    throw error.response
      ? error.response.data
      : new Error("Network error or server unavailable");
  }
};

export const removeProviderSettings = async (providerId) => {
  try {
    const response = await apiClient.delete(`/providers/${providerId}/settings`);
    return response.data;
  } catch (error) {
    console.error(`Error removing provider ${providerId} settings:`, error);
    throw error.response
      ? error.response.data
      : new Error("Network error or server unavailable");
  }
};

export const validateProviderSettings = async (providerId) => {
  try {
    const response = await apiClient.get(`/providers/${providerId}/validate`);
    return response.data;
  } catch (error) {
    console.error(`Error validating provider ${providerId} settings:`, error);
    throw error.response
      ? error.response.data
      : new Error("Network error or server unavailable");
  }
};

export const getUserSettings = async () => {
  try {
    const response = await apiClient.get("/settings");
    return response.data;
  } catch (error) {
    console.error("Error fetching user settings:", error);
    throw error.response
      ? error.response.data
      : new Error("Network error or server unavailable");
  }
};

// ----- Codex MCP API -----
export const createCodexWorkspace = async ({ name_hint, keep = false }) => {
  const response = await apiClient.post('/codex/workspaces', { name_hint, keep });
  const data = response.data || {};
  if (Array.isArray(data)) {
    const txt = (data[0] && data[0].content) || '';
    try {
      return JSON.parse(txt);
    } catch (e) {
      return { raw: data };
    }
  }
  return data;
};

export const startCodexRun = async ({ workspace_id, instruction, model = null, timeout_seconds = 900 }) => {
  const payload = {
    workspace_id,
    workspaceId: workspace_id, // tolerant for backend variants
    instruction: typeof instruction === 'string' ? instruction : String(instruction || ''),
    timeout_seconds,
    timeoutSeconds: timeout_seconds,
  };
  if (model) payload.model = model;
  const response = await apiClient.post('/codex/runs', payload);
  return response.data;
};

export const getCodexRun = async (run_id) => {
  const response = await apiClient.get(`/codex/runs/${run_id}`);
  return response.data;
};

export const cancelCodexRun = async (run_id) => {
  const response = await apiClient.post(`/codex/runs/${run_id}/cancel`);
  return response.data;
};

export const getCodexManifest = async (workspace_id) => {
  const response = await apiClient.get(`/codex/workspaces/${workspace_id}/manifest`);
  return response.data;
};

export const readCodexFile = async (workspace_id, relative_path) => {
  const response = await apiClient.get(`/codex/workspaces/${workspace_id}/file`, { params: { relative_path } });
  return response.data;
};

// Enhanced model listing that includes all providers
export const getAllModels = async () => {
  try {
    const response = await apiClient.get("/models");
    return response.data;
  } catch (error) {
    console.error("Error fetching all models:", error);
    // Fallback to Ollama models for backward compatibility
    try {
      const ollamaModels = await getOllamaModels();
      return {
        models: ollamaModels.map(model => ({
          name: model,
          provider: 'ollama',
          available: true
        })),
        providers: {
          ollama: {
            name: 'Ollama',
            available: true,
            configured: true
          }
        }
      };
    } catch (fallbackError) {
      throw error.response
        ? error.response.data
        : new Error("Network error or server unavailable");
    }
  }
};

// AI Profile Management
export const getProfiles = async () => {
  try {
    const response = await apiClient.get("/profiles");
    return response.data;
  } catch (error) {
    console.error("Error fetching profiles:", error);
    throw error.response
      ? error.response.data
      : new Error("Network error or server unavailable");
  }
};

export const getActiveProfile = async () => {
  try {
    const response = await apiClient.get("/profiles/active");
    return response.data;
  } catch (error) {
    console.error("Error fetching active profile:", error);
    throw error.response
      ? error.response.data
      : new Error("Network error or server unavailable");
  }
};

export const getProfile = async (profileId) => {
  try {
    const response = await apiClient.get(`/profiles/${profileId}`);
    return response.data;
  } catch (error) {
    console.error("Error fetching profile:", error);
    throw error.response
      ? error.response.data
      : new Error("Network error or server unavailable");
  }
};

export const createProfile = async (profileData) => {
  try {
    const response = await apiClient.post("/profiles", profileData);
    return response.data;
  } catch (error) {
    console.error("Error creating profile:", error);
    throw error.response
      ? error.response.data
      : new Error("Network error or server unavailable");
  }
};

export const updateProfile = async (profileId, profileData) => {
  try {
    const response = await apiClient.put(`/profiles/${profileId}`, profileData);
    return response.data;
  } catch (error) {
    console.error("Error updating profile:", error);
    throw error.response
      ? error.response.data
      : new Error("Network error or server unavailable");
  }
};

export const deleteProfile = async (profileId) => {
  try {
    const response = await apiClient.delete(`/profiles/${profileId}`);
    return response.data;
  } catch (error) {
    console.error("Error deleting profile:", error);
    throw error.response
      ? error.response.data
      : new Error("Network error or server unavailable");
  }
};

export const activateProfile = async (profileId) => {
  try {
    const response = await apiClient.post(`/profiles/${profileId}/activate`);
    return response.data;
  } catch (error) {
    console.error("Error activating profile:", error);
    throw error.response
      ? error.response.data
      : new Error("Network error or server unavailable");
  }
};

export const deactivateAllProfiles = async () => {
  try {
    const response = await apiClient.post("/profiles/deactivate");
    return response.data;
  } catch (error) {
    console.error("Error deactivating profiles:", error);
    throw error.response
      ? error.response.data
      : new Error("Network error or server unavailable");
  }
};

// ---------- Artifacts API ----------

export const saveArtifact = async (payload) => {
  try {
    const response = await apiClient.post("/artifacts", payload);
    return response.data;
  } catch (error) {
    console.error("Error saving artifact:", error.response ? error.response.data : error.message);
    throw error.response ? error.response.data : new Error("Network error");
  }
};

export const getArtifactCapabilities = async () => {
  try {
    const response = await apiClient.get("/artifacts/capabilities");
    return response.data;
  } catch (error) {
    return { html: false, docx: false, pdf: false };
  }
};

// ---------- User Context API ----------

export const getUserContext = async () => {
  try {
    const response = await apiClient.get("/user-context/profile");
    return response.data;
  } catch (error) {
    console.error("Error getting user context:", error);
    throw error.response
      ? error.response.data
      : new Error("Network error or server unavailable");
  }
};

export const pinConversation = async (conversationId, pinned = true) => {
  try {
    const response = await apiClient.post("/user-context/pin-conversation", {
      conversation_id: conversationId,
      pinned: pinned
    });
    return response.data;
  } catch (error) {
    console.error("Error pinning conversation:", error);
    throw error.response
      ? error.response.data
      : new Error("Network error or server unavailable");
  }
};

export const getPinStats = async () => {
  try {
    const response = await apiClient.get("/user-context/pin-stats");
    return response.data; // { count, max }
  } catch (error) {
    console.error("Error getting pin stats:", error);
    return { count: 0, max: 5 };
  }
};

export const getPinnedConversations = async () => {
  try {
    const response = await apiClient.get("/user-context/pinned-conversations");
    return response.data;
  } catch (error) {
    console.error("Error getting pinned conversations:", error);
    throw error.response
      ? error.response.data
      : new Error("Network error or server unavailable");
  }
};

export const updateConversationSummary = async (conversationId, summary) => {
  try {
    const response = await apiClient.post("/user-context/conversation-summary", {
      conversation_id: conversationId,
      summary: summary
    });
    return response.data;
  } catch (error) {
    console.error("Error updating conversation summary:", error);
    throw error.response
      ? error.response.data
      : new Error("Network error or server unavailable");
  }
};

// ---------- Summaries API ----------

export const getSummarySettings = async () => {
  try {
    const response = await apiClient.get("/summaries/settings");
    return response.data; // { model_name }
  } catch (error) {
    console.error("Error getting summary settings:", error);
    return { model_name: "" };
  }
};

export const saveSummarySettings = async (modelName) => {
  try {
    const response = await apiClient.post("/summaries/settings", { model_name: modelName });
    return response.data;
  } catch (error) {
    console.error("Error saving summary settings:", error);
    throw error.response ? error.response.data : new Error("Network error or server unavailable");
  }
};

export const generateChatSummary = async (conversationId) => {
  try {
    const response = await apiClient.post("/summaries/generate", { conversation_id: conversationId });
    return response.data; // { success, summary }
  } catch (error) {
    console.error("Error generating chat summary:", error);
    throw error.response ? error.response.data : new Error("Network error or server unavailable");
  }
};

// ---------- User Profile API ----------

export const getUserProfile = async () => {
  try {
    const response = await apiClient.get("/user-profile");
    return response.data; // { success, profile }
  } catch (error) {
    console.error("Error getting user profile:", error);
    throw error.response ? error.response.data : new Error("Network error or server unavailable");
  }
};

export const saveUserProfile = async (profile) => {
  try {
    const response = await apiClient.put("/user-profile", profile);
    return response.data; // { success, profile }
  } catch (error) {
    console.error("Error saving user profile:", error);
    throw error.response ? error.response.data : new Error("Network error or server unavailable");
  }
};

export const deleteUserProfile = async () => {
  try {
    const response = await apiClient.delete("/user-profile");
    return response.data; // { success }
  } catch (error) {
    console.error("Error deleting user profile:", error);
    throw error.response ? error.response.data : new Error("Network error or server unavailable");
  }
};
