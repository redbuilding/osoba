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
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl mx-4 max-h-[90vh] overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-xl font-semibold">Task Templates</h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex h-[70vh]">
          {/* Template List */}
          <div className="w-1/2 border-r overflow-y-auto">
            <div className="p-4">
              <h3 className="font-medium mb-3">Available Templates</h3>
              {templates.map((template) => (
                <div
                  key={template.id}
                  onClick={() => handleSelectTemplate(template)}
                  className={`p-3 border rounded-lg cursor-pointer mb-2 hover:bg-gray-50 ${
                    selectedTemplate?.id === template.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                  }`}
                >
                  <div className="flex items-start">
                    <FileText className="w-4 h-4 mt-1 mr-2 text-gray-500" />
                    <div className="flex-1">
                      <div className="font-medium text-sm">{template.name}</div>
                      <div className="text-xs text-gray-500 mt-1">{template.description}</div>
                      <div className="text-xs text-blue-600 mt-1 capitalize">{template.category}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Template Details & Parameters */}
          <div className="w-1/2 overflow-y-auto">
            {selectedTemplate ? (
              <div className="p-4">
                <h3 className="font-medium mb-3">Configure Template</h3>
                
                <div className="mb-4">
                  <h4 className="font-medium text-sm mb-2">{selectedTemplate.name}</h4>
                  <p className="text-sm text-gray-600 mb-3">{selectedTemplate.description}</p>
                  
                  <div className="bg-gray-50 p-3 rounded text-sm">
                    <strong>Goal Template:</strong>
                    <div className="mt-1 font-mono text-xs">{selectedTemplate.goal_template}</div>
                  </div>
                </div>

                {requiredParams.length > 0 && (
                  <div className="mb-4">
                    <h4 className="font-medium text-sm mb-2 flex items-center">
                      <Settings className="w-4 h-4 mr-1" />
                      Parameters
                    </h4>
                    {requiredParams.map((param) => (
                      <div key={param} className="mb-3">
                        <label className="block text-sm font-medium mb-1">
                          {param.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        </label>
                        <input
                          type="text"
                          value={parameters[param] || ''}
                          onChange={(e) => setParameters(prev => ({
                            ...prev,
                            [param]: e.target.value
                          }))}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                          placeholder={`Enter ${param.replace(/_/g, ' ')}`}
                        />
                      </div>
                    ))}
                  </div>
                )}

                {error && (
                  <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-600">
                    {error}
                  </div>
                )}

                <button
                  onClick={handleCreateTask}
                  disabled={!isFormValid() || loading}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Play className="w-4 h-4" />
                  {loading ? 'Creating Task...' : 'Create Task'}
                </button>
              </div>
            ) : (
              <div className="p-4 text-center text-gray-500">
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
