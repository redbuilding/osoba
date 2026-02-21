import React from 'react';
import { Settings, User, Key, Palette, UserCircle, Target, Brain } from 'lucide-react';

const SettingsSidebar = ({ activeSection, onSectionChange }) => {
  const sections = [
    {
      id: 'profiles',
      label: 'AI Profiles',
      icon: User,
      description: 'Manage your AI assistants'
    },
    {
      id: 'user-profile',
      label: 'User Profile',
      icon: UserCircle,
      description: 'Your personal information'
    },
    {
      id: 'goals',
      label: 'Goals & Priorities',
      icon: Target,
      description: 'Define your objectives'
    },
    {
      id: 'providers',
      label: 'Model Providers',
      icon: Key,
      description: 'Configure API keys'
    },
    {
      id: 'memory',
      label: 'Semantic Memory',
      icon: Brain,
      description: 'Conversation memory settings'
    },
    {
      id: 'appearance',
      label: 'Appearance',
      icon: Palette,
      description: 'Theme and display settings'
    }
  ];

  return (
    <div className="w-64 bg-brand-surface-bg border-r border-gray-700 h-full flex flex-col text-brand-text-primary">
      <div className="p-6 border-b border-gray-700">
        <div className="flex items-center space-x-2">
          <Settings className="w-5 h-5 text-brand-text-secondary" />
          <h1 className="text-lg font-semibold">Settings</h1>
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
                  className={`w-full flex items-start space-x-3 p-3 rounded-lg text-left transition-colors border ${
                    isActive
                      ? 'bg-black/30 border-gray-700 text-brand-purple'
                      : 'border-transparent text-brand-text-secondary hover:bg-gray-800'
                  } focus:outline-none focus:ring-2 focus:ring-brand-purple`}
                >
                  <Icon className={`w-5 h-5 mt-0.5 ${isActive ? 'text-brand-purple' : 'text-brand-text-secondary'}`} />
                  <div>
                    <div className={`font-medium ${isActive ? 'text-brand-text-primary' : 'text-brand-text-primary'}`}>
                      {section.label}
                    </div>
                    <div className={`text-sm ${isActive ? 'text-brand-purple' : 'text-brand-text-secondary'}`}>
                      {section.description}
                    </div>
                  </div>
                </button>
              </li>
            );
          })}
        </ul>
      </nav>
      
      <div className="p-4 border-t border-gray-700">
        <div className="text-xs text-brand-text-secondary">
          Remember to save your changes
        </div>
      </div>
    </div>
  );
};

export default SettingsSidebar;
