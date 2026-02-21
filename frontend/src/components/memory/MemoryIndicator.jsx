import React, { useState, useEffect } from 'react';
import { getMemoryStatus } from '../../services/api';

export default function MemoryIndicator({ conversationId }) {
  const [status, setStatus] = useState(null);
  const [showTooltip, setShowTooltip] = useState(false);

  useEffect(() => {
    if (!conversationId) return;

    const checkStatus = async () => {
      try {
        const data = await getMemoryStatus(conversationId);
        setStatus(data);
      } catch (error) {
        // Silently fail - conversation might not be indexed yet
      }
    };

    checkStatus();
    const interval = setInterval(checkStatus, 30000); // Check every 30s

    return () => clearInterval(interval);
  }, [conversationId]);

  if (!status || !status.indexed) return null;

  const indexedDate = status.indexed_at ? new Date(status.indexed_at).toLocaleDateString() : 'Unknown';

  return (
    <div 
      className="memory-indicator"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <span className="memory-badge">🧠 In Memory</span>
      {showTooltip && (
        <div className="memory-tooltip">
          <div>Indexed: {indexedDate}</div>
          <div>Messages: {status.message_count}</div>
        </div>
      )}
    </div>
  );
}
