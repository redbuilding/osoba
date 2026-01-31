import React, { useState, useEffect } from 'react';
import { X, Clock, Plus, Trash2, Calendar } from 'lucide-react';
import { 
  listScheduledTasks, 
  createScheduledTask, 
  deleteScheduledTask,
  runScheduledTaskNow
} from '../services/api';
import ModelPickerModal from './ModelPickerModal';

const ScheduledTasksPanel = ({ isOpen, onClose }) => {
  const [scheduledTasks, setScheduledTasks] = useState([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isModelModalOpen, setIsModelModalOpen] = useState(false);
  const [formModel, setFormModel] = useState(null);
  const [runOverrideForId, setRunOverrideForId] = useState(null);

  const [formData, setFormData] = useState({
    name: '',
    goal: '',
    cron_expression: '0 9 * * 1', // Default: Every Monday at 9 AM
    timezone: 'UTC',
    enabled: true,
    // New fields for user-friendly scheduling
    scheduleType: 'simple', // 'simple' or 'advanced'
    simpleSchedule: {
      type: 'weekly', // 'once', 'daily', 'weekly', 'monthly'
      date: '', // For 'once' type
      time: '09:00',
      weekday: '1', // Monday
      monthDay: '1' // 1st of month
    }
  });

  useEffect(() => {
    if (isOpen) {
      fetchScheduledTasks();
    }
  }, [isOpen]);

  const fetchScheduledTasks = async () => {
    try {
      const tasks = await listScheduledTasks();
      setScheduledTasks(tasks);
    } catch (error) {
      setError('Failed to load scheduled tasks');
    }
  };

  // Convert 24h time to 12h format for display
  const formatTime12h = (time24) => {
    const [hours, minutes] = time24.split(':');
    const hour12 = hours % 12 || 12;
    const ampm = hours >= 12 ? 'PM' : 'AM';
    return `${hour12}:${minutes} ${ampm}`;
  };

  // Convert 12h time to 24h format for storage
  const formatTime24h = (hour12, minute, ampm) => {
    let hour24 = parseInt(hour12);
    if (ampm === 'PM' && hour24 !== 12) hour24 += 12;
    if (ampm === 'AM' && hour24 === 12) hour24 = 0;
    return `${hour24.toString().padStart(2, '0')}:${minute}`;
  };

  // Parse current time for 12h display
  const parseTime12h = (time24) => {
    const [hours, minutes] = time24.split(':');
    const hour12 = (hours % 12 || 12).toString();
    const ampm = hours >= 12 ? 'PM' : 'AM';
    return { hour: hour12, minute: minutes, ampm };
  };

  // Convert simple schedule to cron expression
  const generateCronFromSimple = (simple) => {
    const [hour, minute] = simple.time.split(':');
    
    switch (simple.type) {
      case 'once':
        // For one-time tasks, we'll use the current cron but this should be handled differently in backend
        return `${parseInt(minute)} ${parseInt(hour)} * * *`; // Daily for now, backend should handle one-time
      case 'daily':
        return `${parseInt(minute)} ${parseInt(hour)} * * *`;
      case 'weekly':
        return `${parseInt(minute)} ${parseInt(hour)} * * ${simple.weekday}`;
      case 'monthly':
        return `${parseInt(minute)} ${parseInt(hour)} ${simple.monthDay} * *`;
      default:
        return `${parseInt(minute)} ${parseInt(hour)} * * *`;
    }
  };

  const handleCreateTask = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const cronExpression = formData.scheduleType === 'simple' 
        ? generateCronFromSimple(formData.simpleSchedule)
        : formData.cron_expression;

      await createScheduledTask({
        name: formData.name,
        goal: formData.goal,
        model_name: formModel || null,
        schedule: {
          cron_expression: cronExpression,
          timezone: formData.timezone,
          enabled: formData.enabled
        }
      });

      setFormData({
        name: '',
        goal: '',
        cron_expression: '0 9 * * 1',
        timezone: 'UTC',
        enabled: true,
        scheduleType: 'simple',
        simpleSchedule: {
          type: 'weekly',
          date: '',
          time: '09:00',
          weekday: '1',
          monthDay: '1'
        }
      });
      setShowCreateForm(false);
      setFormModel(null);
      fetchScheduledTasks();
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to create scheduled task');
    } finally {
      setLoading(false);
    }
  };

  const handleRunNow = async (taskId) => {
    try {
      await runScheduledTaskNow(taskId);
      // maybe show a toast in future
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to run task');
    }
  };

  const handleRunWithModel = (taskId) => {
    setRunOverrideForId(taskId);
    setIsModelModalOpen(true);
  };

  const handleDeleteTask = async (taskId) => {
    if (!confirm('Are you sure you want to delete this scheduled task?')) return;

    try {
      await deleteScheduledTask(taskId);
      fetchScheduledTasks();
    } catch (error) {
      setError('Failed to delete scheduled task');
    }
  };

  const formatCronExpression = (cron) => {
    // Simple cron expression formatter
    const parts = cron.split(' ');
    if (parts.length !== 5) return cron;

    const [minute, hour, day, month, weekday] = parts;
    
    if (weekday !== '*') {
      const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
      return `${days[parseInt(weekday)]} at ${hour}:${minute.padStart(2, '0')}`;
    }
    
    if (day !== '*') {
      return `Day ${day} at ${hour}:${minute.padStart(2, '0')}`;
    }
    
    return `Daily at ${hour}:${minute.padStart(2, '0')}`;
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-brand-surface-bg rounded-lg shadow-xl w-full max-w-4xl mx-4 max-h-[90vh] overflow-hidden border border-gray-700">
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h2 className="text-xl font-semibold flex items-center text-brand-text-primary">
            <Clock className="w-5 h-5 mr-2" />
            Scheduled Tasks
          </h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-700 rounded focus:outline-none focus:ring-2 focus:ring-brand-purple"
          >
            <X className="w-5 h-5 text-brand-text-secondary" />
          </button>
        </div>

        <div className="p-4 max-h-[70vh] overflow-y-auto bg-brand-main-bg">
          {error && (
            <div className="mb-4 p-3 bg-red-900/30 border border-red-700 rounded text-sm text-red-400">
              {error}
            </div>
          )}

          <div className="flex justify-between items-center mb-4">
            <h3 className="font-medium">Scheduled Tasks ({scheduledTasks.length})</h3>
            <button
              onClick={() => setShowCreateForm(true)}
              className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              <Plus className="w-4 h-4" />
              New Schedule
            </button>
          </div>

          {showCreateForm && (
            <div className="mb-6 p-4 border border-gray-700 rounded-lg bg-brand-surface-bg">
              <h4 className="font-medium mb-3 text-brand-text-primary">Create Scheduled Task</h4>
              <form onSubmit={handleCreateTask}>
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <label className="block text-sm font-medium mb-1 text-brand-text-primary">Task Name</label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-700 rounded-md text-sm bg-brand-surface-bg text-brand-text-primary placeholder-brand-text-secondary focus:outline-none focus:ring-2 focus:ring-brand-purple"
                      required
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium mb-1 text-brand-text-primary">Timezone</label>
                    <select
                      value={formData.timezone}
                      onChange={(e) => setFormData(prev => ({ ...prev, timezone: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-700 rounded-md text-sm bg-brand-surface-bg text-brand-text-primary focus:outline-none focus:ring-2 focus:ring-brand-purple"
                    >
                      <option value="UTC">UTC</option>
                      <option value="America/New_York">Eastern Time</option>
                      <option value="America/Chicago">Central Time</option>
                      <option value="America/Denver">Mountain Time</option>
                      <option value="America/Los_Angeles">Pacific Time</option>
                    </select>
                  </div>
                </div>

                {/* Schedule Type Toggle */}
                <div className="mb-4">
                  <label className="block text-sm font-medium mb-2 text-brand-text-primary">Schedule</label>
                  <div className="flex gap-2 mb-3">
                    <button
                      type="button"
                      onClick={() => setFormData(prev => ({ ...prev, scheduleType: 'simple' }))}
                      className={`px-3 py-1 text-sm rounded ${
                        formData.scheduleType === 'simple'
                          ? 'bg-brand-purple text-white'
                          : 'bg-gray-700 text-brand-text-secondary hover:bg-gray-600'
                      }`}
                    >
                      Simple
                    </button>
                    <button
                      type="button"
                      onClick={() => setFormData(prev => ({ ...prev, scheduleType: 'advanced' }))}
                      className={`px-3 py-1 text-sm rounded ${
                        formData.scheduleType === 'advanced'
                          ? 'bg-brand-purple text-white'
                          : 'bg-gray-700 text-brand-text-secondary hover:bg-gray-600'
                      }`}
                    >
                      Advanced (Cron)
                    </button>
                  </div>

                  {formData.scheduleType === 'simple' ? (
                    <div className="space-y-3">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-xs font-medium mb-1 text-brand-text-secondary">Frequency</label>
                          <select
                            value={formData.simpleSchedule.type}
                            onChange={(e) => setFormData(prev => ({
                              ...prev,
                              simpleSchedule: { ...prev.simpleSchedule, type: e.target.value }
                            }))}
                            className="w-full px-3 py-2 border border-gray-700 rounded-md text-sm bg-brand-surface-bg text-brand-text-primary focus:outline-none focus:ring-2 focus:ring-brand-purple"
                          >
                            <option value="once">Once</option>
                            <option value="daily">Daily</option>
                            <option value="weekly">Weekly</option>
                            <option value="monthly">Monthly</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-xs font-medium mb-1 text-brand-text-secondary">Time</label>
                          <div className="flex gap-1">
                            <select
                              value={parseTime12h(formData.simpleSchedule.time).hour}
                              onChange={(e) => {
                                const { minute, ampm } = parseTime12h(formData.simpleSchedule.time);
                                const newTime = formatTime24h(e.target.value, minute, ampm);
                                setFormData(prev => ({
                                  ...prev,
                                  simpleSchedule: { ...prev.simpleSchedule, time: newTime }
                                }));
                              }}
                              className="flex-1 px-2 py-2 border border-gray-700 rounded-md text-sm bg-brand-surface-bg text-brand-text-primary focus:outline-none focus:ring-2 focus:ring-brand-purple"
                            >
                              {Array.from({ length: 12 }, (_, i) => i + 1).map(hour => (
                                <option key={hour} value={hour}>{hour}</option>
                              ))}
                            </select>
                            <span className="flex items-center px-1 text-brand-text-secondary">:</span>
                            <select
                              value={parseTime12h(formData.simpleSchedule.time).minute}
                              onChange={(e) => {
                                const { hour, ampm } = parseTime12h(formData.simpleSchedule.time);
                                const newTime = formatTime24h(hour, e.target.value, ampm);
                                setFormData(prev => ({
                                  ...prev,
                                  simpleSchedule: { ...prev.simpleSchedule, time: newTime }
                                }));
                              }}
                              className="flex-1 px-2 py-2 border border-gray-700 rounded-md text-sm bg-brand-surface-bg text-brand-text-primary focus:outline-none focus:ring-2 focus:ring-brand-purple"
                            >
                              {['00', '15', '30', '45'].map(minute => (
                                <option key={minute} value={minute}>{minute}</option>
                              ))}
                            </select>
                            <select
                              value={parseTime12h(formData.simpleSchedule.time).ampm}
                              onChange={(e) => {
                                const { hour, minute } = parseTime12h(formData.simpleSchedule.time);
                                const newTime = formatTime24h(hour, minute, e.target.value);
                                setFormData(prev => ({
                                  ...prev,
                                  simpleSchedule: { ...prev.simpleSchedule, time: newTime }
                                }));
                              }}
                              className="px-2 py-2 border border-gray-700 rounded-md text-sm bg-brand-surface-bg text-brand-text-primary focus:outline-none focus:ring-2 focus:ring-brand-purple"
                            >
                              <option value="AM">AM</option>
                              <option value="PM">PM</option>
                            </select>
                          </div>
                        </div>
                      </div>

                      {formData.simpleSchedule.type === 'once' && (
                        <div>
                          <label className="block text-xs font-medium mb-1 text-brand-text-secondary">Date</label>
                          <input
                            type="date"
                            value={formData.simpleSchedule.date}
                            onChange={(e) => setFormData(prev => ({
                              ...prev,
                              simpleSchedule: { ...prev.simpleSchedule, date: e.target.value }
                            }))}
                            className="w-full px-3 py-2 border border-gray-700 rounded-md text-sm bg-brand-surface-bg text-brand-text-primary focus:outline-none focus:ring-2 focus:ring-brand-purple [&::-webkit-calendar-picker-indicator]:filter [&::-webkit-calendar-picker-indicator]:invert [&::-webkit-calendar-picker-indicator]:opacity-70"
                            min={new Date(new Date().getTime() - new Date().getTimezoneOffset() * 60000).toISOString().split('T')[0]}
                          />
                        </div>
                      )}

                      {formData.simpleSchedule.type === 'weekly' && (
                        <div>
                          <label className="block text-xs font-medium mb-1 text-brand-text-secondary">Day of Week</label>
                          <select
                            value={formData.simpleSchedule.weekday}
                            onChange={(e) => setFormData(prev => ({
                              ...prev,
                              simpleSchedule: { ...prev.simpleSchedule, weekday: e.target.value }
                            }))}
                            className="w-full px-3 py-2 border border-gray-700 rounded-md text-sm bg-brand-surface-bg text-brand-text-primary focus:outline-none focus:ring-2 focus:ring-brand-purple"
                          >
                            <option value="0">Sunday</option>
                            <option value="1">Monday</option>
                            <option value="2">Tuesday</option>
                            <option value="3">Wednesday</option>
                            <option value="4">Thursday</option>
                            <option value="5">Friday</option>
                            <option value="6">Saturday</option>
                          </select>
                        </div>
                      )}

                      {formData.simpleSchedule.type === 'monthly' && (
                        <div>
                          <label className="block text-xs font-medium mb-1 text-brand-text-secondary">Day of Month</label>
                          <select
                            value={formData.simpleSchedule.monthDay}
                            onChange={(e) => setFormData(prev => ({
                              ...prev,
                              simpleSchedule: { ...prev.simpleSchedule, monthDay: e.target.value }
                            }))}
                            className="w-full px-3 py-2 border border-gray-700 rounded-md text-sm bg-brand-surface-bg text-brand-text-primary focus:outline-none focus:ring-2 focus:ring-brand-purple"
                          >
                            {Array.from({ length: 28 }, (_, i) => i + 1).map(day => (
                              <option key={day} value={day}>{day}</option>
                            ))}
                          </select>
                        </div>
                      )}

                      <div className="text-xs text-brand-text-secondary">
                        Preview: {formatCronExpression(generateCronFromSimple(formData.simpleSchedule))}
                      </div>
                    </div>
                  ) : (
                    <div>
                      <label className="block text-xs font-medium mb-1 text-brand-text-secondary">Cron Expression</label>
                      <input
                        type="text"
                        value={formData.cron_expression}
                        onChange={(e) => setFormData(prev => ({ ...prev, cron_expression: e.target.value }))}
                        className="w-full px-3 py-2 border border-gray-700 rounded-md text-sm font-mono bg-brand-surface-bg text-brand-text-primary placeholder-brand-text-secondary focus:outline-none focus:ring-2 focus:ring-brand-purple"
                        placeholder="0 9 * * 1"
                        required
                      />
                      <div className="text-xs text-brand-text-secondary mt-1">
                        Preview: {formatCronExpression(formData.cron_expression)}
                      </div>
                    </div>
                  )}
                </div>
                
                <div className="mb-4">
                  <label className="block text-sm font-medium mb-1 text-brand-text-primary">Model</label>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setIsModelModalOpen(true)}
                      className="px-3 py-2 text-sm rounded bg-gray-700 hover:bg-gray-600 text-white"
                    >
                      {formModel ? `Model: ${formModel}` : 'Select Model'}
                    </button>
                    {formModel && (
                      <button
                        type="button"
                        onClick={() => setFormModel(null)}
                        className="px-2 py-1 text-xs rounded bg-gray-700 hover:bg-gray-600 text-white"
                      >
                        Clear
                      </button>
                    )}
                  </div>
                </div>

                <div className="mb-4">
                  <label className="block text-sm font-medium mb-1 text-brand-text-primary">Goal</label>
                  <textarea
                    value={formData.goal}
                    onChange={(e) => setFormData(prev => ({ ...prev, goal: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-700 rounded-md text-sm bg-brand-surface-bg text-brand-text-primary placeholder-brand-text-secondary focus:outline-none focus:ring-2 focus:ring-brand-purple"
                    rows="3"
                    placeholder="Describe what this scheduled task should accomplish..."
                    required
                  />
                </div>

                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setShowCreateForm(false)}
                    className="px-4 py-2 text-brand-text-secondary hover:bg-gray-700 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-purple"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={loading}
                    className="px-4 py-2 bg-brand-purple text-white rounded-md hover:bg-brand-button-grad-to disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-brand-purple"
                  >
                    {loading ? 'Creating...' : 'Create Schedule'}
                  </button>
                </div>
              </form>
            </div>
          )}

          <div className="space-y-3">
            {scheduledTasks.map((task) => (
              <div key={task.id} className="p-4 border border-gray-700 rounded-lg bg-brand-surface-bg">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h4 className="font-medium text-brand-text-primary">{task.name}</h4>
                      <span className={`px-2 py-1 text-xs rounded ${
                        task.schedule.enabled 
                          ? 'bg-green-700 text-green-200' 
                          : 'bg-gray-700 text-gray-300'
                      }`}>
                        {task.schedule.enabled ? 'Active' : 'Disabled'}
                      </span>
                    </div>
                    
                    <p className="text-sm text-brand-text-secondary mb-2">{task.goal}</p>
                    {task.model_name && (
                      <div className="text-xs text-brand-text-secondary mb-1">Model: {task.model_name}</div>
                    )}
                    
                    <div className="flex items-center gap-4 text-xs text-brand-text-secondary">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {formatCronExpression(task.schedule.cron_expression)}
                      </span>
                      <span>Runs: {task.run_count || 0}</span>
                      {task.next_run && (
                        <span>Next: {new Date(task.next_run).toLocaleString()}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleRunNow(task.id)}
                      className="px-2 py-1 text-xs rounded bg-blue-700 hover:bg-blue-600 text-white"
                      title="Run now"
                    >
                      Run
                    </button>
                    <button
                      onClick={() => handleRunWithModel(task.id)}
                      className="px-2 py-1 text-xs rounded bg-gray-700 hover:bg-gray-600 text-white"
                      title="Run now with model override"
                    >
                      Run with Model
                    </button>
                    <button
                      onClick={() => handleDeleteTask(task.id)}
                      className="p-2 text-red-400 hover:bg-red-900/30 rounded focus:outline-none focus:ring-2 focus:ring-red-400"
                      title="Delete scheduled task"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}

            {scheduledTasks.length === 0 && !showCreateForm && (
              <div className="text-center py-8 text-brand-text-secondary">
                <Clock className="w-12 h-12 mx-auto mb-3 text-gray-600" />
                <p>No scheduled tasks yet</p>
                <p className="text-sm">Create your first scheduled task to automate recurring work</p>
              </div>
            )}
          </div>
        </div>
      </div>
      {/* Shared Model Picker for create form or run override */}
      <ModelPickerModal
        isOpen={isModelModalOpen}
        onClose={() => { setIsModelModalOpen(false); setRunOverrideForId(null); }}
        onSelectModel={(fullName) => {
          if (runOverrideForId) {
            runScheduledTaskNow(runOverrideForId, fullName).finally(() => {
              setRunOverrideForId(null);
            });
          } else {
            setFormModel(fullName);
          }
          setIsModelModalOpen(false);
        }}
        currentModel={runOverrideForId ? null : formModel}
        onOpenSettings={() => { /* Settings modal owned by App; skip */ }}
      />
    </div>
  );
};

export default ScheduledTasksPanel;
