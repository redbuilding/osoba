import React, { useState } from 'react';
import { saveConversationToMemory } from '../../services/api';

export default function SaveToMemoryButton({ conversationId, messageCount }) {
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  if (messageCount < 5) return null;

  const handleSave = async () => {
    setSaving(true);
    try {
      await saveConversationToMemory(conversationId);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (error) {
      console.error('Error saving to memory:', error);
    } finally {
      setSaving(false);
    }
  };

  return (
    <button
      onClick={handleSave}
      disabled={saving || saved}
      className="memory-save-button"
      title="Save this conversation to semantic memory for future reference"
    >
      {saving ? '💾 Saving...' : saved ? '✓ Saved' : '💾 Save to Memory'}
    </button>
  );
}
