# React Frontend Patterns for User Profile Management & Conversation Pinning

## Overview
Research on modern React patterns for enhancing user profile management and conversation sidebar functionality in the OhSee application. Focus on minimal, performant implementations using modern React hooks and state management.

## 1. User Profile Management Patterns

### Current Implementation Analysis
The existing `ProfileManager.jsx` uses a clean pattern with:
- State management via `useState` hooks
- API integration with proper error handling
- Loading states and user feedback
- Form modal pattern for create/edit operations

### Enhanced Profile Management Patterns

#### A. Profile Quick Switcher Component
```jsx
const ProfileQuickSwitcher = ({ profiles, activeProfile, onProfileChange }) => {
  const [isOpen, setIsOpen] = useState(false);
  
  return (
    <div className="relative">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 p-2 rounded-md hover:bg-gray-700"
      >
        <User className="w-4 h-4" />
        <span className="text-sm truncate max-w-24">
          {activeProfile?.name || 'Default'}
        </span>
        <ChevronDown className="w-3 h-3" />
      </button>
      
      {isOpen && (
        <div className="absolute top-full left-0 mt-1 w-48 bg-brand-surface-bg border border-gray-700 rounded-md shadow-lg z-50">
          <div className="p-1">
            <button
              onClick={() => {
                onProfileChange(null);
                setIsOpen(false);
              }}
              className={`w-full text-left px-3 py-2 text-sm rounded hover:bg-gray-700 ${
                !activeProfile ? 'bg-brand-purple text-white' : ''
              }`}
            >
              Default (No Profile)
            </button>
            {profiles.map(profile => (
              <button
                key={profile._id}
                onClick={() => {
                  onProfileChange(profile);
                  setIsOpen(false);
                }}
                className={`w-full text-left px-3 py-2 text-sm rounded hover:bg-gray-700 ${
                  activeProfile?._id === profile._id ? 'bg-brand-purple text-white' : ''
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="truncate">{profile.name}</span>
                  {profile.is_active && <Star className="w-3 h-3" />}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
```

#### B. Profile Status Indicator
```jsx
const ProfileStatusIndicator = ({ profile }) => {
  if (!profile) return null;
  
  const getStyleColor = (style) => {
    const colors = {
      professional: 'bg-blue-500',
      friendly: 'bg-green-500',
      casual: 'bg-yellow-500',
      technical: 'bg-purple-500',
      creative: 'bg-pink-500',
      supportive: 'bg-teal-500'
    };
    return colors[style] || 'bg-gray-500';
  };
  
  return (
    <div className="flex items-center space-x-2 text-xs text-brand-text-secondary">
      <div className={`w-2 h-2 rounded-full ${getStyleColor(profile.communication_style)}`} />
      <span>{profile.name}</span>
    </div>
  );
};
```

#### C. Inline Profile Editor Hook
```jsx
const useInlineProfileEditor = () => {
  const [editingField, setEditingField] = useState(null);
  const [tempValue, setTempValue] = useState('');
  
  const startEdit = (field, currentValue) => {
    setEditingField(field);
    setTempValue(currentValue);
  };
  
  const cancelEdit = () => {
    setEditingField(null);
    setTempValue('');
  };
  
  const saveEdit = async (profileId, field, value, onSave) => {
    try {
      await onSave(profileId, { [field]: value });
      setEditingField(null);
      setTempValue('');
    } catch (error) {
      console.error('Save failed:', error);
    }
  };
  
  return {
    editingField,
    tempValue,
    setTempValue,
    startEdit,
    cancelEdit,
    saveEdit,
    isEditing: (field) => editingField === field
  };
};
```

## 2. Conversation Pinning & Management Patterns

### Enhanced Conversation Sidebar Features

#### A. Conversation Pinning Hook
```jsx
const useConversationPinning = () => {
  const [pinnedConversations, setPinnedConversations] = useState([]);
  
  const togglePin = useCallback(async (conversationId) => {
    try {
      const isPinned = pinnedConversations.includes(conversationId);
      
      if (isPinned) {
        await api.unpinConversation(conversationId);
        setPinnedConversations(prev => prev.filter(id => id !== conversationId));
      } else {
        await api.pinConversation(conversationId);
        setPinnedConversations(prev => [...prev, conversationId]);
      }
    } catch (error) {
      console.error('Pin toggle failed:', error);
    }
  }, [pinnedConversations]);
  
  const sortConversations = useCallback((conversations) => {
    const pinned = conversations.filter(conv => pinnedConversations.includes(conv.id));
    const unpinned = conversations.filter(conv => !pinnedConversations.includes(conv.id));
    
    return [
      ...pinned.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at)),
      ...unpinned.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at))
    ];
  }, [pinnedConversations]);
  
  return { pinnedConversations, togglePin, sortConversations };
};
```

#### B. Enhanced Conversation Item Component
```jsx
const ConversationItem = ({ 
  conversation, 
  isActive, 
  isPinned, 
  onSelect, 
  onPin, 
  onRename, 
  onDelete,
  isCollapsed 
}) => {
  const [isHovered, setIsHovered] = useState(false);
  const { isEditing, startEdit, cancelEdit, saveEdit } = useInlineEditor();
  
  return (
    <div 
      className={`relative group ${isCollapsed ? 'p-2' : 'p-3'} rounded-md transition-colors
        ${isActive ? 'bg-brand-purple text-white' : 'hover:bg-gray-700'}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="flex items-center space-x-2">
        {isPinned && (
          <Pin className="w-3 h-3 text-brand-purple flex-shrink-0" />
        )}
        <MessageSquare className="w-4 h-4 flex-shrink-0" />
        
        {!isCollapsed && (
          <div className="flex-1 min-w-0">
            {isEditing ? (
              <input
                value={tempValue}
                onChange={(e) => setTempValue(e.target.value)}
                onBlur={() => saveEdit(conversation.id, 'title', tempValue, onRename)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') saveEdit(conversation.id, 'title', tempValue, onRename);
                  if (e.key === 'Escape') cancelEdit();
                }}
                className="w-full bg-gray-600 text-white text-sm p-1 rounded"
                autoFocus
              />
            ) : (
              <div onClick={() => onSelect(conversation.id)}>
                <p className="text-sm font-medium truncate">
                  {conversation.title || `Chat from ${formatDate(conversation.created_at)}`}
                </p>
                <p className="text-xs opacity-75 truncate">
                  {conversation.message_count} messages
                </p>
              </div>
            )}
          </div>
        )}
      </div>
      
      {/* Action buttons */}
      {!isCollapsed && (isHovered || isActive) && !isEditing && (
        <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onPin(conversation.id);
            }}
            className={`p-1 rounded hover:bg-gray-600 ${isPinned ? 'text-brand-purple' : 'text-gray-400'}`}
            title={isPinned ? 'Unpin' : 'Pin'}
          >
            <Pin className="w-3 h-3" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              startEdit('title', conversation.title);
            }}
            className="p-1 rounded hover:bg-gray-600 text-gray-400"
            title="Rename"
          >
            <Pencil className="w-3 h-3" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete(conversation.id);
            }}
            className="p-1 rounded hover:bg-gray-600 text-gray-400 hover:text-red-400"
            title="Delete"
          >
            <Trash2 className="w-3 h-3" />
          </button>
        </div>
      )}
    </div>
  );
};
```

#### C. Conversation Grouping Hook
```jsx
const useConversationGrouping = (conversations) => {
  return useMemo(() => {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000);
    const weekAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
    
    const groups = {
      pinned: [],
      today: [],
      yesterday: [],
      thisWeek: [],
      older: []
    };
    
    conversations.forEach(conv => {
      const updatedAt = new Date(conv.updated_at);
      
      if (conv.is_pinned) {
        groups.pinned.push(conv);
      } else if (updatedAt >= today) {
        groups.today.push(conv);
      } else if (updatedAt >= yesterday) {
        groups.yesterday.push(conv);
      } else if (updatedAt >= weekAgo) {
        groups.thisWeek.push(conv);
      } else {
        groups.older.push(conv);
      }
    });
    
    return groups;
  }, [conversations]);
};
```

## 3. Settings Modal Enhancement Patterns

### A. Tabbed Settings Interface
```jsx
const TabbedSettingsModal = ({ isOpen, onClose }) => {
  const [activeTab, setActiveTab] = useState('providers');
  
  const tabs = [
    { id: 'providers', label: 'Providers', icon: Server },
    { id: 'profiles', label: 'Profiles', icon: User },
    { id: 'preferences', label: 'Preferences', icon: Settings },
    { id: 'shortcuts', label: 'Shortcuts', icon: Keyboard }
  ];
  
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[80vh]">
        <div className="flex h-full">
          {/* Sidebar */}
          <div className="w-48 border-r border-gray-700 p-4">
            <nav className="space-y-1">
              {tabs.map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center space-x-2 px-3 py-2 text-sm rounded-md transition-colors
                    ${activeTab === tab.id 
                      ? 'bg-brand-purple text-white' 
                      : 'text-brand-text-secondary hover:bg-gray-700'
                    }`}
                >
                  <tab.icon className="w-4 h-4" />
                  <span>{tab.label}</span>
                </button>
              ))}
            </nav>
          </div>
          
          {/* Content */}
          <div className="flex-1 p-6">
            {activeTab === 'providers' && <ProviderSettings />}
            {activeTab === 'profiles' && <ProfileManager embedded />}
            {activeTab === 'preferences' && <PreferencesPanel />}
            {activeTab === 'shortcuts' && <ShortcutsPanel />}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
```

### B. Keyboard Shortcuts Hook
```jsx
const useKeyboardShortcuts = () => {
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Cmd/Ctrl + K for command palette
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        // Open command palette
      }
      
      // Cmd/Ctrl + , for settings
      if ((e.metaKey || e.ctrlKey) && e.key === ',') {
        e.preventDefault();
        // Open settings
      }
      
      // Cmd/Ctrl + N for new chat
      if ((e.metaKey || e.ctrlKey) && e.key === 'n') {
        e.preventDefault();
        // Create new chat
      }
      
      // Cmd/Ctrl + P for profile switcher
      if ((e.metaKey || e.ctrlKey) && e.key === 'p') {
        e.preventDefault();
        // Open profile switcher
      }
    };
    
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);
};
```

## 4. State Management Patterns

### A. Conversation State Hook
```jsx
const useConversationState = () => {
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [pinnedIds, setPinnedIds] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const { sortConversations, togglePin } = useConversationPinning();
  
  const sortedConversations = useMemo(() => 
    sortConversations(conversations), 
    [conversations, sortConversations]
  );
  
  const currentConversation = useMemo(() => 
    conversations.find(conv => conv.id === currentConversationId),
    [conversations, currentConversationId]
  );
  
  const createNewConversation = useCallback(async () => {
    try {
      setIsLoading(true);
      const newConv = await api.createConversation();
      setConversations(prev => [newConv, ...prev]);
      setCurrentConversationId(newConv.id);
      return newConv;
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, []);
  
  return {
    conversations: sortedConversations,
    currentConversation,
    currentConversationId,
    setCurrentConversationId,
    createNewConversation,
    togglePin,
    isLoading,
    error
  };
};
```

### B. Profile State Hook
```jsx
const useProfileState = () => {
  const [profiles, setProfiles] = useState([]);
  const [activeProfile, setActiveProfile] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  
  const activateProfile = useCallback(async (profileId) => {
    try {
      setIsLoading(true);
      await api.activateProfile(profileId);
      
      setProfiles(prev => prev.map(p => ({
        ...p,
        is_active: p._id === profileId
      })));
      
      const profile = profiles.find(p => p._id === profileId);
      setActiveProfile(profile);
    } catch (error) {
      console.error('Failed to activate profile:', error);
    } finally {
      setIsLoading(false);
    }
  }, [profiles]);
  
  return {
    profiles,
    activeProfile,
    activateProfile,
    isLoading
  };
};
```

## 5. Performance Optimization Patterns

### A. Virtual Scrolling for Large Conversation Lists
```jsx
import { FixedSizeList as List } from 'react-window';

const VirtualizedConversationList = ({ conversations, onSelect, currentId }) => {
  const Row = ({ index, style }) => (
    <div style={style}>
      <ConversationItem
        conversation={conversations[index]}
        isActive={conversations[index].id === currentId}
        onSelect={onSelect}
      />
    </div>
  );
  
  return (
    <List
      height={400}
      itemCount={conversations.length}
      itemSize={60}
      className="conversation-list"
    >
      {Row}
    </List>
  );
};
```

### B. Debounced Search Hook
```jsx
const useDebouncedSearch = (searchTerm, delay = 300) => {
  const [debouncedTerm, setDebouncedTerm] = useState(searchTerm);
  
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedTerm(searchTerm);
    }, delay);
    
    return () => clearTimeout(handler);
  }, [searchTerm, delay]);
  
  return debouncedTerm;
};
```

## 6. Accessibility Patterns

### A. Focus Management Hook
```jsx
const useFocusManagement = () => {
  const focusRef = useRef(null);
  
  const trapFocus = useCallback((element) => {
    const focusableElements = element.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];
    
    const handleTabKey = (e) => {
      if (e.key === 'Tab') {
        if (e.shiftKey && document.activeElement === firstElement) {
          e.preventDefault();
          lastElement.focus();
        } else if (!e.shiftKey && document.activeElement === lastElement) {
          e.preventDefault();
          firstElement.focus();
        }
      }
    };
    
    element.addEventListener('keydown', handleTabKey);
    return () => element.removeEventListener('keydown', handleTabKey);
  }, []);
  
  return { focusRef, trapFocus };
};
```

## 7. Implementation Recommendations

### Priority Order for OhSee Enhancement:

1. **Profile Quick Switcher** - Add to header/sidebar for easy profile switching
2. **Conversation Pinning** - Enhance existing sidebar with pin functionality
3. **Tabbed Settings Modal** - Organize growing settings into tabs
4. **Keyboard Shortcuts** - Add common shortcuts for power users
5. **Virtual Scrolling** - Optimize for users with many conversations

### Minimal Implementation Strategy:

1. Start with conversation pinning hook and UI
2. Add profile quick switcher to existing header
3. Enhance settings modal with tabs
4. Add keyboard shortcuts gradually
5. Implement virtual scrolling if performance issues arise

### Key Libraries to Consider:

- `@radix-ui/react-dialog` - For enhanced modals
- `react-window` - For virtual scrolling
- `cmdk` - For command palette (future enhancement)
- `framer-motion` - For smooth animations
- `react-hotkeys-hook` - For keyboard shortcuts

This research provides a foundation for implementing modern, accessible, and performant user interface patterns while maintaining the existing design system and architecture of the OhSee application.