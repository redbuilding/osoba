import React, { useState, useEffect } from 'react';
import { X, Play, FileText, Settings } from 'lucide-react';
import { 
  listTemplates, 
  createTaskFromTemplate, 
  getTemplateParameters 
} from '../services/api';

const TaskTemplateSelector = ({ isOpen, onClose, onTaskCreated }) => {
  const [templates, setTemplates] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [parameters, setParameters] = useState({});
  const [requiredParams, setRequiredParams] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen) {
      fetchTemplates();
    }
  }, [isOpen]);

  const fetchTemplates = async () => {
    try {
      const templateList = await listTemplates();
      setTemplates(templateList);
    } catch (error) {
      setError('Failed to load templates');
    }
  };

  const handleSelectTemplate = async (template) => {
    setSelectedTemplate(template);
    setParameters({});
    
    try {
      const params = await getTemplateParameters(template.id);
      setRequiredParams(params);
      
      // Initialize parameters with default values
      const initialParams = {};
      params.forEach(param => {
        initialParams[param] = template.default_parameters?.[param] || '';
      });
      setParameters(initialParams);
    } catch (error) {
      setError('Failed to load template parameters');
    }
  };

  const handleCreateTask = async () => {
    if (!selectedTemplate) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const result = await createTaskFromTemplate(selectedTemplate.id, {
        template_id: selectedTemplate.id,
        parameters: parameters
      });
      
      onTaskCreated(result.task_id, result.rendered_goal);
      onClose();
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to create task');
    } finally {
      setLoading(false);
    }
  };

  const isFormValid = () => {
    return requiredParams.every(param => parameters[param]?.trim());
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-brand-surface-bg rounded-lg shadow-xl w-full max-w-4xl mx-4 max-h-[90vh] overflow-hidden border border-gray-700">
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h2 className="text-xl font-semibold text-brand-text-primary">Task Templates</h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-700 rounded focus:outline-none focus:ring-2 focus:ring-brand-purple"
          >
            <X className="w-5 h-5 text-brand-text-secondary" />
          </button>
        </div>

        <div className="flex h-[70vh]">
          {/* Template List */}
          <div className="w-1/2 border-r border-gray-700 overflow-y-auto bg-brand-main-bg">
            <div className="p-4">
              <h3 className="font-medium mb-3 text-brand-text-primary">Available Templates</h3>
              {templates.map((template) => (
                <div
                  key={template.id}
                  onClick={() => handleSelectTemplate(template)}
                  className={`p-3 border rounded-lg cursor-pointer mb-2 hover:bg-gray-700 ${
                    selectedTemplate?.id === template.id ? 'border-brand-purple bg-brand-purple/10' : 'border-gray-700'
                  }`}
                >
                  <div className="flex items-start">
                    <FileText className="w-4 h-4 mt-1 mr-2 text-brand-text-secondary" />
                    <div className="flex-1">
                      <div className="font-medium text-sm text-brand-text-primary">{template.name}</div>
                      <div className="text-xs text-brand-text-secondary mt-1">{template.description}</div>
                      <div className="text-xs text-brand-blue mt-1 capitalize">{template.category}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Template Details & Parameters */}
          <div className="w-1/2 overflow-y-auto bg-brand-main-bg">
            {selectedTemplate ? (
              <div className="p-4">
                <h3 className="font-medium mb-3 text-brand-text-primary">Configure Template</h3>
                
                <div className="mb-4">
                  <h4 className="font-medium text-sm mb-2 text-brand-text-primary">{selectedTemplate.name}</h4>
                  <p className="text-sm text-brand-text-secondary mb-3">{selectedTemplate.description}</p>
                  
                  <div className="bg-brand-surface-bg border border-gray-700 p-3 rounded text-sm">
                    <strong className="text-brand-text-primary">Goal Template:</strong>
                    <div className="mt-1 font-mono text-xs text-brand-text-secondary">{selectedTemplate.goal_template}</div>
                  </div>
                </div>

                {requiredParams.length > 0 && (
                  <div className="mb-4">
                    <h4 className="font-medium text-sm mb-2 flex items-center text-brand-text-primary">
                      <Settings className="w-4 h-4 mr-1" />
                      Parameters
                    </h4>
                    {requiredParams.map((param) => (
                      <div key={param} className="mb-3">
                        <label className="block text-sm font-medium mb-1 text-brand-text-primary">
                          {param.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        </label>
                        <input
                          type="text"
                          value={parameters[param] || ''}
                          onChange={(e) => setParameters(prev => ({
                            ...prev,
                            [param]: e.target.value
                          }))}
                          className="w-full px-3 py-2 border border-gray-700 rounded-md text-sm bg-brand-surface-bg text-brand-text-primary placeholder-brand-text-secondary focus:outline-none focus:ring-2 focus:ring-brand-purple"
                          placeholder={`Enter ${param.replace(/_/g, ' ')}`}
                        />
                      </div>
                    ))}
                  </div>
                )}

                {error && (
                  <div className="mb-4 p-3 bg-red-900/30 border border-red-700 rounded text-sm text-red-400">
                    {error}
                  </div>
                )}

                <button
                  onClick={handleCreateTask}
                  disabled={!isFormValid() || loading}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-brand-purple text-white rounded-md hover:bg-brand-button-grad-to disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-brand-purple"
                >
                  <Play className="w-4 h-4" />
                  {loading ? 'Creating Task...' : 'Create Task'}
                </button>
              </div>
            ) : (
              <div className="p-4 text-center text-brand-text-secondary">
                Select a template to configure and create a task
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default TaskTemplateSelector;
