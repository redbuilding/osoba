import React, { useEffect, useState } from 'react';
import { X, FileText } from 'lucide-react';

const FileViewerModal = ({ isOpen, onClose, workspaceId, fetchManifest, fetchFile }) => {
  const [manifest, setManifest] = useState(null);
  const [selectedPath, setSelectedPath] = useState(null);
  const [fileContent, setFileContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen && workspaceId) {
      (async () => {
        try {
          const data = await fetchManifest(workspaceId);
          setManifest(data.manifest || data);
        } catch (e) {
          setError('Failed to load manifest');
        }
      })();
    } else {
      setManifest(null);
      setSelectedPath(null);
      setFileContent('');
      setError(null);
    }
  }, [isOpen, workspaceId, fetchManifest]);

  const openFile = async (path) => {
    setSelectedPath(path);
    setLoading(true);
    setError(null);
    try {
      const data = await fetchFile(workspaceId, path);
      setFileContent(data.content || '');
    } catch (e) {
      setError('Failed to load file');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-brand-surface-bg rounded-lg shadow-xl w-full max-w-5xl mx-4 max-h-[85vh] overflow-hidden border border-gray-700">
        <div className="flex items-center justify-between p-3 border-b border-gray-700">
          <div className="text-sm font-semibold text-brand-text-primary">Workspace Files</div>
          <button onClick={onClose} className="p-1 hover:bg-gray-700 rounded focus:outline-none focus:ring-2 focus:ring-brand-purple">
            <X className="w-5 h-5 text-brand-text-secondary" />
          </button>
        </div>
        <div className="grid grid-cols-[280px_1fr] h-[75vh]">
          <div className="border-r border-gray-700 overflow-y-auto">
            {manifest?.files?.map((f) => (
              <button
                key={f.path}
                onClick={() => openFile(f.path)}
                className={`w-full text-left px-3 py-2 flex items-center gap-2 text-sm hover:bg-gray-700 ${selectedPath===f.path?'bg-gray-700':''}`}
              >
                <FileText className="w-4 h-4 text-brand-text-secondary"/> <span className="text-brand-text-primary truncate">{f.path}</span>
              </button>
            ))}
            {!manifest && (
              <div className="p-3 text-sm text-brand-text-secondary">Loading manifest…</div>
            )}
          </div>
          <div className="overflow-y-auto p-3">
            {error && <div className="text-sm text-brand-alert-red mb-2">{error}</div>}
            {loading && <div className="text-sm text-brand-text-secondary">Loading…</div>}
            {!loading && selectedPath && (
              <>
                <div className="text-sm text-brand-text-secondary mb-2">{selectedPath}</div>
                <pre className="text-xs whitespace-pre-wrap bg-black/20 p-2 rounded border border-gray-700 text-brand-text-secondary min-h-[60vh]">
                  {fileContent}
                </pre>
              </>
            )}
            {!selectedPath && !loading && (
              <div className="text-sm text-brand-text-secondary">Select a file to view.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default FileViewerModal;

