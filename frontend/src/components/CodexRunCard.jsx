import React from 'react';
import { Loader2, FolderOpen, AlertTriangle, CheckCircle2 } from 'lucide-react';

const CodexRunCard = ({ run, onViewManifest, onCancel }) => {
  const status = run?.status || 'running';
  const isRunning = status === 'queued' || status === 'running';
  const isFailed = status === 'failed';
  const isCompleted = status === 'completed';
  const summary = run?.summary || '';
  const stdout = run?.stdout_tail || '';
  const stderr = run?.stderr_tail || '';

  return (
    <div className="p-3 bg-brand-surface-bg rounded-lg shadow border border-gray-700">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {isRunning && <Loader2 className="w-4 h-4 animate-spin text-brand-purple" />}
          {isCompleted && <CheckCircle2 className="w-4 h-4 text-brand-success-green" />}
          {isFailed && <AlertTriangle className="w-4 h-4 text-brand-alert-red" />}
          <span className="text-sm text-brand-text-primary font-medium">Codex Workspace Run</span>
        </div>
        <div className="text-xs text-brand-text-secondary">{status}</div>
      </div>
      {summary && (
        <div className="text-sm text-brand-text-secondary mb-2">{summary}</div>
      )}
      {(stdout || stderr) && (
        <div className="grid grid-cols-2 gap-2">
          {stdout && (
            <div>
              <div className="text-xs text-brand-text-secondary mb-1">Stdout</div>
              <pre className="text-xs whitespace-pre-wrap bg-black/20 p-2 rounded border border-gray-700 text-brand-text-secondary max-h-40 overflow-auto">{stdout}</pre>
            </div>
          )}
          {stderr && (
            <div>
              <div className="text-xs text-brand-text-secondary mb-1">Stderr</div>
              <pre className="text-xs whitespace-pre-wrap bg-black/20 p-2 rounded border border-gray-700 text-brand-text-secondary max-h-40 overflow-auto">{stderr}</pre>
            </div>
          )}
        </div>
      )}
      <div className="flex items-center gap-2 mt-3">
        <button
          onClick={onViewManifest}
          className="px-3 py-1 bg-brand-purple text-white rounded-md hover:bg-brand-button-grad-to text-xs focus:outline-none focus:ring-2 focus:ring-brand-purple flex items-center gap-1"
        >
          <FolderOpen className="w-3 h-3"/> View Files
        </button>
        {isRunning && (
          <button
            onClick={onCancel}
            className="px-3 py-1 bg-gray-700 text-white rounded-md hover:bg-gray-600 text-xs focus:outline-none focus:ring-2 focus:ring-brand-purple"
          >
            Cancel
          </button>
        )}
      </div>
    </div>
  );
};

export default CodexRunCard;

