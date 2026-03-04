import React, { useState, useEffect, useRef } from 'react';
import { Trash2 } from 'lucide-react';
import {
  uploadDocument,
  ingestDocumentUrl,
  listDocuments,
  deleteDocument,
  searchDocuments,
} from '../../services/api';
import './KnowledgeStyles.css';

const FILE_TYPES = ['txt', 'md', 'docx', 'pdf'];

function getTypeBadgeClass(type) {
  if (!type) return '';
  const t = type.toLowerCase();
  if (FILE_TYPES.includes(t)) return t;
  if (t === 'url') return 'url';
  return 'txt';
}

function IndexedDot({ indexed }) {
  let cls = 'pending';
  let title = 'Indexing...';
  if (indexed === true) { cls = 'indexed'; title = 'Indexed'; }
  if (indexed === false) { cls = 'pending'; title = 'Not indexed'; }
  return <span className={`kb-indexed-dot ${cls}`} title={title} />;
}

function formatDate(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function formatChars(n) {
  if (!n) return '';
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k chars`;
  return `${n} chars`;
}

export default function KnowledgeBase({ isOpen, onClose }) {
  const [tab, setTab] = useState('documents');
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState(null); // { type: 'success'|'error', text }

  // Upload state
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef(null);

  // URL state
  const [urlInput, setUrlInput] = useState('');
  const [urlTitle, setUrlTitle] = useState('');
  const [urlLoading, setUrlLoading] = useState(false);

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  useEffect(() => {
    if (isOpen) {
      loadDocs();
      setStatusMsg(null);
    }
  }, [isOpen]);

  const loadDocs = async () => {
    setLoading(true);
    try {
      const data = await listDocuments();
      setDocs(data.documents || []);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  };

  const showStatus = (type, text) => {
    setStatusMsg({ type, text });
    setTimeout(() => setStatusMsg(null), 4000);
  };

  // --- File upload ---
  const handleFileSelect = (file) => {
    if (!file) return;
    const ext = file.name.rsplit ? file.name.rsplit('.', 1)[1] : file.name.split('.').pop().toLowerCase();
    if (!FILE_TYPES.includes(ext.toLowerCase())) {
      showStatus('error', `Unsupported file type. Please upload: ${FILE_TYPES.join(', ')}`);
      return;
    }

    const reader = new FileReader();
    reader.onload = async (e) => {
      const dataUrl = e.target.result;
      const data_b64 = dataUrl.split(',')[1];
      const title = file.name.replace(/\.[^.]+$/, '');
      try {
        await uploadDocument({ filename: file.name, data_b64, title });
        showStatus('success', `"${title}" uploaded and indexed`);
        loadDocs();
      } catch (err) {
        showStatus('error', err?.detail || err?.message || 'Upload failed');
      }
    };
    reader.readAsDataURL(file);
  };

  const handleInputChange = (e) => {
    const file = e.target.files?.[0];
    if (file) handleFileSelect(file);
    e.target.value = '';
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFileSelect(file);
  };

  // --- URL ingestion ---
  const handleAddUrl = async () => {
    if (!urlInput.trim()) return;
    const title = urlTitle.trim() || urlInput.trim();
    setUrlLoading(true);
    try {
      await ingestDocumentUrl(urlInput.trim(), title);
      showStatus('success', `"${title}" fetched and indexed`);
      setUrlInput('');
      setUrlTitle('');
      loadDocs();
    } catch (err) {
      showStatus('error', err?.detail || err?.message || 'Failed to fetch URL');
    } finally {
      setUrlLoading(false);
    }
  };

  // --- Delete ---
  const handleDelete = async (docId, title) => {
    if (!window.confirm(`Delete "${title}"? This cannot be undone.`)) return;
    try {
      await deleteDocument(docId);
      setDocs(prev => prev.filter(d => d.id !== docId));
    } catch (err) {
      showStatus('error', err?.detail || 'Delete failed');
    }
  };

  // --- Search ---
  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    setSearchResults([]);
    try {
      const data = await searchDocuments(searchQuery, 10);
      setSearchResults(data.results || []);
    } catch {
      // silent
    } finally {
      setSearching(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="kb-overlay" onClick={onClose}>
      <div className="kb-panel" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="kb-header">
          <h2>Knowledge Base</h2>
          <button className="kb-close-btn" onClick={onClose}>×</button>
        </div>

        {/* Tabs */}
        <div className="kb-tabs">
          <button
            className={`kb-tab ${tab === 'documents' ? 'active' : ''}`}
            onClick={() => setTab('documents')}
          >
            Documents {docs.length > 0 && `(${docs.length})`}
          </button>
          <button
            className={`kb-tab ${tab === 'search' ? 'active' : ''}`}
            onClick={() => setTab('search')}
          >
            Search
          </button>
        </div>

        {/* Content */}
        <div className="kb-content">
          {statusMsg && (
            <div className={`kb-status-msg ${statusMsg.type}`}>{statusMsg.text}</div>
          )}

          {tab === 'documents' && (
            <>
              {/* Drop zone */}
              <div
                className={`kb-upload-zone ${dragging ? 'dragging' : ''}`}
                onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                onDragLeave={() => setDragging(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <p>Drag & drop a file here</p>
                <p className="hint">Supported: .txt, .md, .docx, .pdf</p>
                <button className="kb-choose-btn" onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click(); }}>
                  Choose File
                </button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".txt,.md,.docx,.pdf"
                  style={{ display: 'none' }}
                  onChange={handleInputChange}
                />
              </div>

              {/* URL ingestion */}
              <div className="kb-url-row">
                <input
                  className="kb-url-input"
                  type="url"
                  placeholder="https://example.com/article"
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAddUrl()}
                />
                <input
                  className="kb-url-input"
                  style={{ maxWidth: 180 }}
                  type="text"
                  placeholder="Title (optional)"
                  value={urlTitle}
                  onChange={(e) => setUrlTitle(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAddUrl()}
                />
                <button
                  className="kb-add-url-btn"
                  onClick={handleAddUrl}
                  disabled={urlLoading || !urlInput.trim()}
                >
                  {urlLoading ? 'Fetching...' : 'Add URL'}
                </button>
              </div>

              {/* Document list */}
              {loading ? (
                <div className="kb-empty"><p>Loading...</p></div>
              ) : docs.length === 0 ? (
                <div className="kb-empty">
                  <p>No documents yet.</p>
                  <p>Upload a file or paste a URL to get started.</p>
                </div>
              ) : (
                <div className="kb-doc-list">
                  {docs.map((doc) => (
                    <div key={doc.id} className="kb-doc-card">
                      <div className="kb-doc-info">
                        <div className="kb-doc-title" title={doc.title}>{doc.title}</div>
                        <div className="kb-doc-meta">
                          <span className={`kb-type-badge ${getTypeBadgeClass(doc.file_type)}`}>
                            {doc.file_type || 'txt'}
                          </span>
                          <IndexedDot indexed={doc.indexed} />
                          <span className="kb-doc-chars">{formatChars(doc.char_count)}</span>
                          <span className="kb-doc-date">{formatDate(doc.created_at)}</span>
                        </div>
                      </div>
                      <button
                        className="kb-delete-btn"
                        onClick={() => handleDelete(doc.id, doc.title)}
                        title="Delete document"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}

          {tab === 'search' && (
            <>
              <div className="kb-search-row">
                <input
                  className="kb-search-input"
                  type="text"
                  placeholder="Search your documents..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  autoFocus
                />
                <button
                  className="kb-search-btn"
                  onClick={handleSearch}
                  disabled={searching || !searchQuery.trim()}
                >
                  {searching ? 'Searching...' : 'Search'}
                </button>
              </div>

              <div className="kb-search-results">
                {!searching && searchResults.length === 0 && (
                  <div className="kb-empty">
                    <p>{searchQuery ? 'No matching document chunks found' : 'Enter a query to search your documents'}</p>
                  </div>
                )}
                {searchResults.map((result) => (
                  <div key={result.id} className="kb-result-card">
                    <div className="kb-result-header">
                      <span className="kb-result-title">
                        {result.metadata?.title || 'Untitled'}
                      </span>
                      <span className="kb-result-score">
                        {Math.round(result.score * 100)}% match
                      </span>
                    </div>
                    <div className="kb-result-snippet">
                      {result.text?.slice(0, 200)}{result.text?.length > 200 ? '...' : ''}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
