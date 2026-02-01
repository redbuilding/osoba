import React from 'react';

const GenerateSummaryModal = ({ isOpen, onConfirm, onCancel, isGenerating }) => {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="bg-brand-surface-bg border border-gray-700 rounded-xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden">
        <div className="p-4 border-b border-gray-700">
          <h3 className="text-lg font-semibold text-brand-text-primary">Generate AI Summary</h3>
        </div>
        <div className="p-4 text-brand-text-secondary text-sm space-y-2">
          <p>
            This chat doesn’t have a summary yet. Generate a concise AI summary (max 750 characters) using your configured summary model?
          </p>
          <p>
            The app will pause other activity until the summary is finished to avoid conflicts.
          </p>
        </div>
        <div className="p-4 bg-brand-main-bg border-t border-gray-700 flex justify-end gap-2">
          <button
            onClick={onCancel}
            disabled={isGenerating}
            className="px-3 py-1.5 rounded bg-gray-700 text-white hover:bg-gray-600 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isGenerating}
            className="px-3 py-1.5 rounded bg-brand-purple text-white hover:bg-brand-button-grad-to disabled:opacity-50"
          >
            {isGenerating ? 'Generating…' : 'Generate'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default GenerateSummaryModal;

