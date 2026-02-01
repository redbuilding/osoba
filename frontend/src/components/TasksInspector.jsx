import React, { useEffect, useMemo, useState, useCallback } from "react";
import { X, Play, Pause, Square, RefreshCcw, Loader2, ChevronDown, ChevronRight, Image as ImageIcon, Table as TableIcon, FileText, Clock, Layers, Copy, Trash2 } from "lucide-react";
import { createTask, listTasks, getTaskDetail, streamTask, pauseTask, resumeTask, cancelTask, deleteTask } from "../services/api";
import TaskTemplateSelector from "./TaskTemplateSelector";
import ScheduledTasksPanel from "./ScheduledTasksPanel";
import RightPanel from "./RightPanel";
import ModelPickerModal from "./ModelPickerModal";

const StatusPill = ({ status }) => {
  const color = {
    PLANNING: "bg-brand-stat-blue",
    PENDING: "bg-gray-600",
    RUNNING: "bg-brand-success-green",
    PAUSED: "bg-yellow-600",
    FAILED: "bg-brand-alert-red",
    COMPLETED: "bg-brand-success-green",
    CANCELED: "bg-gray-500",
  }[status] || "bg-gray-600";
  return <span className={`text-xs px-2 py-1 rounded ${color} text-white`}>{status}</span>;
};

const TaskRow = ({ task, onSelect }) => (
  <button onClick={() => onSelect(task.id)} className="w-full text-left p-2 rounded hover:bg-gray-700 flex items-center justify-between">
    <div className="min-w-0 flex-1">
      <div className="text-sm text-brand-text-primary truncate">{task.title || task.goal}</div>
      <div className="text-xs text-brand-text-secondary truncate">{task.goal}</div>
      {task.model_name && (
        <div className="text-[11px] text-brand-text-secondary truncate">Model: {task.model_name}</div>
      )}
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
                {blk.content || blk.text || ""}
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

const TaskDetailInline = ({ taskId, onClose, onTaskDeleted }) => {
  const [detail, setDetail] = useState(null);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState({});
  
  const toggle = useCallback((i) => setExpanded((e) => ({ ...e, [i]: !e[i] })), []);

  useEffect(() => {
    let aborter;
    let poller;
    const load = async () => {
      try {
        const d = await getTaskDetail(taskId);
        setDetail(d);
      } finally {
        setLoading(false);
      }
      aborter = new AbortController();
      streamTask(taskId, {
        onData: async (e) => {
          setEvents((prev) => [...prev, e]);
          // Optimistically merge step status for snappier UI
          if (e && e.type === 'STEP_STATUS' && typeof e.index === 'number') {
            setDetail((prev) => {
              if (!prev || !prev.plan || !Array.isArray(prev.plan.steps)) return prev;
              const steps = [...prev.plan.steps];
              if (steps[e.index]) {
                const next = { ...steps[e.index], status: e.status };
                // Clear transient errors when step restarts or completes
                if (e.status === 'RUNNING' || e.status === 'COMPLETED') {
                  next.error = undefined;
                } else if (typeof e.error !== 'undefined') {
                  next.error = e.error;
                }
                steps[e.index] = next;
              }
              return { ...prev, plan: { ...prev.plan, steps } };
            });
          }
          if (e && e.type === 'TASK_STATUS' && e.status) {
            setDetail((prev) => prev ? { ...prev, status: e.status } : prev);
          }
          // Always fetch fresh state to sync outputs and counters
          if (e && (e.type === 'STEP_STATUS' || e.type === 'TASK_STATUS')) {
            try {
              const fresh = await getTaskDetail(taskId);
              setDetail(fresh);
            } catch {}
          }
          // On terminal status, do a delayed fetch in case of write/read race
          if (e && e.type === 'TASK_STATUS' && ['COMPLETED','FAILED','CANCELED'].includes(e.status)) {
            setTimeout(async () => {
              try { const finalFresh = await getTaskDetail(taskId); setDetail(finalFresh); } catch {}
            }, 300);
          }
        },
        onError: () => {},
        onClose: () => {},
      }, aborter.signal);
    };
    load();
    return () => {
      aborter && aborter.abort();
    };
  }, [taskId]);

  const handlePause = async () => { await pauseTask(taskId); const d = await getTaskDetail(taskId); setDetail(d); };
  const handleResume = async () => { await resumeTask(taskId); const d = await getTaskDetail(taskId); setDetail(d); };
  const handleCancel = async () => { await cancelTask(taskId); const d = await getTaskDetail(taskId); setDetail(d); };
  const handleDelete = async () => {
    if (!confirm('Delete this task? This action cannot be undone.')) return;
    try {
      await deleteTask(taskId);
    } catch (e) {
      console.warn('Delete task failed or task not found:', e);
    } finally {
      onTaskDeleted();
    }
  };

  const handleCopyTask = () => {
    if (!detail) return;
    
    let content = `Task: ${detail.title}\nGoal: ${detail.goal}\nStatus: ${detail.status}\n\n`;
    
    steps.forEach((step, i) => {
      content += `${i + 1}. ${step.title}\n`;
      content += `   Status: ${step.status || 'PENDING'}\n`;
      content += `   Tool: ${step.tool}\n`;
      
      if (step.outputs) {
        if (step.outputs.text) {
          content += `   Output: ${step.outputs.text}\n`;
        } else if (step.outputs.raw) {
          const rawStr = typeof step.outputs.raw === 'string' ? step.outputs.raw : JSON.stringify(step.outputs.raw, null, 2);
          content += `   Output: ${rawStr.substring(0, 500)}${rawStr.length > 500 ? '...' : ''}\n`;
        }
      }
      
      if (step.error) {
        content += `   Error: ${step.error}\n`;
      }
      content += '\n';
    });
    
    navigator.clipboard.writeText(content);
  };

  const handleCopyStep = (step) => {
    if (!step.outputs) return;
    
    let content = '';
    if (step.outputs.text) {
      content = step.outputs.text;
    } else if (step.outputs.raw) {
      content = typeof step.outputs.raw === 'string' ? step.outputs.raw : JSON.stringify(step.outputs.raw, null, 2);
    }
    
    if (content) {
      navigator.clipboard.writeText(content);
    }
  };

  if (loading) return <div className="p-4 text-sm text-brand-text-secondary flex items-center"><Loader2 size={16} className="animate-spin mr-2"/> Loading…</div>;
  if (!detail) return null;

  const isCompleted = detail.status === 'COMPLETED';
  const isFailed = detail.status === 'FAILED';
  const isCanceled = detail.status === 'CANCELED';

  const steps = detail.plan?.steps || [];

  return (
    <div className="p-3 border-t border-gray-700">
      <div className="flex items-center justify-between mb-2">
        <div className="text-brand-text-primary font-semibold truncate flex-1">{detail.title}</div>
        <div className="flex items-center gap-1 ml-2">
          <StatusPill status={detail.status} />
          <button onClick={handleCopyTask} className="p-1 bg-gray-700 rounded hover:bg-gray-600" title="Copy Task Results"><Copy size={14}/></button>
          {!isCompleted && !isFailed && !isCanceled && (
            <>
              <button onClick={handlePause} className="p-1 bg-gray-700 rounded hover:bg-gray-600" title="Pause"><Pause size={14}/></button>
              <button onClick={handleResume} className="p-1 bg-gray-700 rounded hover:bg-gray-600" title="Resume"><Play size={14}/></button>
              <button onClick={handleCancel} className="p-1 bg-gray-700 rounded hover:bg-gray-600" title="Cancel"><Square size={14}/></button>
            </>
          )}
          {(isCompleted || isFailed || isCanceled) && (
            <button onClick={handleDelete} className="p-1 bg-red-700 rounded hover:bg-red-600" title="Delete Task"><Trash2 size={14}/></button>
          )}
          <button onClick={onClose} className="p-1 bg-gray-700 rounded hover:bg-gray-600" title="Close"><X size={14}/></button>
        </div>
      </div>
      {detail.model_name && (
        <div className="text-[11px] text-brand-text-secondary mb-2">Model: {detail.model_name}</div>
      )}
      <div className="text-xs text-brand-text-secondary mb-3">{detail.goal}</div>
      <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
        {steps.map((s, i) => {
          // Derive a stable status when step.status is temporarily missing
          const deriveStatus = () => {
            const csi = typeof detail.current_step_index === 'number' ? detail.current_step_index : -1;
            const isTerminal = ['COMPLETED','FAILED','CANCELED'].includes(detail.status);
            if (isTerminal) {
              if (i < csi) return 'COMPLETED';
              if (i === csi) return detail.status === 'COMPLETED' ? 'COMPLETED' : 'FAILED';
              return 'PENDING';
            }
            if (s.status) return s.status;
            if (csi < 0) return 'PENDING';
            if (i < csi) return 'COMPLETED';
            if (i === csi) return 'RUNNING';
            return 'PENDING';
          };
          const effectiveStatus = deriveStatus();
          const hasTable = s.outputs && s.outputs.raw && typeof s.outputs.raw === 'string' && s.outputs.raw.includes('columns');
          const hasImage = Array.isArray(s.outputs?.raw) && s.outputs.raw.some(b => b.type === 'image');
          return (
            <div key={i} className="p-2 rounded bg-brand-surface-bg border border-gray-700">
              <div className="flex items-center justify-between">
                <button onClick={() => toggle(i)} className="flex items-center text-left min-w-0 flex-1">
                  {expanded[i] ? <ChevronDown size={14} className="mr-1 flex-shrink-0"/> : <ChevronRight size={14} className="mr-1 flex-shrink-0"/>}
                  <div className="text-sm text-brand-text-primary truncate">{i+1}. {s.title}</div>
                </button>
                <div className="flex items-center gap-1 ml-2">
                  {hasTable && <TableIcon size={12} className="text-brand-text-secondary"/>}
                  {hasImage && <ImageIcon size={12} className="text-brand-text-secondary"/>}
                  <StatusPill status={effectiveStatus} />
                </div>
              </div>
              <div className="text-xs text-brand-text-secondary mt-1">Tool: {s.tool}</div>
              {s.error && <div className="text-xs text-red-400 mt-1">{s.error}</div>}
              {expanded[i] && s.outputs && (
                <div className="mt-2">
                  {(s.outputs.text || s.outputs.raw) && (
                    <div className="flex items-center justify-between mb-1">
                      <div className="text-xs text-brand-text-secondary">Output:</div>
                      <button 
                        onClick={() => handleCopyStep(s)} 
                        className="p-1 bg-gray-600 rounded hover:bg-gray-500 text-xs" 
                        title="Copy Step Output"
                      >
                        <Copy size={10}/>
                      </button>
                    </div>
                  )}
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

const TasksInspector = ({ isOpen, onClose, initialGoal = "", conversationId = null, defaultConversationModel = null }) => {
  const [goal, setGoal] = useState("");
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState("");
  const [selectedId, setSelectedId] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [showTemplates, setShowTemplates] = useState(false);
  const [showScheduled, setShowScheduled] = useState(false);
  const [taskModel, setTaskModel] = useState(null);
  const [isModelModalOpen, setIsModelModalOpen] = useState(false);

  const fetchTasks = async () => {
    setLoading(true);
    setListError("");
    try {
      const data = await listTasks();
      setTasks(data || []);
    } catch (e) {
      setTasks([]);
      setListError("Failed to load tasks. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (isOpen) fetchTasks(); }, [isOpen]);
  useEffect(() => {
    if (isOpen) {
      setGoal(initialGoal || "");
      // Initialize task model from conversation if available
      setTaskModel(defaultConversationModel || null);
    }
  }, [isOpen, initialGoal, defaultConversationModel]);

  const handleCreate = async () => {
    if (!goal.trim()) return;
    setSubmitting(true);
    try {
      const payload = { goal, conversation_id: conversationId };
      if (taskModel) payload.model_name = taskModel;
      await createTask(payload);
      setGoal("");
      // keep selected task model for next time
      await fetchTasks();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <RightPanel isOpen={isOpen} onClose={onClose} title="Tasks" width="w-[480px]">
      <div className="flex flex-col h-full">
        {/* Task Creation */}
        <div className="p-3 border-b border-gray-700">
          <div className="flex items-center gap-2 mb-3">
            <input 
              value={goal} 
              onChange={(e) => setGoal(e.target.value)} 
              placeholder="Describe your long-running goal..." 
              className="flex-1 p-2 bg-brand-surface-bg border border-gray-700 rounded text-brand-text-primary placeholder-brand-text-secondary focus:outline-none focus:ring-2 focus:ring-brand-purple text-sm"
            />
            <button
              onClick={() => setIsModelModalOpen(true)}
              className="px-2 py-2 rounded bg-gray-700 hover:bg-gray-600 text-white text-xs"
              title="Select model for this task"
            >
              {taskModel ? `Model: ${taskModel}` : 'Select Model'}
            </button>
            <button 
              onClick={handleCreate} 
              disabled={submitting || !goal.trim()} 
              className="p-2 rounded bg-brand-purple text-white hover:bg-brand-button-grad-to disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-brand-purple"
              title="Create task"
            >
              {submitting ? <Loader2 size={16} className="animate-spin"/> : <Play size={16}/>} 
            </button>
            <button 
              onClick={fetchTasks} 
              className="p-2 rounded bg-gray-700 text-white hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-brand-purple" 
              title="Refresh"
            >
              <RefreshCcw size={16}/>
            </button>
          </div>
          
          <div className="flex gap-2">
            <button 
              onClick={() => setShowTemplates(true)}
              className="flex items-center gap-1 px-3 py-1 text-xs rounded bg-gray-700 hover:bg-gray-600 text-white focus:outline-none focus:ring-2 focus:ring-brand-purple"
            >
              <Layers className="w-3 h-3" />
              Templates
            </button>
            <button 
              onClick={() => setShowScheduled(true)}
              className="flex items-center gap-1 px-3 py-1 text-xs rounded bg-gray-700 hover:bg-gray-600 text-white focus:outline-none focus:ring-2 focus:ring-brand-purple"
            >
              <Clock className="w-3 h-3" />
              Scheduled
            </button>
          </div>
        </div>

        {/* Task List */}
        <div className="flex-1 p-3 overflow-hidden">
          {loading ? (
            <div className="text-sm text-brand-text-secondary flex items-center">
              <Loader2 size={16} className="animate-spin mr-2"/> Loading…
            </div>
          ) : (
            <div className="space-y-1 h-full overflow-y-auto">
              {listError && (
                <div className="text-sm text-brand-alert-red">{listError}</div>
              )}
              {tasks.length === 0 && !listError && (
                <div className="text-sm text-brand-text-secondary">No tasks yet.</div>
              )}
              {tasks.map((t) => (
                <TaskRow key={t.id} task={t} onSelect={setSelectedId} />
              ))}
            </div>
          )}
        </div>

        {/* Task Detail */}
        {selectedId && <TaskDetailInline taskId={selectedId} onClose={() => setSelectedId(null)} onTaskDeleted={() => { fetchTasks(); setSelectedId(null); }} />}
      </div>
      
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

      {/* Model Picker for direct task */}
      <ModelPickerModal
        isOpen={isModelModalOpen}
        onClose={() => setIsModelModalOpen(false)}
        onSelectModel={(fullName) => { setTaskModel(fullName); setIsModelModalOpen(false); }}
        currentModel={taskModel}
        onOpenSettings={() => { /* Settings modal owned by App; skip here */ }}
      />
    </RightPanel>
  );
};

export default TasksInspector;
