import React from 'react';
import { Settings, User, Key, Palette } from 'lucide-react';

const SettingsSidebar = ({ activeSection, onSectionChange }) => {
  const sections = [
    {
      id: 'profiles',
      label: 'AI Profiles',
      icon: User,
      description: 'Manage your AI assistants'
    },
    {
      id: 'providers',
      label: 'Model Providers',
      icon: Key,
      description: 'Configure API keys'
    },
    {
      id: 'appearance',
      label: 'Appearance',
      icon: Palette,
      description: 'Theme and display settings'
    }
  ];

  return (
    <div className="w-64 bg-gray-50 border-r border-gray-200 h-full flex flex-col">
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center space-x-2">
          <Settings className="w-5 h-5 text-gray-600" />
          <h1 className="text-lg font-semibold text-gray-900">Settings</h1>
        </div>
      </div>
      
      <nav className="flex-1 p-4">
        <ul className="space-y-2">
          {sections.map((section) => {
            const Icon = section.icon;
            const isActive = activeSection === section.id;
            
            return (
              <li key={section.id}>
                <button
                  onClick={() => onSectionChange(section.id)}
                  className={`w-full flex items-start space-x-3 p-3 rounded-lg text-left transition-colors ${
                    isActive
                      ? 'bg-blue-50 text-blue-700 border border-blue-200'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  <Icon className={`w-5 h-5 mt-0.5 ${isActive ? 'text-blue-600' : 'text-gray-500'}`} />
                  <div>
                    <div className={`font-medium ${isActive ? 'text-blue-700' : 'text-gray-900'}`}>
                      {section.label}
                    </div>
                    <div className={`text-sm ${isActive ? 'text-blue-600' : 'text-gray-500'}`}>
                      {section.description}
                    </div>
                  </div>
                </button>
              </li>
            );
          })}
        </ul>
      </nav>
      
      <div className="p-4 border-t border-gray-200">
        <div className="text-xs text-gray-500">
          Settings are saved automatically
        </div>
      </div>
    </div>
  );
};

export default SettingsSidebar;
