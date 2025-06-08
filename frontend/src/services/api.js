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
  ollamaModelName = null,
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
    if (ollamaModelName && !conversationId) {
      payload.ollama_model_name = ollamaModelName;
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
