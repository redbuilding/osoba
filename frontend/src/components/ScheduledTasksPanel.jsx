import React, { useState, useEffect } from 'react';
import { X, Clock, Plus, Trash2, Calendar } from 'lucide-react';
import { 
  listScheduledTasks, 
  createScheduledTask, 
  deleteScheduledTask 
} from '../services/api';

const ScheduledTasksPanel = ({ isOpen, onClose }) => {
  const [scheduledTasks, setScheduledTasks] = useState([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [formData, setFormData] = useState({
    name: '',
    goal: '',
    cron_expression: '0 9 * * 1', // Default: Every Monday at 9 AM
    timezone: 'UTC',
    enabled: true
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

  const handleCreateTask = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await createScheduledTask({
        name: formData.name,
        goal: formData.goal,
        schedule: {
          cron_expression: formData.cron_expression,
          timezone: formData.timezone,
          enabled: formData.enabled
        }
      });

      setFormData({
        name: '',
        goal: '',
        cron_expression: '0 9 * * 1',
        timezone: 'UTC',
        enabled: true
      });
      setShowCreateForm(false);
      fetchScheduledTasks();
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to create scheduled task');
    } finally {
      setLoading(false);
    }
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
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl mx-4 max-h-[90vh] overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-xl font-semibold flex items-center">
            <Clock className="w-5 h-5 mr-2" />
            Scheduled Tasks
          </h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-4 max-h-[70vh] overflow-y-auto">
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-600">
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
            <div className="mb-6 p-4 border border-gray-200 rounded-lg bg-gray-50">
              <h4 className="font-medium mb-3">Create Scheduled Task</h4>
              <form onSubmit={handleCreateTask}>
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Task Name</label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Cron Expression</label>
                    <input
                      type="text"
                      value={formData.cron_expression}
                      onChange={(e) => setFormData(prev => ({ ...prev, cron_expression: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm font-mono"
                      placeholder="0 9 * * 1"
                      required
                    />
                    <div className="text-xs text-gray-500 mt-1">
                      Preview: {formatCronExpression(formData.cron_expression)}
                    </div>
                  </div>
                </div>
                
                <div className="mb-4">
                  <label className="block text-sm font-medium mb-1">Goal</label>
                  <textarea
                    value={formData.goal}
                    onChange={(e) => setFormData(prev => ({ ...prev, goal: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                    rows="3"
                    placeholder="Describe what this scheduled task should accomplish..."
                    required
                  />
                </div>

                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setShowCreateForm(false)}
                    className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-md"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={loading}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                  >
                    {loading ? 'Creating...' : 'Create Schedule'}
                  </button>
                </div>
              </form>
            </div>
          )}

          <div className="space-y-3">
            {scheduledTasks.map((task) => (
              <div key={task.id} className="p-4 border border-gray-200 rounded-lg">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h4 className="font-medium">{task.name}</h4>
                      <span className={`px-2 py-1 text-xs rounded ${
                        task.schedule.enabled 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {task.schedule.enabled ? 'Active' : 'Disabled'}
                      </span>
                    </div>
                    
                    <p className="text-sm text-gray-600 mb-2">{task.goal}</p>
                    
                    <div className="flex items-center gap-4 text-xs text-gray-500">
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
                  
                  <button
                    onClick={() => handleDeleteTask(task.id)}
                    className="p-2 text-red-600 hover:bg-red-50 rounded"
                    title="Delete scheduled task"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}

            {scheduledTasks.length === 0 && !showCreateForm && (
              <div className="text-center py-8 text-gray-500">
                <Clock className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                <p>No scheduled tasks yet</p>
                <p className="text-sm">Create your first scheduled task to automate recurring work</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ScheduledTasksPanel;
