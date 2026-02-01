import React, { useState } from 'react';
import SettingsSidebar from '../components/SettingsSidebar';
import ProfileManager from '../components/ProfileManager';
import SettingsModal from '../components/SettingsModal';

const SettingsPage = ({ onClose }) => {
  const [activeSection, setActiveSection] = useState('profiles');

  const renderContent = () => {
    switch (activeSection) {
      case 'profiles':
        return <ProfileManager />;
      case 'providers':
        return (
          <div>
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-gray-900">Model Providers</h2>
              <p className="text-gray-600 mt-1">
                Configure API keys for different AI model providers.
              </p>
            </div>
            <div className="bg-white rounded-lg border border-gray-200">
              <SettingsModal 
                isOpen={true} 
                onClose={() => {}} 
                onSettingsUpdate={() => {}}
                embedded={true}
              />
            </div>
          </div>
        );
      case 'appearance':
        return (
          <div>
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-gray-900">Appearance</h2>
              <p className="text-gray-600 mt-1">
                Customize the look and feel of your chat interface.
              </p>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <div className="text-center py-12">
                <div className="text-gray-400 mb-4">
                  <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zM21 5a2 2 0 00-2-2h-4a2 2 0 00-2 2v12a4 4 0 004 4h4a4 4 0 004-4V5z" />
                  </svg>
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">Coming Soon</h3>
                <p className="text-gray-600">
                  Theme customization and appearance settings will be available in a future update.
                </p>
              </div>
            </div>
          </div>
        );
      default:
        return <ProfileManager />;
    }
  };

  return (
    <div className="fixed inset-0 bg-white z-50 flex">
      {/* Sidebar */}
      <SettingsSidebar 
        activeSection={activeSection} 
        onSectionChange={setActiveSection} 
      />
      
      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h1 className="text-xl font-semibold text-gray-900">
              {activeSection === 'profiles' && 'AI Profiles'}
              {activeSection === 'providers' && 'Model Providers'}
              {activeSection === 'appearance' && 'Appearance'}
            </h1>
          </div>
          
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-md transition-colors"
          >
            Close
          </button>
        </div>
        
        {/* Content Area */}
        <div className="flex-1 overflow-auto">
          <div className="max-w-4xl mx-auto p-6">
            {renderContent()}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
