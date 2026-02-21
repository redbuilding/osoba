# Enhanced Heartbeat System - User Guide

## Overview

The Enhanced Heartbeat System provides proactive AI assistance through automated insights and task creation. It analyzes your goals, conversations, project state, and system health to suggest actionable next steps.

## Key Features

### 1. **Context Gathering**
The heartbeat collects rich context from multiple sources:
- **Semantic Memory**: Conversation history, indexed conversations, storage usage
- **Git Repository**: Current branch, uncommitted files, unpushed commits, recent commits
- **Project Files**: TODO/FIXME comments, recently modified files
- **System Health**: Disk usage, service status

### 2. **Automated Task Creation**
Insights can automatically create tracked tasks in your task system:
- Enable "Auto-Create Tasks" in settings
- Tasks inherit title and description from insights
- Tasks are linked to insights for tracking
- Manual conversion available via "Create Task" button

### 3. **File-Based Configuration (Power Users)**
Define heartbeat tasks in `HEARTBEAT.md` for version control and team sharing:
- Category-based task organization
- Custom schedules (cron or interval format)
- Per-task context source configuration
- Two-way sync between file and UI

## Getting Started

### Basic Setup

1. **Open Settings** → Click Settings icon in header
2. **Navigate to Proactive Heartbeat** → Select from sidebar
3. **Enable Heartbeat** → Toggle "Enable Heartbeat" switch
4. **Configure Interval** → Choose check frequency (30m, 1h, 2h, 4h, 6h)
5. **Set Max Insights** → Limit daily insights (default: 5)

### Context Sources

Enable the context sources you want included in heartbeat analysis:

- **Semantic Memory** ✅ (Recommended)
  - Conversation history and search statistics
  - Helps identify patterns in your work

- **Git Repository** ✅ (Recommended)
  - Branch status and uncommitted changes
  - Suggests commits and code organization

- **Project Files** (Optional)
  - TODO/FIXME comment tracking
  - Recent file activity analysis

- **System Health** (Optional)
  - Disk usage monitoring
  - Service status checks

### Auto-Create Tasks

Enable automatic task creation for high-priority insights:

1. Toggle "Auto-Create Tasks" in settings
2. Insights will automatically create tracked tasks
3. View tasks in the Tasks panel
4. Tasks are linked to insights via metadata

## Using HEARTBEAT.md (Power Users)

### Creating the File

1. Create `HEARTBEAT.md` in your project root (or `.heartbeat/` or `.kiro/`)
2. Define tasks using the format below
3. Sync to database via Settings → Proactive Heartbeat

### File Format

```markdown
# Heartbeat Tasks

## Memory Management
Schedule: 0 2 * * *
Enabled: true
Prompt: Review semantic memory usage and suggest cleanup if storage exceeds 100MB
Context: memory

## Testing Reminders
Schedule: 0 9 * * 1
Enabled: true
Prompt: Check test coverage and suggest missing tests for recently modified files
Create_Task: true
Context: git,project

## Git Status Check
Schedule: 4h
Enabled: false
Prompt: Review uncommitted changes and suggest commits if there are 5+ uncommitted files
Context: git
```

### Field Reference

- **Category Name** (## heading): Task category/name
- **Schedule**: Cron expression or interval (e.g., `2h`, `30m`, `0 9 * * 1`)
- **Enabled**: `true` or `false`
- **Prompt**: Task-specific prompt for the AI
- **Create_Task** (optional): `true` to auto-create tasks
- **Context** (optional): Comma-separated sources (`memory,git,project,system`)

### Schedule Formats

**Interval Format:**
- `30m` - Every 30 minutes
- `1h` - Every hour
- `2h` - Every 2 hours
- `4h` - Every 4 hours

**Cron Format:**
- `0 9 * * *` - Daily at 9 AM
- `0 9 * * 1` - Every Monday at 9 AM
- `0 */4 * * *` - Every 4 hours
- `0 2 * * *` - Daily at 2 AM

### Syncing

**Load from File:**
1. Edit `HEARTBEAT.md` in your editor
2. Go to Settings → Proactive Heartbeat
3. Click "Load from File"
4. Tasks are validated and loaded to database

**Save to File:**
1. Configure tasks in UI
2. Click "Save to File"
3. Tasks are written to `HEARTBEAT.md`
4. Commit to version control

## Viewing Insights

### Insights Panel

1. **Click Bell Icon** (🔔) in header
2. **View Insights** - Unread count shown in badge
3. **Create Task** - Convert insight to tracked task
4. **Dismiss** - Remove insight from list

### Insight Actions

- **Create Task**: Converts insight to a tracked task in the Tasks panel
- **Dismiss**: Removes insight from the list (won't reappear)
- **Auto-Dismiss**: Insights older than 7 days are auto-dismissed

## Best Practices

### Recommended Configuration

**For Active Development:**
- Interval: 2 hours
- Context: Memory + Git
- Auto-Create Tasks: Enabled
- Max Insights: 5/day

**For Maintenance Mode:**
- Interval: 4-6 hours
- Context: Git + System
- Auto-Create Tasks: Disabled
- Max Insights: 3/day

**For Research/Writing:**
- Interval: 1-2 hours
- Context: Memory only
- Auto-Create Tasks: Enabled
- Max Insights: 5/day

### Context Source Guidelines

**Always Enable:**
- Semantic Memory (if you use conversation history)
- Git Repository (if you're coding)

**Enable When Needed:**
- Project Files (for TODO tracking and file activity)
- System Health (for disk space monitoring)

**Disable When:**
- Not relevant to your workflow
- Causing too many insights
- Privacy concerns (e.g., system health on shared machines)

### Managing Insight Volume

If you're getting too many insights:

1. **Increase Interval** - Check less frequently (4h instead of 2h)
2. **Reduce Max Insights** - Lower daily limit (3 instead of 5)
3. **Disable Context Sources** - Remove less relevant sources
4. **Refine Goals** - Make goals more specific in Goals & Priorities

If you're not getting enough insights:

1. **Decrease Interval** - Check more frequently (1h instead of 2h)
2. **Enable More Context** - Add project or system context
3. **Update Goals** - Add more detailed goals and priorities
4. **Check Active Hours** - Ensure heartbeat runs during work hours

## Advanced Features

### Manual Trigger

Test heartbeat immediately without waiting for interval:

1. Go to Settings → Proactive Heartbeat
2. Click "Test Heartbeat Now"
3. Check Insights Panel (🔔) for results

### Active Hours (Coming Soon)

Configure specific hours when heartbeat should run:
- Set start/end times
- Configure timezone
- Prevent insights during off-hours

### Category-Based Tasks (Coming Soon)

Define multiple heartbeat categories with independent schedules:
- Memory Management (daily at 2 AM)
- Testing Reminders (Monday mornings)
- Documentation Updates (Friday afternoons)
- System Health (every 12 hours)

## Troubleshooting

### No Insights Appearing

**Check Configuration:**
- Heartbeat is enabled
- Interval is reasonable (not too long)
- Max insights per day not reached
- Context sources are enabled

**Check Goals:**
- Goals document is filled out
- Goals are specific and actionable
- Recent conversations exist

**Check Logs:**
- Backend logs for errors
- Network tab for API failures

### Too Many Insights

**Adjust Settings:**
- Increase interval (2h → 4h)
- Reduce max insights (5 → 3)
- Disable less relevant context sources

**Refine Goals:**
- Make goals more specific
- Remove completed goals
- Focus on current priorities

### File Sync Errors

**Validation Errors:**
- Check HEARTBEAT.md syntax
- Ensure all required fields present
- Verify schedule format

**File Not Found:**
- Create HEARTBEAT.md in project root
- Or create in `.heartbeat/` directory
- Or create in `.kiro/` directory

### Tasks Not Creating

**Check Configuration:**
- "Auto-Create Tasks" is enabled
- Or use "Create Task" button manually

**Check Insight:**
- Insight is not already dismissed
- Insight has valid title/description

## API Reference

For developers integrating with the heartbeat system:

### Endpoints

```
GET  /api/heartbeat/config              - Get configuration
PUT  /api/heartbeat/config              - Update configuration
GET  /api/heartbeat/context-config      - Get context sources
PUT  /api/heartbeat/context-config      - Update context sources
GET  /api/heartbeat/insights            - Get insights
POST /api/heartbeat/insights/{id}/dismiss - Dismiss insight
POST /api/heartbeat/insights/{id}/create-task - Create task
GET  /api/heartbeat/file-status         - Check HEARTBEAT.md
POST /api/heartbeat/sync-from-file      - Load from file
POST /api/heartbeat/sync-to-file        - Write to file
POST /api/heartbeat/trigger             - Manual trigger
```

### Configuration Schema

```json
{
  "enabled": true,
  "interval": "2h",
  "model_name": "anthropic/claude-haiku-4-5",
  "max_insights_per_day": 5,
  "create_task": false,
  "context_sources": {
    "memory": true,
    "git": true,
    "project": false,
    "system": false
  }
}
```

## Privacy & Security

### Data Storage

- All insights stored in MongoDB
- Context data gathered locally
- No external API calls for context gathering
- Embeddings use local Ollama (if semantic memory enabled)

### Data Sharing

- Insights are user-specific
- No cross-user data leakage
- HEARTBEAT.md can be committed to version control
- Context sources can be disabled for privacy

### Recommendations

- Review context sources before enabling
- Disable system health on shared machines
- Use `.gitignore` for sensitive HEARTBEAT.md files
- Regularly review and dismiss old insights

## Support

For issues or questions:

1. Check this guide first
2. Review backend logs for errors
3. Test with "Test Heartbeat Now" button
4. Report issues on GitHub with logs

## Changelog

### Version 1.0 (Current)
- Context gathering (memory, git, project, system)
- Automated task creation
- File-based configuration (HEARTBEAT.md)
- Two-way sync between file and UI
- Manual insight-to-task conversion
- Configurable context sources
- Interval-based scheduling

### Coming Soon
- Active hours configuration
- Category-based tasks with independent schedules
- Insight priority levels
- Custom prompt templates
- Insight history and analytics
