import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export const getInsights = async (userId = 'default', dismissed = null) => {
  try {
    const params = { user_id: userId };
    if (dismissed !== null) {
      params.dismissed = dismissed;
    }
    const response = await axios.get(`${API_URL}/heartbeat/insights`, { params });
    return response.data.insights || [];
  } catch (error) {
    console.error('Error fetching insights:', error);
    throw error;
  }
};

export const dismissInsight = async (insightId, userId = 'default') => {
  try {
    const response = await axios.post(
      `${API_URL}/heartbeat/insights/${insightId}/dismiss`,
      null,
      { params: { user_id: userId } }
    );
    return response.data;
  } catch (error) {
    console.error('Error dismissing insight:', error);
    throw error;
  }
};

export const getHeartbeatConfig = async (userId = 'default') => {
  try {
    const response = await axios.get(`${API_URL}/heartbeat/config`, {
      params: { user_id: userId }
    });
    return response.data.config || {};
  } catch (error) {
    console.error('Error fetching heartbeat config:', error);
    throw error;
  }
};

export const updateHeartbeatConfig = async (config, userId = 'default') => {
  try {
    const response = await axios.put(
      `${API_URL}/heartbeat/config`,
      config,
      { params: { user_id: userId } }
    );
    return response.data.config || {};
  } catch (error) {
    console.error('Error updating heartbeat config:', error);
    throw error;
  }
};

export const triggerHeartbeat = async (userId = 'default') => {
  try {
    const response = await axios.post(`${API_URL}/heartbeat/trigger`, null, {
      params: { user_id: userId }
    });
    return response.data;
  } catch (error) {
    console.error('Error triggering heartbeat:', error);
    throw error;
  }
};
