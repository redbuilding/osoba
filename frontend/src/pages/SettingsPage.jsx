import React, { useEffect, useState } from 'react';
import SettingsSidebar from '../components/SettingsSidebar';
import ProfileManager from '../components/ProfileManager';
import SettingsModal from '../components/SettingsModal';
import UserProfileSettings from '../components/UserProfileSettings';
import GoalsEditor from '../components/GoalsEditor';
import { MemorySettings } from '../components/memory';
import EnhancedHeartbeatSettings from '../components/EnhancedHeartbeatSettings';

const SettingsPage = ({ onClose }) => {
  const [activeSection, setActiveSection] = useState('profiles');
  const [entered, setEntered] = useState(false);
  const [leaving, setLeaving] = useState(false);

  useEffect(() => {
    // trigger enter animation on mount
    const t = setTimeout(() => setEntered(true), 10);
    return () => clearTimeout(t);
  }, []);

  const handleClose = () => {
    // play exit animation before unmounting
    setLeaving(true);
    setTimeout(() => {
      onClose && onClose();
    }, 300);
  };

  const renderContent = () => {
    switch (activeSection) {
      case 'profiles':
        return <ProfileManager />;
      case 'user-profile':
        return (
          <div>
            <div className="mb-6">
              <h2 className="text-2xl font-semibold text-brand-text-primary">User Profile</h2>
              <p className="text-brand-text-secondary mt-1">
                Configure your personal information and preferences for better AI assistance.
              </p>
            </div>
            <div className="bg-brand-surface-bg rounded-lg border border-gray-700 p-6">
              <UserProfileSettings onProfileUpdate={() => {}} />
            </div>
          </div>
        );
      case 'goals':
        return (
          <div>
            <div className="mb-6">
              <h2 className="text-2xl font-semibold text-brand-text-primary">Goals & Priorities</h2>
              <p className="text-brand-text-secondary mt-1">
                Define your goals and priorities for proactive AI assistance.
              </p>
            </div>
            <GoalsEditor userId="default" />
          </div>
        );
      case 'providers':
        return (
          <div>
            <div className="mb-6">
              <h2 className="text-2xl font-semibold text-brand-text-primary">Model Providers</h2>
              <p className="text-brand-text-secondary mt-1">
                Configure API keys for different AI model providers.
              </p>
            </div>
            <div className="bg-brand-surface-bg rounded-lg border border-gray-700">
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
              <h2 className="text-2xl font-semibold text-brand-text-primary">Appearance</h2>
              <p className="text-brand-text-secondary mt-1">
                Customize the look and feel of your chat interface.
              </p>
            </div>
            <div className="bg-brand-surface-bg rounded-lg border border-gray-700 p-6">
              <div className="text-center py-12">
                <div className="text-brand-text-secondary mb-4">
                  <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zM21 5a2 2 0 00-2-2h-4a2 2 0 00-2 2v12a4 4 0 004 4h4a4 4 0 004-4V5z" />
                  </svg>
                </div>
                <h3 className="text-lg font-medium text-brand-text-primary mb-2">Coming Soon</h3>
                <p className="text-brand-text-secondary">
                  Theme customization and appearance settings will be available in a future update.
                </p>
              </div>
            </div>
          </div>
        );
      case 'memory':
        return (
          <div>
            <div className="mb-6">
              <h2 className="text-2xl font-semibold text-brand-text-primary">Semantic Memory</h2>
              <p className="text-brand-text-secondary mt-1">
                Manage your conversation memory and semantic search settings.
              </p>
            </div>
            <div className="bg-brand-surface-bg rounded-lg border border-gray-700 p-6">
              <MemorySettings />
            </div>
          </div>
        );
      case 'heartbeat':
        return (
          <div>
            <div className="mb-6">
              <h2 className="text-2xl font-semibold text-brand-text-primary">Proactive Heartbeat</h2>
              <p className="text-brand-text-secondary mt-1">
                Configure automated insights and task creation from your activity.
              </p>
            </div>
            <EnhancedHeartbeatSettings />
          </div>
        );
      default:
        return <ProfileManager />;
    }
  };

  return (
    <div className="fixed inset-0 bg-brand-main-bg z-50 overflow-hidden">
      <div className={`h-full flex transform transition-transform duration-300 ease-in-out ${entered && !leaving ? 'translate-y-0' : '-translate-y-full'}`}>
        {/* Sidebar */}
        <SettingsSidebar 
          activeSection={activeSection} 
          onSectionChange={setActiveSection} 
        />
        
        {/* Main Content */}
        <div className="flex-1 flex flex-col">
          {/* Header */}
          <div className="bg-brand-surface-bg border-b border-gray-700 px-6 py-4 flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <h1 className="text-xl font-semibold text-brand-text-primary">
                {activeSection === 'profiles' && 'AI Profiles'}
                {activeSection === 'user-profile' && 'User Profile'}
                {activeSection === 'providers' && 'Model Providers'}
                {activeSection === 'appearance' && 'Appearance'}
              </h1>
            </div>
            
            <button
              onClick={handleClose}
              className="px-4 py-2 text-brand-text-secondary hover:text-brand-text-primary hover:bg-gray-700 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-brand-purple"
            >
              Close
            </button>
          </div>
          
          {/* Content Area */}
          <div className="flex-1 overflow-auto">
            <div className="max-w-4xl mx-auto p-6 text-brand-text-primary">
              {renderContent()}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
