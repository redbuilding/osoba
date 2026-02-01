import React, { useEffect, useRef, useState } from 'react';

// Lightweight toast container listening for global 'oc-toast' events.
// Usage: window.dispatchEvent(new CustomEvent('oc-toast', { detail: { message, url, linkLabel } }))

const Toast = ({ id, message, url, linkLabel = 'Open', onDone, duration = 7000 }) => {
  const [visible, setVisible] = useState(false);
  const hideTimer = useRef(null);
  const removeTimer = useRef(null);

  useEffect(() => {
    // Fade in shortly after mount
    const t = setTimeout(() => setVisible(true), 10);
    // Fade out after duration, then remove after transition
    hideTimer.current = setTimeout(() => setVisible(false), duration);
    removeTimer.current = setTimeout(() => onDone(id), duration + 350);
    return () => {
      clearTimeout(t);
      if (hideTimer.current) clearTimeout(hideTimer.current);
      if (removeTimer.current) clearTimeout(removeTimer.current);
    };
  }, [id, duration, onDone]);

  return (
    <div
      className={`w-full max-w-sm pointer-events-auto mb-2 transform transition-all duration-300 ${
        visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2'
      }`}
    >
      <div className="flex items-start gap-3 p-3 rounded-lg border bg-brand-surface-bg border-gray-700 shadow-xl">
        <div className="text-sm text-brand-text-primary flex-1">{message}</div>
        {url && (
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs px-2 py-1 rounded bg-brand-purple hover:bg-brand-button-grad-to text-white"
          >
            {linkLabel || 'Open'}
          </a>
        )}
      </div>
    </div>
  );
};

const ToastContainer = () => {
  const [toasts, setToasts] = useState([]);
  const nextId = useRef(1);

  useEffect(() => {
    const handler = (e) => {
      const { message, url, linkLabel } = e.detail || {};
      const id = nextId.current++;
      setToasts((prev) => [...prev, { id, message: message || 'Saved', url: url || null, linkLabel }]);
    };
    window.addEventListener('oc-toast', handler);
    return () => window.removeEventListener('oc-toast', handler);
  }, []);

  const remove = (id) => setToasts((prev) => prev.filter((t) => t.id !== id));

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col items-end">
      {toasts.map((t) => (
        <Toast key={t.id} id={t.id} message={t.message} url={t.url} linkLabel={t.linkLabel} onDone={remove} />)
      )}
    </div>
  );
};

export default ToastContainer;

