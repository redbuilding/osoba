# OhSee Heartbeat Integration Design

**Date:** 2026-02-17  
**Status:** Architecture Design Complete  
**Objective:** Integrate Heartbeat Service with OhSee's existing systems

---

## Current Architecture Understanding

### 1. Existing Task System (`services/task_runner.py`)
- **TaskRunner**: Long-running task execution with steps, retries, budgets
- **TaskDispatcher**: Scans and schedules tasks every N seconds
- **MongoDB storage**: Tasks persisted with state (pending, running, completed, failed)
- **Progress bus**: Real-time updates to frontend
- **Tools integration**: Web search, SQL, Python, YouTube, etc.

### 2. Settings System (`db/settings_crud.py`)
- **Encrypted storage**: API keys stored with Fernet encryption
- **User-scoped**: Settings per user_id (default: "default")
- **Provider configs**: OpenAI, Anthropic, etc. API keys
- **Validation**: Runtime validation of settings

### 3. UI Pattern (`SettingsPage.jsx`, `SettingsSidebar.jsx`)
- **Slide-over panel**: Settings slides down from top (z-50 overlay)
- **Sidebar navigation**: 4 sections (Profiles, User Profile, Providers, Appearance)
- **Section switching**: `activeSection` state drives content
- **Embedded components**: SettingsModal reused in providers section

### 4. Memory System
- **MEMORY.md**: Long-term curated memory
- **memory/YYYY-MM-DD.md**: Daily logs
- **Vector search**: Semantic retrieval of past context
- **Session memory**: Just enabled (experimental)

---

## Integration Design

### A. Opt-In/Opt-Out Architecture

**User Control Levels:**

```
Level 1: Master Switch (kill switch)
  └─ Enabled/Disabled in Settings
  └─ Stored in user_settings.heartbeat.enabled
  
Level 2: Task Categories
  └─ Memory maintenance: [✓]
  └─ Test execution: [✓]  
  └─ Proactive messages: [ ]
  └─ File cleanup: [✓]
  
Level 3: Individual Tasks (from HEARTBEAT.md)
  └─ [✓] Check memory files every hour
  └─ [ ] Run security tests daily
  └─ [✓] Commit changes hourly
```

**Implementation:**

```python
# db/settings_crud.py addition
heartbeat_settings = {
    "enabled": False,  # Default: OFF (opt-in)
    "global_quiet_hours": {"start": 23, "end": 7},
    "categories": {
        "memory": {"enabled": True, "max_frequency": "hourly"},
        "testing": {"enabled": False, "max_frequency": "daily"},
        "messaging": {"enabled": False, "max_frequency": "daily"},
        "maintenance": {"enabled": True, "max_frequency": "hourly"}
    },
    "task_overrides": {}  # Individual task enable/disable
}
```

**Why opt-in by default?**
- Privacy: User must consent to autonomous actions
- Surprise prevention: No unexpected behavior
- Resource awareness: User knows it's running
- Trust building: Start conservative

---

### B. Heartbeat ↔ Task Runner Integration

**Two Integration Patterns:**

#### Pattern 1: Heartbeat Creates Tasks (Recommended)
Heartbeat service schedules tasks → Task Runner executes them

```python
# services/heartbeat_service.py
async def _execute_task(self, task: HeartbeatTask):
    # Convert heartbeat task to OhSee Task
    task_payload = {
        "goal": task.description,
        "conversation_id": None,  # System task
        "model_name": None,  # Use default
        "priority": 2,  # Normal priority
        "dry_run": False,
        "budget": {
            "max_seconds": 300,  # 5 min limit for heartbeat tasks
            "max_tool_calls": 10
        }
    }
    
    # Submit to task scheduler
    from services.task_scheduler import schedule_task
    await schedule_task(task_payload)
```

**Benefits:**
- Leverages existing task infrastructure
- Progress tracking via existing UI
- Budget/enforcement automatic
- Retries and error handling built-in
- Appears in Tasks panel for visibility

#### Pattern 2: Heartbeat as Task Runner Extension
Heartbeat runs as background worker alongside existing dispatcher

**Trade-offs:**
- More complex: Two scheduling systems
- Less visibility: Tasks don't appear in UI
- Redundant: Duplicates task logic

**Decision:** Use Pattern 1 (Heartbeat → Task Scheduler)

---

### C. Context & Memory Integration

**Problem:** Heartbeat tasks need context to be effective

**Solution: Context Injection Pipeline**

```
HEARTBEAT.md Task Discovered
    ↓
Context Gatherer (new component)
    ├─ Read MEMORY.md (long-term context)
    ├─ Search recent memory files (last 7 days)
    ├─ Query session transcripts (recent conversations)
    ├─ Check current git status
    └─ Load relevant project files
    ↓
Context Enriched Task
    ↓
Submitted to Task Runner
    ↓
Task executes with full context
```

**Implementation:**

```python
# services/context_gatherer.py
class ContextGatherer:
    """Gathers context for heartbeat tasks."""
    
    async def gather(self, task: HeartbeatTask) -> Dict[str, Any]:
        context = {
            "memory_summary": await self._load_memory_summary(),
            "recent_activity": await self._get_recent_activity(days=7),
            "project_state": await self._get_project_state(),
            "conversations": await self._get_recent_conversations(limit=10),
            "git_status": await self._get_git_status(),
        }
        return context
    
    async def _load_memory_summary(self) -> str:
        # Read MEMORY.md and summarize
        from memory_search import memory_search
        results = memory_search("current priorities active projects", max_results=5)
        return self._summarize_results(results)
```

**Context Usage in Task:**

```python
# Enhanced task description with context
task_payload = {
    "goal": f"""{task.description}

Context for this task:
- Current active projects: {context['memory_summary']}
- Recent activity: {context['recent_activity']}
- Git status: {context['git_status']}

Use this context to prioritize and execute effectively.
""",
    ...
}
```

**Benefits:**
- Tasks are context-aware
- Avoids redundant work
- References recent decisions
- Maintains continuity

---

### D. UI/UX Design

**New Settings Section: "Automation"**

```jsx
// SettingsSidebar.jsx addition
{
  id: 'automation',
  label: 'Automation',
  icon: Clock,  // or Activity, Zap
  description: 'Heartbeat and scheduled tasks'
}
```

**Automation Settings Panel:**

```jsx
// New component: AutomationSettings.jsx
<AutomationSettings>
  
  {/* Master Toggle */}
  <Section title="Heartbeat">
    <Toggle 
      label="Enable autonomous heartbeat"
      description="Allow OhSee to check for and execute proactive tasks"
      checked={heartbeatEnabled}
      onChange={toggleHeartbeat}
    />
    
    {heartbeatEnabled && (
      <>
        <QuietHoursSelector 
          start={quietHoursStart}
          end={quietHoursEnd}
          onChange={updateQuietHours}
        />
        
        <FrequencySelector
          options={['every_15min', 'hourly', 'every_4hours', 'daily']}
          value={checkFrequency}
          onChange={updateFrequency}
        />
      </>
    )}
  </Section>
  
  {/* Task Categories */}
  {heartbeatEnabled && (
    <Section title="Task Categories">
      <CategoryToggle
        icon={Brain}
        label="Memory Maintenance"
        description="Check memory files, update summaries"
        enabled={categories.memory.enabled}
        frequency={categories.memory.max_frequency}
        onToggle={() => toggleCategory('memory')}
      />
      
      <CategoryToggle
        icon={TestTube}
        label="Test Execution"
        description="Run security and unit tests"
        enabled={categories.testing.enabled}
        frequency={categories.testing.max_frequency}
        onToggle={() => toggleCategory('testing')}
      />
      
      <CategoryToggle
        icon={MessageSquare}
        label="Proactive Messages"
        description="Send Telegram updates about progress"
        enabled={categories.messaging.enabled}
        frequency={categories.messaging.max_frequency}
        onToggle={() => toggleCategory('messaging')}
      />
    </Section>
  )}
  
  {/* Live Status */}
  {heartbeatEnabled && (
    <Section title="Status">
      <StatusCard
        lastCheck={lastCheckTime}
        nextCheck={nextCheckTime}
        tasksExecuted={executionCount}
        isQuietHours={isQuietHours}
      />
      
      <TaskList
        tasks={recentTasks}
        onExecuteNow={executeTask}
        onToggleTask={toggleTask}
      />
    </Section>
  )}
  
</AutomationSettings>
```

**Visual Design:**
- Use existing OhSee styling (brand colors, borders)
- Toggle switches (not checkboxes) for main features
- Inline frequency selectors (dropdowns)
- Status cards with timestamps
- Real-time updates via WebSocket

---

### E. HEARTBEAT.md ↔ UI Sync

**Two-Way Binding:**

```
User edits HEARTBEAT.md (in workspace)
    ↓
HeartbeatService detects file change
    ↓
Parses tasks → Updates settings.heartbeat.task_overrides
    ↓
Frontend receives update via API/WebSocket
    ↓
UI reflects new tasks

User toggles task in UI
    ↓
API updates settings.heartbeat.task_overrides
    ↓
HeartbeatService respects setting
    ↓
(HEARTBEAT.md remains source of truth for task definitions)
```

**Data Model:**

```python
# HEARTBEAT.md (source of truth for WHAT)
- [ ] Check memory files every hour
- [ ] Run security tests daily

# settings.heartbeat.task_overrides (source of truth for ENABLED)
{
  "check-memory-files": {"enabled": true, "last_run": "2026-02-17T20:00:00Z"},
  "run-security-tests": {"enabled": false}  # User disabled in UI
}
```

---

## Implementation Plan

### Hour 8A: Backend Foundation
1. Add heartbeat settings to `db/settings_crud.py`
2. Create `services/context_gatherer.py`
3. Wire HeartbeatService → Task Scheduler
4. Add heartbeat status to API

### Hour 8B: Frontend UI
1. Create `AutomationSettings.jsx` component
2. Add 'automation' section to SettingsSidebar
3. Add route to SettingsPage
4. Connect to API

### Hour 9: Integration & Polish
1. Test end-to-end flow
2. Add real context gathering
3. Verify opt-in works
4. Document usage

---

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| **Opt-in default** | Privacy, trust, no surprises |
| **Heartbeat → Task Scheduler** | Reuse infrastructure, visibility, budgets |
| **Context Gatherer** | Tasks need context to be effective |
| **Two-way HEARTBEAT.md sync** | Power users edit files, casual users use UI |
| **Settings panel integration** | Consistent with existing OhSee UX |

---

## Open Questions

1. **Should heartbeat tasks appear in main Tasks panel?**
   - Yes: Full visibility
   - No: Separate "System Tasks" view

2. **Should heartbeat send Telegram notifications?**
   - Option: "Notify me when heartbeat executes tasks"
   - Categories: All, failures only, summaries only

3. **Should multiple users share heartbeat?**
   - Personal: Each user has their own HEARTBEAT.md
   - Shared: One system-wide HEARTBEAT.md
   - Hybrid: Personal + shared

4. **How handle failures?**
   - Retry N times, then alert user
   - Or: Log and continue (don't spam)

---

**Ready to implement?** 🦉
