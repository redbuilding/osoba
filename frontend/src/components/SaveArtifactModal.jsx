import React, { useEffect, useMemo, useState } from 'react';
import { X, FileText, FileCode, File, AlertTriangle } from 'lucide-react';
import { saveArtifact, getArtifactCapabilities } from '../services/api';

const baseFormats = [
  { id: 'md', label: 'Markdown (.md)' },
  { id: 'html', label: 'HTML (templated)' },
  { id: 'docx', label: 'DOCX (generated)' },
  { id: 'pdf', label: 'PDF (from HTML)' },
];

const SaveArtifactModal = ({
  isOpen,
  onClose,
  sourceType, // 'message' | 'task_run'
  content,    // string if message
  taskId,     // string if task_run
  defaultTitle,
  profileName,
  onSaved,
}) => {
  const [format, setFormat] = useState('md');
  const [pathTemplate, setPathTemplate] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [caps, setCaps] = useState({ html: false, docx: false, pdf: false });
  const [templateId, setTemplateId] = useState('branded_report');

  useEffect(() => {
    if (!isOpen) return;
    setError('');
    setSaving(false);
    setFormat('md');
    setTemplateId('branded_report');
    (async () => {
      try {
        const c = await getArtifactCapabilities();
        setCaps({ html: !!c.html, docx: !!c.docx, pdf: !!c.pdf });
      } catch {}
    })();
    if (sourceType === 'task_run') {
      setPathTemplate('artifacts/{date}/tasks/{task_slug}/{run_id}-{title}.md');
    } else {
      setPathTemplate('artifacts/{date}/messages/{title}.md');
    }
  }, [isOpen, sourceType]);

  const disabled = useMemo(() => saving, [saving]);

  if (!isOpen) return null;

  const handleSave = async () => {
    setSaving(true);
    setError('');
    try {
      const payload = {
        source_type: sourceType,
        format,
        path_template: pathTemplate,
        title: defaultTitle || (sourceType === 'task_run' ? 'Task' : 'Message'),
        profile: profileName || '',
      };
      if (sourceType === 'message') payload.content = content || '';
      if (sourceType === 'task_run') payload.task_id = taskId;
      if (format === 'html' || format === 'pdf') payload.template_id = templateId;
      const res = await saveArtifact(payload);
      onSaved && onSaved(res);
      onClose();
    } catch (e) {
      setError(e?.detail || e?.message || 'Failed to save file');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black bg-opacity-70" onClick={onClose} />
      <div className="absolute inset-0 flex items-center justify-center p-4">
        <div className="w-full max-w-2xl bg-brand-surface-bg border border-gray-700 rounded-xl shadow-2xl overflow-hidden">
          <div className="flex items-center justify-between p-4 border-b border-gray-700 bg-black/20">
            <h2 className="text-lg font-semibold text-brand-text-primary">Save to File</h2>
            <button onClick={onClose} className="p-1 rounded hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-brand-purple" aria-label="Close save dialog">
              <X className="w-5 h-5 text-brand-text-secondary" />
            </button>
          </div>
          <div className="p-4 space-y-4">
            {/* Format */}
            <div>
              <label className="block text-xs text-brand-text-secondary mb-1">Format</label>
              <div className="grid grid-cols-2 gap-2">
                {baseFormats.map(f => {
                  const enabled = (f.id === 'md') || (f.id === 'html' && caps.html) || (f.id === 'pdf' && caps.pdf) || (f.id === 'docx' && caps.docx);
                  return (
                  <button
                    key={f.id}
                    disabled={!enabled}
                    onClick={() => enabled && setFormat(f.id)}
                    className={`flex items-center gap-2 px-3 py-2 rounded border ${
                      format === f.id ? 'bg-black/30 border-gray-700 text-brand-text-primary' : 'bg-brand-main-bg border-gray-800 text-brand-text-secondary hover:bg-gray-800'
                    } ${!enabled ? 'opacity-50 cursor-not-allowed' : ''}`}
                    title={!enabled ? 'Unavailable (missing dependencies)' : f.label}
                  >
                    {f.id === 'md' ? <FileText className="w-4 h-4"/> : <File className="w-4 h-4"/>}
                    <span className="text-sm">{f.label}</span>
                  </button>
                  );
                })}
              </div>
            </div>

            {(format === 'html' || format === 'pdf') && (
              <div>
                <label className="block text-xs text-brand-text-secondary mb-1">Template</label>
                <select
                  value={templateId}
                  onChange={(e) => setTemplateId(e.target.value)}
                  className="w-full px-3 py-2 bg-brand-main-bg border border-gray-700 rounded text-brand-text-primary focus:outline-none focus:ring-2 focus:ring-brand-purple text-sm"
                >
                  <option value="branded_report">Branded Report</option>
                </select>
              </div>
            )}

            {/* Path template */}
            <div>
              <label className="block text-xs text-brand-text-secondary mb-1">Path template</label>
              <input
                type="text"
                value={pathTemplate}
                onChange={(e) => setPathTemplate(e.target.value)}
                className="w-full px-3 py-2 bg-brand-main-bg border border-gray-700 rounded text-brand-text-primary placeholder-brand-text-secondary focus:outline-none focus:ring-2 focus:ring-brand-purple"
                placeholder={sourceType === 'task_run' ? 'artifacts/{date}/tasks/{task_slug}/{run_id}-{title}.md' : 'artifacts/{date}/messages/{title}.md'}
              />
              <div className="text-[11px] text-brand-text-secondary mt-1">Tokens: {'{date} {timestamp} {task_slug} {run_id} {title} {profile}'}</div>
            </div>

            {error && (
              <div className="flex items-center text-sm text-brand-alert-red">
                <AlertTriangle className="w-4 h-4 mr-2" /> {error}
              </div>
            )}

            <div className="flex items-center justify-end gap-2">
              <button onClick={onClose} className="px-3 py-2 text-sm bg-gray-700 hover:bg-gray-600 text-white rounded">Cancel</button>
              <button onClick={handleSave} disabled={disabled} className="px-3 py-2 text-sm bg-brand-purple hover:bg-brand-button-grad-to text-white rounded focus:outline-none focus:ring-2 focus:ring-brand-purple">
                {saving ? 'Saving…' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SaveArtifactModal;
