import React, { useEffect, useMemo, useState, useCallback } from "react";
import { X, Play, Pause, Square, RefreshCcw, Loader2, ChevronDown, ChevronRight, Image as ImageIcon, Table as TableIcon, FileText, Clock, Layers } from "lucide-react";
import { createTask, listTasks, getTaskDetail, streamTask, pauseTask, resumeTask, cancelTask } from "../services/api";
import TaskTemplateSelector from "./TaskTemplateSelector";
import ScheduledTasksPanel from "./ScheduledTasksPanel";

const StatusPill = ({ status }) => {
  const color = {
    PLANNING: "bg-blue-700",
    PENDING: "bg-gray-600",
    RUNNING: "bg-green-700",
    PAUSED: "bg-yellow-600",
    FAILED: "bg-red-700",
    COMPLETED: "bg-emerald-700",
    CANCELED: "bg-gray-500",
  }[status] || "bg-gray-600";
  return <span className={`text-xs px-2 py-1 rounded ${color} text-white`}>{status}</span>;
};

const TaskRow = ({ task, onSelect }) => (
  <button onClick={() => onSelect(task._id)} className="w-full text-left p-2 rounded hover:bg-gray-700 flex items-center justify-between">
    <div>
      <div className="text-sm text-brand-text-primary truncate max-w-[220px]">{task.title || task.goal}</div>
      <div className="text-xs text-brand-text-secondary truncate max-w-[240px]">{task.goal}</div>
    </div>
    <StatusPill status={task.status} />
  </button>
);

const StepOutput = ({ output }) => {
  if (!output) return null;
  const raw = output.raw;
  const text = output.text;

  if (text && typeof text === 'string') {
    return (
      <pre className="text-xs whitespace-pre-wrap bg-black/20 p-2 rounded border border-gray-700 text-brand-text-secondary">{text}</pre>
    );
  }

  // Case: FastMCP content blocks (list of {type, ...})
  if (Array.isArray(raw)) {
    return (
      <div className="space-y-2">
        {raw.map((blk, i) => {
          if (blk.type === "image" && blk.data) {
            const mime = blk.mimeType || "image/png";
            return (
              <div key={i} className="border border-gray-700 rounded p-1 bg-black/20">
                <div className="text-xs text-brand-text-secondary mb-1 flex items-center"><ImageIcon size={14} className="mr-1"/> Image</div>
                <img alt="artifact" src={`data:${mime};base64,${blk.data}`} className="max-h-64 rounded" />
              </div>
            );
          }
          if (blk.type === "text") {
            return (
              <pre key={i} className="text-xs whitespace-pre-wrap bg-black/20 p-2 rounded border border-gray-700 text-brand-text-secondary">
                {blk.content || ""}
              </pre>
            );
          }
          return (
            <pre key={i} className="text-xs whitespace-pre-wrap bg-black/20 p-2 rounded border border-gray-700 text-brand-text-secondary">{JSON.stringify(blk)}</pre>
          );
        })}
      </div>
    );
  }

  const tryParse = (s) => {
    try { return JSON.parse(s); } catch { return null; }
  };

  const asTable = (obj) => {
    if (!obj) return null;
    const cols = obj.columns;
    const rows = obj.rows;
    if (Array.isArray(cols) && Array.isArray(rows)) return { cols, rows };
    return null;
  };

  // Case: string (maybe JSON)
  if (typeof raw === "string") {
    const parsed = tryParse(raw);
    const table = asTable(parsed);
    if (table) {
      return <DataTable columns={table.cols} rows={table.rows} />;
    }
    return (
      <pre className="text-xs whitespace-pre-wrap bg-black/20 p-2 rounded border border-gray-700 text-brand-text-secondary">
        {raw}
      </pre>
    );
  }

  // Case: object with columns/rows
  if (raw && typeof raw === "object") {
    const table = asTable(raw);
    if (table) return <DataTable columns={table.cols} rows={table.rows} />;
    return (
      <pre className="text-xs whitespace-pre-wrap bg-black/20 p-2 rounded border border-gray-700 text-brand-text-secondary">{JSON.stringify(raw, null, 2)}</pre>
    );
  }
  return null;
};

const DataTable = ({ columns, rows }) => {
  if (!Array.isArray(columns) || !Array.isArray(rows)) return null;
  const small = columns.length > 6 || rows.length > 6;
  return (
    <div className="border border-gray-700 rounded overflow-auto max-h-64">
      <table className={`min-w-full ${small ? 'text-[11px]' : 'text-xs'}`}>
        <thead className="bg-gray-800 sticky top-0">
          <tr>
            {columns.map((c, i) => (
              <th key={i} className="text-left px-2 py-1 text-brand-text-secondary whitespace-nowrap">{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, idx) => (
            <tr key={idx} className="odd:bg-black/10">
              {columns.map((c, i) => (
                <td key={i} className="px-2 py-1 text-brand-text-primary whitespace-nowrap">{String(r[c] ?? "")}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const TaskDetailInline = ({ taskId, onClose }) => {
  const [detail, setDetail] = useState(null);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let aborter;
    const load = async () => {
      try {
        const d = await getTaskDetail(taskId);
        setDetail(d);
      } finally {
        setLoading(false);
      }
      aborter = new AbortController();
      streamTask(taskId, {
        onData: (e) => setEvents((prev) => [...prev, e]),
        onError: () => {},
        onClose: () => {},
      }, aborter.signal);
    };
    load();
    return () => aborter && aborter.abort();
  }, [taskId]);

  if (loading) return <div className="p-4 text-sm text-brand-text-secondary flex items-center"><Loader2 size={16} className="animate-spin mr-2"/> Loading…</div>;
  if (!detail) return null;

  const steps = detail.plan?.steps || [];
  const [expanded, setExpanded] = useState({});
  const toggle = useCallback((i) => setExpanded((e) => ({ ...e, [i]: !e[i] })), []);

  const handlePause = async () => { await pauseTask(taskId); const d = await getTaskDetail(taskId); setDetail(d); };
  const handleResume = async () => { await resumeTask(taskId); const d = await getTaskDetail(taskId); setDetail(d); };
  const handleCancel = async () => { await cancelTask(taskId); const d = await getTaskDetail(taskId); setDetail(d); };

  return (
    <div className="p-3 border-t border-gray-700">
      <div className="flex items-center justify-between mb-2">
        <div className="text-brand-text-primary font-semibold">{detail.title}</div>
        <div className="flex items-center gap-2">
          <StatusPill status={detail.status} />
          <button onClick={handlePause} className="p-1 bg-gray-700 rounded hover:bg-gray-600" title="Pause"><Pause size={16}/></button>
          <button onClick={handleResume} className="p-1 bg-gray-700 rounded hover:bg-gray-600" title="Resume"><Play size={16}/></button>
          <button onClick={handleCancel} className="p-1 bg-gray-700 rounded hover:bg-gray-600" title="Cancel"><Square size={16}/></button>
          <button onClick={onClose} className="p-1 bg-gray-700 rounded hover:bg-gray-600" title="Close"><X size={16}/></button>
        </div>
      </div>
      <div className="text-xs text-brand-text-secondary mb-3">{detail.goal}</div>
      <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
        {steps.map((s, i) => {
          const hasTable = s.outputs && s.outputs.raw && typeof s.outputs.raw === 'string' && s.outputs.raw.includes('columns');
          const hasImage = Array.isArray(s.outputs?.raw) && s.outputs.raw.some(b => b.type === 'image');
          return (
            <div key={i} className="p-2 rounded bg-brand-surface-bg border border-gray-700">
              <div className="flex items-center justify-between">
                <button onClick={() => toggle(i)} className="flex items-center text-left">
                  {expanded[i] ? <ChevronDown size={16} className="mr-1"/> : <ChevronRight size={16} className="mr-1"/>}
                  <div className="text-sm text-brand-text-primary">{i+1}. {s.title}</div>
                </button>
                <div className="flex items-center gap-2">
                  {hasTable && <TableIcon size={14} className="text-brand-text-secondary"/>}
                  {hasImage && <ImageIcon size={14} className="text-brand-text-secondary"/>}
                  <StatusPill status={s.status || 'PENDING'} />
                </div>
              </div>
              <div className="text-xs text-brand-text-secondary mt-1">Tool: {s.tool}</div>
              {s.error && <div className="text-xs text-red-400 mt-1">{s.error}</div>}
              {expanded[i] && (
                <div className="mt-2">
                  <StepOutput output={s.outputs} />
                </div>
              )}
            </div>
          );
        })}
      </div>
      <div className="mt-3">
        <div className="text-xs text-brand-text-secondary mb-1">Events</div>
        <div className="text-xs bg-gray-800 p-2 rounded max-h-40 overflow-y-auto">
          {events.map((e, idx) => (
            <div key={idx} className="truncate">{JSON.stringify(e)}</div>
          ))}
        </div>
      </div>
    </div>
  );
};

const TasksPanel = ({ isOpen, onClose, initialGoal = "", conversationId = null }) => {
  const [goal, setGoal] = useState("");
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [showTemplates, setShowTemplates] = useState(false);
  const [showScheduled, setShowScheduled] = useState(false);

  const fetchTasks = async () => {
    setLoading(true);
    try {
      const data = await listTasks();
      setTasks(data || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (isOpen) fetchTasks(); }, [isOpen]);
  useEffect(() => {
    if (isOpen) {
      setGoal(initialGoal || "");
    }
  }, [isOpen, initialGoal]);

  const handleCreate = async () => {
    if (!goal.trim()) return;
    setSubmitting(true);
    try {
      await createTask({ goal, conversation_id: conversationId });
      setGoal("");
      await fetchTasks();
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-40" onClick={onClose}>
      <div className="absolute right-0 top-0 bottom-0 w-full sm:w-[500px] bg-brand-main-bg border-l border-gray-700 z-50" onClick={(e) => e.stopPropagation()}>
        <div className="p-3 border-b border-gray-700 flex items-center justify-between">
          <div className="font-semibold text-brand-text-primary">Tasks</div>
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-700"><X size={18}/></button>
        </div>
        <div className="p-3">
          <div className="flex items-center gap-2 mb-3">
            <input value={goal} onChange={(e) => setGoal(e.target.value)} placeholder="Describe your long-running goal..." className="flex-grow p-2 bg-brand-surface-bg rounded text-brand-text-primary placeholder-brand-text-secondary focus:outline-none"/>
            <button onClick={handleCreate} disabled={submitting || !goal.trim()} className="p-2 rounded bg-brand-purple text-white hover:bg-brand-button-grad-to disabled:opacity-50">
              {submitting ? <Loader2 size={18} className="animate-spin"/> : <Play size={18}/>} 
            </button>
            <button onClick={fetchTasks} className="p-2 rounded bg-gray-700 text-white hover:bg-gray-600" title="Refresh"><RefreshCcw size={18}/></button>
          </div>
          
          <div className="flex gap-2">
            <button 
              onClick={() => setShowTemplates(true)}
              className="flex items-center gap-1 px-3 py-1 text-xs rounded bg-blue-600 hover:bg-blue-700 text-white"
            >
              <Layers className="w-3 h-3" />
              Templates
            </button>
            <button 
              onClick={() => setShowScheduled(true)}
              className="flex items-center gap-1 px-3 py-1 text-xs rounded bg-green-600 hover:bg-green-700 text-white"
            >
              <Clock className="w-3 h-3" />
              Scheduled
            </button>
          </div>
        </div>
        <div className="p-3 border-t border-gray-700">
          {loading ? (
            <div className="text-sm text-brand-text-secondary flex items-center"><Loader2 size={16} className="animate-spin mr-2"/> Loading…</div>
          ) : (
            <div className="space-y-1 max-h-60 overflow-y-auto">
              {tasks.length === 0 && <div className="text-sm text-brand-text-secondary">No tasks yet.</div>}
              {tasks.map((t) => (
                <TaskRow key={t._id} task={t} onSelect={setSelectedId} />
              ))}
            </div>
          )}
        </div>
        {selectedId && <TaskDetailInline taskId={selectedId} onClose={() => setSelectedId(null)} />}
        
        {/* Template Selector Modal */}
        <TaskTemplateSelector
          isOpen={showTemplates}
          onClose={() => setShowTemplates(false)}
          onTaskCreated={(taskId, renderedGoal) => {
            setShowTemplates(false);
            fetchTasks();
            setSelectedId(taskId);
          }}
        />
        
        {/* Scheduled Tasks Modal */}
        <ScheduledTasksPanel
          isOpen={showScheduled}
          onClose={() => setShowScheduled(false)}
        />
      </div>
    </div>
  );
};

export default TasksPanel;
